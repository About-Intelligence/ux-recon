"""Browser controller — handles Playwright browser lifecycle, login, navigation, and deep interaction."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
from rich.console import Console

from src.config import AppConfig

console = Console()

# Counter for unique screenshot naming
_capture_counter = 0


def _next_id() -> int:
    global _capture_counter
    _capture_counter += 1
    return _capture_counter


@dataclass
class PageSnapshot:
    """Captured data from a single page."""
    url: str
    title: str
    html: str
    screenshot_path: str
    styles: list[str]
    computed_styles: dict[str, dict[str, str]]
    links: list[str]
    meta: dict[str, str]
    context: str = ""  # What triggered this capture (e.g., "nav", "action_click", "modal")


@dataclass
class CrawlResult:
    """Result of a full crawl session."""
    pages: list[PageSnapshot] = field(default_factory=list)
    visited_urls: set[str] = field(default_factory=set)
    failed_urls: dict[str, str] = field(default_factory=dict)
    interaction_captures: list[PageSnapshot] = field(default_factory=list)


class BrowserController:
    """Controls browser automation for website analysis with deep interaction support."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._project_root = Path(__file__).parent.parent.parent

    async def start(self) -> None:
        """Launch browser and create context."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo,
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            },
        )
        self._page = await self._context.new_page()
        console.print("[green]Browser launched[/green]")

    async def stop(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        console.print("[green]Browser closed[/green]")

    async def login(self) -> bool:
        """Log into the target website using visitor credentials."""
        page = self._page
        cfg = self.config.login
        wait_s = self.config.crawl.wait_for_spa / 1000

        if not cfg.username or not cfg.password:
            console.print("[red]No credentials configured. Set in settings.local.yaml or MIMIC_USERNAME/MIMIC_PASSWORD env vars.[/red]")
            return False

        console.print(f"[yellow]Navigating to login page: {self.config.target.url}[/yellow]")
        try:
            await page.goto(self.config.target.url, wait_until="networkidle", timeout=30000)
        except PwTimeout:
            console.print("[yellow]Page load timed out, continuing anyway...[/yellow]")
        await asyncio.sleep(wait_s)

        try:
            username_input = page.locator(cfg.username_selector).first
            await username_input.wait_for(state="visible", timeout=10000)
            await username_input.fill(cfg.username)

            password_input = page.locator(cfg.password_selector).first
            await password_input.fill(cfg.password)

            submit_btn = page.locator(cfg.submit_selector).first
            await submit_btn.click()

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(wait_s)

            # Check for successful login
            current_url = page.url

            # Method 1: custom success indicator
            if cfg.success_indicator:
                try:
                    await page.locator(cfg.success_indicator).first.wait_for(
                        state="visible", timeout=5000
                    )
                    console.print(f"[green]Login successful! Now at: {current_url}[/green]")
                    return True
                except PwTimeout:
                    console.print("[red]Login indicator not found[/red]")
                    return False

            # Method 2: check URL changed away from login
            if "login" not in current_url.lower() and "auth" not in current_url.lower():
                console.print(f"[green]Login successful! Now at: {current_url}[/green]")
                return True
            else:
                console.print("[red]Login may have failed — still on login/auth page[/red]")
                return False

        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            return False

    async def capture_current(self, label: str = "", context: str = "nav") -> PageSnapshot | None:
        """Capture a full snapshot of whatever is currently displayed."""
        page = self._page
        try:
            current_url = page.url
            title = await page.title()

            # Build a unique, filesystem-safe filename
            seq = _next_id()
            safe_label = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', label or title)[:40]
            screenshot_name = f"{seq:03d}_{safe_label}_{context}.png"
            screenshot_path = self._project_root / self.config.output.screenshots_dir / screenshot_name
            await page.screenshot(path=str(screenshot_path), full_page=True)

            html = await page.content()

            # Save DOM snapshot
            dom_path = self._project_root / self.config.output.dom_snapshots_dir / f"{seq:03d}_{safe_label}_{context}.html"
            try:
                dom_path.write_text(html, encoding="utf-8")
            except OSError as e:
                console.print(f"[yellow]Could not save DOM snapshot: {e}[/yellow]")

            styles = await self._safe_evaluate(page, """
                () => {
                    const styles = [];
                    for (const sheet of document.styleSheets) {
                        try {
                            const rules = Array.from(sheet.cssRules || []);
                            styles.push(rules.map(r => r.cssText).join('\\n'));
                        } catch (e) {
                            if (sheet.href) styles.push('/* External: ' + sheet.href + ' */');
                        }
                    }
                    return styles;
                }
            """, default=[])

            computed_styles = await self._safe_evaluate(page, """
                () => {
                    const selectors = ['body', 'header', 'nav', 'main', 'footer',
                        'h1', 'h2', 'h3', 'p', 'a', 'button',
                        '.sidebar', '.navbar', '.container', '.card',
                        '.el-dialog', '.el-drawer', '.el-form', '.el-table',
                        '.el-aside', '.el-header', '.el-main',
                        '.ant-layout-sider', '.ant-layout-header',
                        '[class*="sidebar"]', '[class*="navbar"]', '[class*="header"]'];
                    const result = {};
                    for (const sel of selectors) {
                        try {
                            const el = document.querySelector(sel);
                            if (!el) continue;
                            const cs = window.getComputedStyle(el);
                            result[sel] = {
                                color: cs.color, backgroundColor: cs.backgroundColor,
                                fontFamily: cs.fontFamily, fontSize: cs.fontSize,
                                fontWeight: cs.fontWeight, padding: cs.padding,
                                margin: cs.margin, display: cs.display,
                                position: cs.position, width: cs.width,
                                height: cs.height, borderRadius: cs.borderRadius,
                                boxShadow: cs.boxShadow,
                            };
                        } catch (e) {}
                    }
                    return result;
                }
            """, default={})

            links = await self._safe_evaluate(page, """
                () => {
                    const links = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href && !href.startsWith('javascript:') && !href.startsWith('mailto:')
                            && href.startsWith('http'))
                            links.add(href);
                    });
                    document.querySelectorAll('[to], [data-href]').forEach(el => {
                        const to = el.getAttribute('to') || el.getAttribute('data-href');
                        if (to && to.length > 0) links.add(to);
                    });
                    return [...links];
                }
            """, default=[])

            meta = await self._safe_evaluate(page, """
                () => ({
                    title: document.title || '',
                    charset: document.characterSet || 'UTF-8',
                    viewport: (document.querySelector('meta[name=viewport]') || {}).content || '',
                    description: (document.querySelector('meta[name=description]') || {}).content || '',
                })
            """, default={"title": "", "charset": "UTF-8", "viewport": "", "description": ""})

            console.print(f"[green]  Captured [{context}]: {label or title}[/green]")
            return PageSnapshot(
                url=current_url, title=title, html=html,
                screenshot_path=str(screenshot_path), styles=styles,
                computed_styles=computed_styles, links=links, meta=meta,
                context=context,
            )
        except Exception as e:
            console.print(f"[red]  Capture failed: {e}[/red]")
            return None

    async def _safe_evaluate(self, page: Page, script: str, default: Any = None) -> Any:
        """Run page.evaluate with error handling."""
        try:
            return await page.evaluate(script)
        except Exception as e:
            console.print(f"[yellow]  JS evaluate failed: {e}[/yellow]")
            return default

    async def _close_overlays(self) -> None:
        """Close any open modals, drawers, or dialogs using configurable selectors."""
        page = self._page
        icfg = self.config.interaction

        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            # Try each close button selector
            for selector in icfg.modal_close_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return
                except Exception:
                    continue

            # Fallback: press Escape again
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _find_first_visible(self, selectors: list[str]) -> tuple[any, int] | tuple[None, int]:
        """Find the first visible element matching any of the given selectors. Returns (locator, count)."""
        page = self._page
        for selector in selectors:
            try:
                loc = page.locator(selector)
                count = await loc.count()
                if count > 0 and await loc.first.is_visible():
                    return loc, count
            except Exception:
                continue
        return None, 0

    async def _interact_with_page(self, page_label: str, result: CrawlResult) -> None:
        """Deep interaction: click action buttons, open modals/drawers, capture states."""
        page = self._page
        icfg = self.config.interaction
        wait_s = self.config.crawl.wait_after_navigation / 1000
        timeout = self.config.crawl.interaction_timeout
        max_items = self.config.crawl.max_interaction_items

        # --- 1. Try action/operation dropdown buttons ---
        action_loc, action_count = await self._find_first_visible(icfg.action_button_selectors)
        if action_loc and action_count > 0:
            try:
                console.print(f"[cyan]  Found {action_count} action buttons, clicking first...[/cyan]")
                await action_loc.first.click()
                await asyncio.sleep(1)

                snap = await self.capture_current(f"{page_label}_action_dropdown", "action_dropdown")
                if snap:
                    result.interaction_captures.append(snap)

                dropdown_items = page.locator(icfg.dropdown_item_selector)
                item_count = await dropdown_items.count()
                console.print(f"[cyan]  Found {item_count} dropdown items[/cyan]")

                for i in range(min(item_count, max_items)):
                    try:
                        # Re-open dropdown
                        await action_loc.first.click()
                        await asyncio.sleep(0.8)

                        visible_items = page.locator(icfg.dropdown_item_selector)
                        current_count = await visible_items.count()
                        if i >= current_count:
                            break

                        item = visible_items.nth(i)
                        item_text = (await item.text_content() or "").strip()

                        if not item_text:
                            continue
                        # Skip destructive actions (case-insensitive)
                        if any(kw.lower() in item_text.lower() for kw in icfg.destructive_keywords):
                            console.print(f"[yellow]    Skipping destructive: {item_text}[/yellow]")
                            continue

                        console.print(f"[cyan]    Clicking: {item_text}[/cyan]")
                        await item.click()
                        await asyncio.sleep(wait_s)

                        # Check for modal
                        modal_opened = await self._check_and_capture_modal(
                            f"{page_label}_{item_text}", result
                        )

                        if not modal_opened:
                            snap = await self.capture_current(
                                f"{page_label}_{item_text}", "action_result"
                            )
                            if snap:
                                result.interaction_captures.append(snap)

                            # If we navigated away, go back
                            new_url = page.url
                            if "login" in new_url.lower() or "auth" in new_url.lower():
                                console.print("[yellow]  Redirected to login, re-logging in...[/yellow]")
                                await self.login()
                                return
                            await page.go_back()
                            await asyncio.sleep(wait_s)

                    except Exception as e:
                        console.print(f"[yellow]    Item {i} failed: {type(e).__name__}[/yellow]")
                        await self._close_overlays()

            except Exception as e:
                console.print(f"[yellow]  Action button interaction failed: {e}[/yellow]")

        # --- 2. Try add/create buttons ---
        add_loc, _ = await self._find_first_visible(icfg.add_button_selectors)
        if add_loc:
            try:
                console.print(f"[cyan]  Found Add button, clicking...[/cyan]")
                await add_loc.first.click()
                await asyncio.sleep(wait_s)
                await self._check_and_capture_modal(f"{page_label}_add_form", result)
            except Exception as e:
                console.print(f"[yellow]  Add button failed: {type(e).__name__}[/yellow]")

        # --- 3. Try expanding table rows ---
        expand_loc, expand_count = await self._find_first_visible(icfg.expand_selectors)
        if expand_loc and expand_count > 0:
            try:
                console.print(f"[cyan]  Found {expand_count} expandable rows, expanding first...[/cyan]")
                await expand_loc.first.click()
                await asyncio.sleep(1)
                snap = await self.capture_current(f"{page_label}_expanded_row", "expanded_row")
                if snap:
                    result.interaction_captures.append(snap)
            except Exception:
                pass

        # --- 4. Try clicking inactive tabs ---
        try:
            tabs = page.locator(icfg.tab_selector)
            tab_count = await tabs.count()
            if tab_count > 0:
                console.print(f"[cyan]  Found {tab_count} inactive tabs[/cyan]")
                for i in range(min(tab_count, 4)):
                    try:
                        tab = tabs.nth(i)
                        tab_text = (await tab.text_content() or "").strip()
                        if not tab_text:
                            continue
                        console.print(f"[cyan]    Clicking tab: {tab_text}[/cyan]")
                        await tab.click()
                        await asyncio.sleep(wait_s)
                        snap = await self.capture_current(
                            f"{page_label}_tab_{tab_text}", "tab_switch"
                        )
                        if snap:
                            result.interaction_captures.append(snap)
                    except Exception:
                        pass
        except Exception:
            pass

    async def _check_and_capture_modal(self, label: str, result: CrawlResult) -> bool:
        """Check if a modal/drawer/dialog is open, capture it, then close it."""
        page = self._page
        icfg = self.config.interaction

        # Check each modal selector
        for selector in icfg.modal_selectors:
            try:
                modal = page.locator(selector).first
                await modal.wait_for(state="visible", timeout=2000)
                console.print(f"[cyan]  Modal/drawer detected, capturing...[/cyan]")
                snap = await self.capture_current(label, "modal")
                if snap:
                    result.interaction_captures.append(snap)
                await self._close_overlays()
                return True
            except PwTimeout:
                continue
            except Exception:
                continue

        return False

    async def crawl(self) -> CrawlResult:
        """Crawl the website with deep interaction."""
        result = CrawlResult()
        start_url = self.config.target.dashboard_url or self.config.target.url
        base_domain = urlparse(start_url).netloc
        wait_s = self.config.crawl.wait_after_navigation / 1000
        retries = self.config.crawl.retry_failed

        # BFS crawl
        queue: list[tuple[str, int]] = [(start_url, 0)]

        while queue and len(result.pages) < self.config.crawl.max_pages:
            url, depth = queue.pop(0)

            norm_url = self._normalize_url(url)
            if norm_url in result.visited_urls:
                continue

            if any(pat in url for pat in self.config.crawl.exclude_patterns):
                continue

            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc != base_domain:
                continue
            if parsed.scheme and parsed.scheme not in ("http", "https"):
                continue

            result.visited_urls.add(norm_url)
            console.print(f"\n[bold cyan]Crawling (depth={depth}): {url}[/bold cyan]")

            # Navigate with retry
            page = self._page
            nav_success = False
            for attempt in range(1 + retries):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(wait_s)
                    nav_success = True
                    break
                except PwTimeout:
                    if attempt == 0:
                        console.print(f"[yellow]  Timeout on networkidle, retrying...[/yellow]")
                    else:
                        console.print(f"[yellow]  Proceeding despite timeout[/yellow]")
                        nav_success = True  # Continue with whatever loaded
                except Exception as e:
                    console.print(f"[red]  Navigation failed (attempt {attempt + 1}): {e}[/red]")

            if not nav_success:
                result.failed_urls[url] = "Navigation failed after retries"
                continue

            page_label = url.split("#")[-1].strip("/").replace("/", "_") if "#" in url else "page"

            # 1. Capture the page
            snapshot = await self.capture_current(page_label, "nav")
            if snapshot:
                result.pages.append(snapshot)

                if depth < self.config.crawl.max_depth:
                    for link in snapshot.links:
                        link_norm = self._normalize_url(link)
                        if link_norm not in result.visited_urls:
                            queue.append((link, depth + 1))

            # 2. Deep interaction
            console.print(f"[yellow]  Deep interaction on: {page_label}[/yellow]")
            await self._interact_with_page(page_label, result)

        total = len(result.pages) + len(result.interaction_captures)
        console.print(f"\n[bold green]Crawl complete: {len(result.pages)} pages + "
                      f"{len(result.interaction_captures)} interactions = {total} total[/bold green]")
        return result

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for dedup. For hash-routed SPAs, keep the hash path."""
        parsed = urlparse(url)
        # Hash routing: #/path IS the route
        if parsed.fragment and parsed.fragment.startswith("/"):
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#{parsed.fragment.split('?')[0]}"
        # Hashbang: #!/path
        if parsed.fragment and parsed.fragment.startswith("!/"):
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#{parsed.fragment.split('?')[0]}"
        # Regular URL — strip fragment and query
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
