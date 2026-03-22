"""Exploration engine — state machine loop that orchestrates the agent."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel

from src.config import AppConfig
from src.agent.state import (
    AgentPhase, AgentState, ExplorationTarget, StateSnapshot,
    ActionType, TargetType, VisitStatus,
)
from src.agent.logger import RunLogger
from src.browser.controller import BrowserController
from src.browser.authenticator import Authenticator
from src.observer.extractor import CandidateExtractor
from src.observer.fingerprint import DOMFingerprinter
from src.observer.novelty import NoveltyScorer
from src.analyzer.page_analyzer import PageAnalyzer
from src.artifacts.manager import ArtifactManager
from src.artifacts.inventory import InventoryGenerator
from src.artifacts.sitemap import SitemapGenerator
from src.artifacts.report import ReportGenerator

console = Console()


class ExplorationEngine:
    """State machine engine for autonomous website exploration."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.state = AgentState(
            budget=config.budget.max_states,
            max_depth=config.budget.max_depth,
        )

        # Components
        self.controller = BrowserController(config)
        self.authenticator = Authenticator(config, self.controller)
        self.extractor = CandidateExtractor(config)
        self.fingerprinter = DOMFingerprinter()
        self.novelty_scorer = NoveltyScorer(self.fingerprinter)
        self.analyzer = PageAnalyzer()
        self.artifacts = ArtifactManager(config)

        # Logger (created lazily after output is cleared)
        self._logger: RunLogger | None = None
        self._log_path = Path(__file__).parent.parent.parent / config.output.artifacts_dir / "run_log.jsonl"

        # Analysis results (state_id -> analysis dict)
        self._analysis_results: dict[str, dict] = {}

        # Timing
        self._start_time: str = ""

    @property
    def logger(self) -> RunLogger:
        if self._logger is None:
            self._logger = RunLogger(self._log_path)
        return self._logger

    async def run(self) -> AgentState:
        """Run the full exploration loop."""
        self._start_time = datetime.now().isoformat()

        console.print(Panel.fit(
            f"[bold cyan]Frontend Mimic Agent[/bold cyan]\n"
            f"Target: {self.config.target.url}\n"
            f"Budget: {self.config.budget.max_states} states, depth {self.config.budget.max_depth}\n"
            f"Novelty threshold: {self.config.budget.novelty_threshold}",
            title="Agent Configuration",
        ))

        try:
            # INITIALIZE
            await self._phase_initialize()

            # AUTHENTICATE
            await self._phase_authenticate()

            # Navigate to dashboard if configured
            dashboard_url = self.config.target.dashboard_url
            if dashboard_url:
                await self.controller.goto(dashboard_url)

            # Create initial target for the current page
            current_url = await self.controller.get_url()
            root_target = ExplorationTarget.create(
                target_type=TargetType.ROUTE,
                locator=current_url,
                label=self._url_to_label(current_url),
                depth=0,
                discovery_method="initial_page",
            )
            self.state.add_target(root_target)

            # Main exploration loop
            while True:
                # OBSERVE current page
                await self._phase_observe()

                # SELECT next action
                target = self._phase_select_action()
                if target is None:
                    break  # Frontier empty or budget exhausted

                # EXECUTE (includes pre-capture novelty check)
                snapshot = await self._phase_execute(target)
                if snapshot is None:
                    # Failed or skipped (low novelty) — still backtrack
                    await self._phase_backtrack_continue(target)
                    continue

                # ANALYZE (snapshot already passed novelty threshold)
                await self._phase_analyze(snapshot)

                # BACKTRACK / CONTINUE
                await self._phase_backtrack_continue(target)

            # FINALIZE
            await self._phase_finalize()

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            await self._phase_finalize()
        except Exception as e:
            console.print(f"\n[red]Engine error: {e}[/red]")
            self.logger.log(AgentPhase.FINALIZE, "engine_error", "", "failed", str(e))
            await self._phase_finalize()
        finally:
            await self.controller.stop()
            if self._logger:
                self._logger.close()

        return self.state

    # ── Phase implementations ──

    async def _phase_initialize(self) -> None:
        """INITIALIZE: Launch browser, set up output dirs."""
        self.state.phase = AgentPhase.INITIALIZE

        # Clear previous output BEFORE logger opens the log file
        self.artifacts.clear_output()

        with self.logger.timed(AgentPhase.INITIALIZE, "launch_browser") as ctx:
            await self.controller.start()
            ctx["reason"] = "chromium started"

        self.logger.log(AgentPhase.INITIALIZE, "clear_output", "", "success", "output directories cleared")
        console.print("[green]Browser launched, output cleared[/green]")

    async def _phase_authenticate(self) -> None:
        """AUTHENTICATE: Login to target website with retries."""
        self.state.phase = AgentPhase.AUTHENTICATE

        for attempt in range(3):
            with self.logger.timed(AgentPhase.AUTHENTICATE, "login", self.config.target.url) as ctx:
                success = await self.authenticator.login()
                if success:
                    ctx["reason"] = "login successful"
                    console.print("[green]Authenticated successfully[/green]")
                    return
                ctx["result"] = "retry" if attempt < 2 else "failed"
                ctx["reason"] = f"login attempt {attempt + 1} failed"
            console.print(f"[yellow]Login attempt {attempt + 1} failed, retrying...[/yellow]")
            await asyncio.sleep(3)

        raise RuntimeError("Authentication failed after 3 attempts. Check credentials in config.")

    async def _phase_observe(self) -> None:
        """OBSERVE: Extract candidates from current page, add to frontier."""
        self.state.phase = AgentPhase.OBSERVE

        page = self.controller.page
        current_url = await self.controller.get_url()
        current_target = self.state.targets.get(self.state.current_target_id or "")
        current_depth = current_target.depth if current_target else 0

        # Skip re-observation of already-observed URLs
        normalized_url = self._normalize_url(current_url)
        if normalized_url in self.state.observed_urls:
            return
        self.state.observed_urls.add(normalized_url)

        with self.logger.timed(AgentPhase.OBSERVE, "extract_candidates",
                               current_target.label if current_target else "root") as ctx:
            candidates, coverage = await self.extractor.extract_all(page, self.state.current_target_id, current_depth)
            added = self.state.add_targets(candidates)
            ctx["reason"] = f"found {len(candidates)} candidates, {added} new"

            # Store coverage for this page (only for route targets, first visit)
            if current_target and current_target.id not in self.state.coverage:
                self.state.coverage[current_target.id] = coverage

        if added > 0:
            console.print(f"[cyan]  Discovered {added} new targets (frontier: {len(self.state.frontier)})[/cyan]")

    def _phase_select_action(self) -> ExplorationTarget | None:
        """SELECT_ACTION: Pick next target from frontier, check budget."""
        self.state.phase = AgentPhase.SELECT_ACTION

        if not self.state.has_budget():
            self.logger.log(AgentPhase.SELECT_ACTION, "budget_exhausted", "", "success",
                          f"budget exhausted ({self.state.budget_total} states)")
            console.print("[yellow]Budget exhausted[/yellow]")
            return None

        target = self.state.pop_frontier()
        if target is None:
            self.logger.log(AgentPhase.SELECT_ACTION, "frontier_empty", "", "success",
                          "no more targets to explore")
            console.print("[yellow]Frontier empty — exploration complete[/yellow]")
            return None

        self.logger.log(AgentPhase.SELECT_ACTION, "selected_target", target.label, "success",
                      f"type={target.target_type.value}, depth={target.depth}")
        return target

    async def _phase_execute(self, target: ExplorationTarget) -> StateSnapshot | None:
        """EXECUTE: Navigate/click to target, capture screenshot + HTML."""
        self.state.phase = AgentPhase.EXECUTE
        step = self.state.next_step()

        console.print(f"\n[bold cyan]Step {step}: {target.target_type.value} → {target.label}[/bold cyan]")

        # Execute the action based on target type
        success = False
        action_type = self._target_to_action(target)

        for attempt in range(1 + self.config.budget.retry_limit):
            with self.logger.timed(AgentPhase.EXECUTE, action_type.value, target.label) as ctx:
                try:
                    success = await self._execute_target(target)
                    if success:
                        ctx["reason"] = "navigation successful"
                        break
                    else:
                        ctx["result"] = "retry" if attempt < self.config.budget.retry_limit else "failed"
                        ctx["reason"] = f"attempt {attempt + 1} failed"
                except Exception as e:
                    ctx["result"] = "retry" if attempt < self.config.budget.retry_limit else "failed"
                    ctx["reason"] = str(e)

            if not success and attempt < self.config.budget.retry_limit:
                console.print(f"[yellow]  Retry {attempt + 1}...[/yellow]")
                await asyncio.sleep(1)

        if not success:
            retries = self.state.mark_failed(target.id)
            self.logger.log(AgentPhase.EXECUTE, "mark_failed", target.label, "failed",
                          f"failed after {retries} attempts")
            return None

        # Check session (might have been redirected to login)
        if not await self.authenticator.check_session():
            console.print("[yellow]Session expired, re-authenticating...[/yellow]")
            await self.authenticator.re_login()
            return None

        # Pre-capture novelty check: get HTML and score before taking screenshot
        html = await self.controller.get_html()
        novelty, fingerprint = self.novelty_scorer.score(html)
        threshold = self.config.budget.novelty_threshold

        if novelty < threshold:
            # Low novelty — mark visited but DON'T consume budget or capture screenshot
            self.state.mark_visited(target.id)
            self.novelty_scorer.register(html, fingerprint)
            self.logger.log(AgentPhase.EVAL_NOVELTY, "skip_duplicate", target.label,
                          "skipped", f"novelty={novelty:.2f} < {threshold}")
            console.print(f"[dim]  Low novelty ({novelty:.2f}) — skipping capture entirely[/dim]")

            # Still create a minimal snapshot for the inventory (no files saved)
            url = await self.controller.get_url()
            snapshot = StateSnapshot.create(
                target_id=target.id, url=url, title=await self.controller.get_title(),
                visit_status=VisitStatus.SKIPPED, depth=target.depth,
                novelty_score=novelty, dom_fingerprint=fingerprint,
            )
            snapshot.metadata = {"skipped_reason": "low_novelty"}
            self.state.register_state(snapshot)
            self.state.current_target_id = target.id
            return None  # Don't proceed to analyze

        # Novel enough — capture screenshot + DOM, consume budget
        snapshot = await self._capture_state(target)
        if snapshot:
            snapshot.novelty_score = novelty
            snapshot.dom_fingerprint = fingerprint
            self.novelty_scorer.register(html, fingerprint)
            self.state.mark_visited(target.id)
            self.state.consume_budget()

            # Add edge from previous state
            if self.state.current_state_id:
                self.state.add_edge(
                    self.state.current_state_id, snapshot.id,
                    action_type, target.locator, target.label,
                )

            self.state.current_state_id = snapshot.id
            self.state.current_target_id = target.id

            # Update parent coverage tracking
            self._update_coverage(target)

            console.print(f"[green]  Captured: {snapshot.url} (novelty={novelty:.2f})[/green]")

        return snapshot

    async def _phase_analyze(self, snapshot: StateSnapshot) -> None:
        """ANALYZE: Run local page analysis on the captured state."""
        self.state.phase = AgentPhase.ANALYZE

        html = ""
        try:
            html_path = Path(snapshot.html_path)
            if html_path.exists():
                html = html_path.read_text(encoding="utf-8")
        except Exception:
            return

        if not html:
            return

        with self.logger.timed(AgentPhase.ANALYZE, "analyze_page", snapshot.id) as ctx:
            computed_styles = await self.controller.get_computed_styles()
            analysis = self.analyzer.analyze(html, computed_styles)
            self._analysis_results[snapshot.id] = analysis
            self.artifacts.save_analysis(snapshot.id, analysis)
            ctx["reason"] = f"components: {', '.join(analysis.get('component_types', []))}"

    async def _phase_backtrack_continue(self, target: ExplorationTarget) -> None:
        """BACKTRACK_CONTINUE: Close overlays or go back if needed."""
        self.state.phase = AgentPhase.BACKTRACK_CONTINUE

        if target.target_type in (TargetType.MODAL, TargetType.DROPDOWN):
            # Close the overlay
            await self.controller.close_overlays()
            self.logger.log(AgentPhase.BACKTRACK_CONTINUE, "close_overlay", target.label,
                          "success", "overlay closed")

        elif target.target_type == TargetType.DROPDOWN_ITEM:
            # Dropdown item may have opened a modal, navigated to a new page, or both
            if await self.controller.is_modal_open():
                await self.controller.close_overlays()
                self.logger.log(AgentPhase.BACKTRACK_CONTINUE, "close_overlay", target.label,
                              "success", "modal from dropdown item closed")
            else:
                # May have navigated — go back to parent page
                await self.controller.go_back()
                self.logger.log(AgentPhase.BACKTRACK_CONTINUE, "go_back", target.label,
                              "success", "returned from dropdown item page")

        elif target.target_type == TargetType.EXPANDED_ROW:
            pass

        elif target.target_type == TargetType.TAB_STATE:
            pass

    async def _phase_finalize(self) -> None:
        """FINALIZE: Generate all artifacts and report."""
        self.state.phase = AgentPhase.FINALIZE
        end_time = datetime.now().isoformat()

        console.print("\n[bold]Generating artifacts...[/bold]")

        # Inventory
        with self.logger.timed(AgentPhase.FINALIZE, "generate_inventory") as ctx:
            inventory = InventoryGenerator().generate(self.state)
            path = self.artifacts.save_json("inventory.json", inventory)
            ctx["reason"] = f"{len(inventory)} entries → {path.name}"

        # Sitemap
        with self.logger.timed(AgentPhase.FINALIZE, "generate_sitemap") as ctx:
            sitemap = SitemapGenerator().generate(self.state)
            path = self.artifacts.save_json("sitemap.json", sitemap)
            ctx["reason"] = f"{sitemap['stats']['total_nodes']} nodes → {path.name}"

        # Coverage
        with self.logger.timed(AgentPhase.FINALIZE, "generate_coverage") as ctx:
            from dataclasses import asdict
            coverage_data = {tid: asdict(cov) for tid, cov in self.state.coverage.items()}
            path = self.artifacts.save_json("coverage.json", coverage_data)
            pages_with_gaps = sum(1 for c in self.state.coverage.values() if c.has_unexplored)
            ctx["reason"] = f"{len(coverage_data)} pages, {pages_with_gaps} with gaps → {path.name}"

        # Report
        with self.logger.timed(AgentPhase.FINALIZE, "generate_report") as ctx:
            report = ReportGenerator().generate(
                self.state, self._start_time, end_time, self._analysis_results
            )
            path = self.artifacts.save_text("exploration_report.md", report)
            ctx["reason"] = f"report → {path.name}"

        # Print summary
        stats = self.state.get_stats()
        console.print(Panel.fit(
            f"[bold green]Exploration Complete[/bold green]\n\n"
            f"States captured: {stats['states_captured']}\n"
            f"Targets discovered: {stats['total_targets']}\n"
            f"Visited: {stats['visited']} | Skipped: {stats['skipped']} | Failed: {stats['failed']}\n"
            f"Budget used: {stats['budget_used']} / {self.state.budget_total}\n"
            f"Steps: {stats['steps']}\n\n"
            f"Artifacts:\n"
            f"  inventory.json, sitemap.json, run_log.jsonl\n"
            f"  exploration_report.md\n"
            f"  {len(self._analysis_results)} state analyses",
            title="Summary",
        ))

    # ── Helpers ──

    def _update_coverage(self, target: ExplorationTarget) -> None:
        """Update parent page's coverage counters when an interaction target is explored."""
        if not target.parent_id or target.parent_id not in self.state.coverage:
            return
        cov = self.state.coverage[target.parent_id]
        if target.target_type == TargetType.DROPDOWN:
            cov.action_buttons_clicked += 1
        elif target.target_type == TargetType.DROPDOWN_ITEM:
            cov.dropdown_items_explored += 1
        elif target.target_type == TargetType.MODAL:
            cov.add_buttons_clicked += 1
        elif target.target_type == TargetType.TAB_STATE:
            cov.tabs_switched += 1
        elif target.target_type == TargetType.EXPANDED_ROW:
            cov.expand_rows_expanded += 1

    async def _navigate_to_parent_page(self, target: ExplorationTarget) -> bool:
        """For non-route targets, navigate to the parent route first."""
        if target.target_type == TargetType.ROUTE:
            return True  # Routes navigate themselves

        # Find the parent route target
        parent_id = target.parent_id
        while parent_id:
            parent = self.state.targets.get(parent_id)
            if not parent:
                break
            if parent.target_type == TargetType.ROUTE:
                # Navigate to this route
                current_url = await self.controller.get_url()
                parent_locator = parent.locator
                if parent_locator.startswith(("http://", "https://", "#", "/")):
                    if parent_locator.startswith(("#", "/")):
                        parsed = urlparse(current_url)
                        if parent_locator.startswith("#"):
                            parent_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}{parent_locator}"
                        else:
                            parent_url = f"{parsed.scheme}://{parsed.netloc}{parent_locator}"
                    else:
                        parent_url = parent_locator

                    # Check if already on parent page
                    if self._normalize_url(current_url) == self._normalize_url(parent_url):
                        return True

                    return await self.controller.goto(parent_url)
                break
            parent_id = parent.parent_id
        return True  # No parent found, try anyway

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        parsed = urlparse(url)
        if parsed.fragment and parsed.fragment.startswith("/"):
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#{parsed.fragment.split('?')[0]}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    async def _execute_target(self, target: ExplorationTarget) -> bool:
        """Execute navigation/interaction for a target."""
        # For non-route targets, navigate to parent page first
        if target.target_type != TargetType.ROUTE:
            if not await self._navigate_to_parent_page(target):
                return False

        if target.target_type == TargetType.ROUTE:
            locator = target.locator
            url_before = await self.controller.get_url()

            if locator.startswith(("http://", "https://", "#", "/")):
                # Direct URL navigation
                url = locator
                if locator.startswith(("#", "/")):
                    base = url_before
                    parsed = urlparse(base)
                    if locator.startswith("#"):
                        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}{locator}"
                    else:
                        url = f"{parsed.scheme}://{parsed.netloc}{locator}"
                return await self.controller.goto(url)
            else:
                # CSS selector — click it and verify URL changed
                clicked = await self.controller.click(locator, timeout=self.config.crawl.interaction_timeout)
                if clicked:
                    url_after = await self.controller.get_url()
                    if url_after == url_before:
                        # Click didn't navigate — probably a sub-menu toggle
                        return False
                return clicked

        elif target.target_type == TargetType.DROPDOWN:
            clicked = await self.controller.click(target.locator, timeout=self.config.crawl.interaction_timeout)
            if clicked:
                # Detect dropdown items and add them as targets
                await self._discover_dropdown_items(target)
            return clicked

        elif target.target_type == TargetType.DROPDOWN_ITEM:
            return await self._execute_dropdown_item(target)

        elif target.target_type == TargetType.MODAL:
            return await self.controller.click(target.locator, timeout=self.config.crawl.interaction_timeout)

        elif target.target_type == TargetType.TAB_STATE:
            return await self.controller.click(target.locator, timeout=self.config.crawl.interaction_timeout)

        elif target.target_type == TargetType.EXPANDED_ROW:
            return await self.controller.click(target.locator, timeout=self.config.crawl.interaction_timeout)

        return False

    async def _discover_dropdown_items(self, dropdown_target: ExplorationTarget) -> None:
        """After opening a dropdown, detect individual menu items and add them as targets."""
        page = self.controller.page
        icfg = self.config.interaction
        destructive = self.config.exploration.destructive_keywords

        # Use strict dropdown-only selectors (not [role=menuitem] which matches sidebar)
        strict_selector = (
            ".el-dropdown-menu__item:visible, "
            ".ant-dropdown-menu-item:visible, "
            ".dropdown-item:visible"
        )

        try:
            await asyncio.sleep(0.5)  # Wait for dropdown animation
            items = page.locator(strict_selector)
            count = await items.count()

            if count == 0:
                return

            # Find the parent route target for these items
            route_parent_id = dropdown_target.parent_id

            added = 0
            max_items = self.config.crawl.max_interaction_items
            for i in range(min(count, max_items)):
                try:
                    item = items.nth(i)
                    if not await item.is_visible():
                        continue
                    text = (await item.text_content() or "").strip()
                    if not text:
                        continue

                    # Skip destructive actions
                    if any(kw.lower() in text.lower() for kw in destructive):
                        continue

                    target = ExplorationTarget.create(
                        target_type=TargetType.DROPDOWN_ITEM,
                        locator=f"{icfg.dropdown_item_selector} >> nth={i}",
                        label=f"{text}@{dropdown_target.label}",
                        parent_id=route_parent_id,
                        depth=dropdown_target.depth + 1,
                        discovery_method="dropdown_item",
                        metadata={
                            "item_text": text,
                            "item_index": i,
                            "dropdown_target_id": dropdown_target.id,
                            "dropdown_selector": dropdown_target.locator,
                        },
                    )
                    if self.state.add_target(target):
                        added += 1
                except Exception:
                    continue

            if added > 0:
                console.print(f"[cyan]  Discovered {added} dropdown items[/cyan]")

            # Update coverage
            if dropdown_target.parent_id and dropdown_target.parent_id in self.state.coverage:
                cov = self.state.coverage[dropdown_target.parent_id]
                cov.dropdown_items_found = max(cov.dropdown_items_found, count)

        except Exception:
            pass

    async def _execute_dropdown_item(self, target: ExplorationTarget) -> bool:
        """Execute a dropdown item: open the dropdown first, then click the specific item."""
        meta = target.metadata
        dropdown_selector = meta.get("dropdown_selector", "")
        item_index = meta.get("item_index", 0)

        # Use strict dropdown-only selectors
        strict_selector = (
            ".el-dropdown-menu__item:visible, "
            ".ant-dropdown-menu-item:visible, "
            ".dropdown-item:visible"
        )

        # Open the dropdown
        if dropdown_selector:
            clicked = await self.controller.click(dropdown_selector, timeout=self.config.crawl.interaction_timeout)
            if not clicked:
                return False
            await asyncio.sleep(0.5)

        # Click the specific item
        try:
            items = self.controller.page.locator(strict_selector)
            count = await items.count()
            if item_index >= count:
                return False

            item = items.nth(item_index)
            if not await item.is_visible():
                return False

            await item.click()
            await asyncio.sleep(self.config.crawl.wait_after_navigation / 1000)
            return True
        except Exception:
            return False

    async def _capture_state(self, target: ExplorationTarget) -> StateSnapshot | None:
        """Capture current browser state as a snapshot."""
        try:
            url = await self.controller.get_url()
            title = await self.controller.get_title()

            label = target.label or self._url_to_label(url)
            context = target.target_type.value

            screenshot_path = await self.controller.capture_screenshot(label, context)
            html_path = await self.controller.save_html(label, context)

            snapshot = StateSnapshot.create(
                target_id=target.id,
                url=url,
                title=title,
                screenshot_path=screenshot_path,
                html_path=html_path,
                visit_status=VisitStatus.SUCCESS,
                depth=target.depth,
            )

            self.state.register_state(snapshot)
            return snapshot

        except Exception as e:
            console.print(f"[red]  Capture failed: {e}[/red]")
            return None

    def _target_to_action(self, target: ExplorationTarget) -> ActionType:
        """Map target type to action type."""
        mapping = {
            TargetType.ROUTE: ActionType.NAVIGATE,
            TargetType.MODAL: ActionType.OPEN_MODAL,
            TargetType.DROPDOWN: ActionType.CLICK_ACTION,
            TargetType.DROPDOWN_ITEM: ActionType.CLICK_DROPDOWN_ITEM,
            TargetType.TAB_STATE: ActionType.SWITCH_TAB,
            TargetType.EXPANDED_ROW: ActionType.EXPAND_ROW,
        }
        return mapping.get(target.target_type, ActionType.NAVIGATE)

    def _url_to_label(self, url: str) -> str:
        """Extract a human-readable label from URL."""
        if "#" in url:
            path = url.split("#")[-1].strip("/")
            return path.replace("/", "_") if path else "root"
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        return path.replace("/", "_") if path else "root"
