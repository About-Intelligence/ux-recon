"""Reviewer-style UX memo orchestration built from rich browser artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup

from src.agent.state import AgentState, StateSnapshot
from src.analysis.competitive_report import CompetitiveAnalysis
from src.analysis.report_text import best_surface_label, clean_report_text, display_label, route_family_from_url


@dataclass
class UXSnapshotContext:
    snapshot: StateSnapshot
    label: str
    page_type: str
    route_family: str
    headings: list[str] = field(default_factory=list)
    action_labels: list[str] = field(default_factory=list)
    input_prompts: list[str] = field(default_factory=list)
    interaction_hints: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    has_contenteditable: bool = False
    has_upgrade_cta: bool = False
    text_blob: str = ""

    @property
    def screenshot_path(self) -> str:
        return str(self.snapshot.metadata.get("report_screenshot_path") or self.snapshot.screenshot_path)


@dataclass
class UXReviewFinding:
    key: str
    title: str
    summary: str
    why_it_matters: str
    evidence: list[str] = field(default_factory=list)
    related_urls: list[str] = field(default_factory=list)


@dataclass
class UXRecommendation:
    title: str
    action: str
    rationale: str


@dataclass
class UXVisual:
    title: str
    summary: str
    caption: str
    image_path: str
    related_key: str


@dataclass
class UXReviewMemo:
    target: str
    evaluation_mode: str
    evaluation_lens: list[str]
    score: float
    overall_assessment: str
    scope_paths: list[str] = field(default_factory=list)
    scope_notes: list[str] = field(default_factory=list)
    strengths: list[UXReviewFinding] = field(default_factory=list)
    issues: list[UXReviewFinding] = field(default_factory=list)
    new_user_judgment: str = ""
    experienced_user_judgment: str = ""
    recommendations: list[UXRecommendation] = field(default_factory=list)
    conclusion: str = ""
    visuals: list[UXVisual] = field(default_factory=list)


class UXReviewOrchestrator:
    """Turn captures into a judgment-oriented UX review memo."""

    CAPABILITY_KEYWORDS = {
        "create": ("new", "create", "start", "begin", "新建", "创建", "开始"),
        "ask": ("ask", "question", "describe", "prompt", "输入", "描述任务", "问"),
        "files": ("file", "files", "upload", "import", "source", "资料", "文件", "导入", "分析文件"),
        "research": ("research", "search", "finder", "deep research", "slides", "diagram", "研究", "资料查找", "制作"),
    }
    CONCEPT_MAP = {
        "Project": ("project", "项目"),
        "Board": ("board", "看板"),
        "Document": ("document", "文档"),
        "Playground": ("playground",),
        "Agent": ("agent",),
        "Editor": ("editor",),
        "Space": ("space", "workspace", "空间"),
    }

    def build(
        self,
        state: AgentState,
        analysis: CompetitiveAnalysis,
        page_insights: dict[str, dict] | None,
        extraction_results: dict[str, dict] | None,
    ) -> UXReviewMemo:
        page_insights = page_insights or {}
        extraction_results = extraction_results or {}
        insights_by_url = self._insights_by_url(page_insights)
        snapshots = sorted(state.states.values(), key=lambda item: item.timestamp)
        contexts = [self._snapshot_context(snapshot, insights_by_url.get(snapshot.url, {})) for snapshot in snapshots]

        strengths = self._strengths(contexts)
        issues = self._issues(contexts)
        score = self._score(strengths, issues)
        target = analysis.target or (contexts[0].snapshot.url if contexts else "unknown")

        return UXReviewMemo(
            target=target,
            evaluation_mode="Post-login exploratory pass grounded in browser captures, DOM snapshots, and page insights.",
            evaluation_lens=[
                "first-use clarity",
                "task initiation efficiency",
                "information architecture",
                "interaction load",
            ],
            score=score,
            overall_assessment=self._overall_assessment(score, strengths, issues),
            scope_paths=[context.label for context in contexts[:6]],
            scope_notes=self._scope_notes(contexts, analysis, extraction_results),
            strengths=strengths,
            issues=issues,
            new_user_judgment=self._new_user_judgment(score, strengths, issues),
            experienced_user_judgment=self._experienced_user_judgment(score, strengths, issues),
            recommendations=self._recommendations(issues),
            conclusion=self._conclusion(strengths, issues),
            visuals=self._visuals(contexts, strengths, issues),
        )

    def _snapshot_context(self, snapshot: StateSnapshot, insight: dict) -> UXSnapshotContext:
        label = best_surface_label(
            url=snapshot.url,
            title=snapshot.title,
            capture_label=str(snapshot.metadata.get("capture_label", "")).strip(),
            fallback="Captured surface",
        )
        page_type = self._page_type(snapshot, insight)
        dom = self._extract_dom_signals(Path(snapshot.html_path))
        interaction_hints = [
            clean_report_text(str(item.get("label", "")))
            for item in (insight.get("interaction_hints") or [])
        ]
        interaction_hints = [item for item in interaction_hints if item]
        concepts = self._detect_concepts([dom["text_blob"], *dom["action_labels"], *dom["headings"], *interaction_hints])
        return UXSnapshotContext(
            snapshot=snapshot,
            label=label,
            page_type=page_type,
            route_family=route_family_from_url(snapshot.url),
            headings=dom["headings"],
            action_labels=dom["action_labels"],
            input_prompts=dom["input_prompts"],
            interaction_hints=interaction_hints,
            concepts=concepts,
            has_contenteditable=dom["has_contenteditable"],
            has_upgrade_cta=dom["has_upgrade_cta"],
            text_blob=dom["text_blob"],
        )

    def _extract_dom_signals(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {
                "headings": [],
                "action_labels": [],
                "input_prompts": [],
                "has_contenteditable": False,
                "has_upgrade_cta": False,
                "text_blob": "",
            }

        html = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        headings = self._collect_texts(soup.select("h1, h2, h3, h4"), limit=10)
        action_labels = self._collect_texts(
            soup.select("button, a, [role='button'], [data-testid*='button']"),
            limit=24,
        )
        input_prompts = self._collect_input_prompts(soup)
        text_blob = " ".join(
            [*headings, *action_labels, *input_prompts, clean_report_text(soup.get_text(" ", strip=True)[:4000])]
        ).strip()

        contenteditable_nodes = soup.select("[contenteditable='true']")
        has_contenteditable = bool(contenteditable_nodes)
        has_upgrade_cta = any(self._contains_any(text, ("upgrade", "pricing", "升级", "订阅")) for text in action_labels)

        return {
            "headings": headings,
            "action_labels": action_labels,
            "input_prompts": input_prompts,
            "has_contenteditable": has_contenteditable,
            "has_upgrade_cta": has_upgrade_cta,
            "text_blob": text_blob,
        }

    def _collect_texts(self, elements: Iterable, limit: int) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for element in elements:
            text = clean_report_text(element.get_text(" ", strip=True))
            if not text:
                text = clean_report_text(
                    element.get("aria-label") or element.get("title") or ""
                )
            if not text or len(text) > 80 or text in seen:
                continue
            seen.add(text)
            items.append(text)
            if len(items) >= limit:
                break
        return items

    def _collect_input_prompts(self, soup: BeautifulSoup) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for element in soup.select("input, textarea, [contenteditable='true']"):
            for candidate in (
                element.get("placeholder"),
                element.get("data-placeholder"),
                element.get("aria-label"),
                element.get_text(" ", strip=True),
            ):
                text = clean_report_text(str(candidate or ""))
                if not text or len(text) > 120 or text in seen:
                    continue
                seen.add(text)
                items.append(text)
                break
            if len(items) >= 12:
                break
        return items

    def _page_type(self, snapshot: StateSnapshot, insight: dict) -> str:
        page_type_vision = clean_report_text(str(insight.get("page_type_vision", "")))
        if page_type_vision and page_type_vision != "unknown":
            return display_label(page_type_vision)
        page_type_dom = clean_report_text(str(insight.get("page_type_dom", "")))
        if page_type_dom:
            return display_label(page_type_dom)
        return display_label(route_family_from_url(snapshot.url))

    def _detect_concepts(self, texts: Iterable[str]) -> list[str]:
        blob = " ".join(clean_report_text(text).lower() for text in texts if clean_report_text(text))
        concepts: list[str] = []
        for concept, keywords in self.CONCEPT_MAP.items():
            if any(keyword.lower() in blob for keyword in keywords):
                concepts.append(concept)
        return concepts

    def _strengths(self, contexts: list[UXSnapshotContext]) -> list[UXReviewFinding]:
        strengths: list[UXReviewFinding] = []
        entry = contexts[0] if contexts else None
        if entry:
            primary_actions = self._salient_actions(entry.action_labels)
            categories = self._capability_categories(primary_actions + entry.input_prompts)
            if len(categories) >= 2 and len(primary_actions) >= 3:
                sample = ", ".join(f"`{label}`" for label in primary_actions[:5])
                strengths.append(
                    UXReviewFinding(
                        key="entry_capability_clarity",
                        title="The first workspace makes product breadth visible quickly",
                        summary=(
                            "The opening surface immediately signals that the product is more than a single chat box. "
                            "Users can see multiple starting modes without digging through menus."
                        ),
                        why_it_matters="A broad capability surface can create early confidence that the tool can handle different types of knowledge work.",
                        evidence=[
                            f"`{entry.label}` exposes visible starting points such as {sample}.",
                            *self._hint_evidence(entry, limit=2),
                        ],
                        related_urls=[entry.snapshot.url],
                    )
                )

        workspace = self._first_matching(contexts, lambda item: item.page_type == "Dashboard" and bool(item.action_labels))
        if workspace and len(workspace.action_labels) >= 4 and (workspace.input_prompts or workspace.interaction_hints):
            strengths.append(
                UXReviewFinding(
                    key="blank_state_guidance",
                    title="Blank-state and onboarding cues reduce dead-screen uncertainty",
                    summary=(
                        "The initial workspace does not feel empty in a broken or abandoned way. "
                        "The page offers a prompt field, visible actions, and onboarding hints that tell the user what to do next."
                    ),
                    why_it_matters="First-time users tolerate complexity better when the screen still communicates a next action instead of a void.",
                    evidence=[
                        *[f"Input prompt: `{prompt}`." for prompt in workspace.input_prompts[:2]],
                        *self._hint_evidence(workspace, limit=2),
                    ],
                    related_urls=[workspace.snapshot.url],
                )
            )

        if any(len(context.interaction_hints) >= 2 for context in contexts):
            exemplar = max(contexts, key=lambda item: len(item.interaction_hints), default=None)
            if exemplar:
                strengths.append(
                    UXReviewFinding(
                        key="next_step_discoverability",
                        title="Visible next-step cues make the workspace reasonably self-explanatory",
                        summary=(
                            "Across the captured screens, the interface usually exposes what the next move is supposed to be, "
                            "whether that means switching sections, starting from files, or opening a deeper workspace."
                        ),
                        why_it_matters="Strong next-step cues improve learnability even when the product surface is broad.",
                        evidence=self._hint_evidence(exemplar, limit=3),
                        related_urls=[exemplar.snapshot.url],
                    )
                )

        if any(context.has_upgrade_cta for context in contexts) and any(
            "research" in " ".join(context.action_labels).lower() or "研究" in context.text_blob for context in contexts
        ):
            strengths.append(
                UXReviewFinding(
                    key="workflow_breadth",
                    title="The product already reads like a real workbench, not a single-purpose tool",
                    summary=(
                        "The captured surfaces suggest that the product is trying to unify asking questions, importing sources, deeper research, and output-oriented work in one place."
                    ),
                    why_it_matters="That breadth can become a strong differentiator for repeat users if the product also improves its guidance layer.",
                    evidence=[
                        f"Observed route scope included {', '.join(f'`{context.label}`' for context in contexts[:4])}.",
                    ],
                    related_urls=[context.snapshot.url for context in contexts[:4]],
                )
            )

        return strengths[:4]

    def _issues(self, contexts: list[UXSnapshotContext]) -> list[UXReviewFinding]:
        issues: list[UXReviewFinding] = []
        entry = contexts[0] if contexts else None
        if entry:
            primary_actions = self._salient_actions(entry.action_labels)
            categories = self._capability_categories(primary_actions + entry.input_prompts)
            if len(categories) >= 2 and len(primary_actions) >= 4:
                sample = ", ".join(f"`{label}`" for label in primary_actions[:6])
                issues.append(
                    UXReviewFinding(
                        key="entry_overload",
                        title="The first screen offers too many equally weighted starting points",
                        summary=(
                            "The opening workspace surfaces several ways to begin, but it does not clearly establish one primary path for a first-time user."
                        ),
                        why_it_matters="When many options look equally primary, users pay the cost of choosing before they have learned the product model.",
                        evidence=[
                            f"`{entry.label}` shows competing start points such as {sample}.",
                            *self._hint_evidence(entry, limit=1),
                        ],
                        related_urls=[entry.snapshot.url],
                    )
                )

        all_concepts = sorted({concept for context in contexts for concept in context.concepts})
        if len(all_concepts) >= 4:
            concept_text = ", ".join(f"`{concept}`" for concept in all_concepts[:6])
            related = self._urls_with_concepts(contexts, all_concepts[:4])
            issues.append(
                UXReviewFinding(
                    key="concept_density",
                    title="The object model becomes visible faster than it becomes understandable",
                    summary=(
                        "The product exposes several core nouns early, but the relationship between those concepts is not obvious from the captured surfaces alone."
                    ),
                    why_it_matters="Users can handle many concepts if the hierarchy is clear; they struggle when the concepts appear before the mental model does.",
                    evidence=[
                        f"Concepts visible across the captured surfaces include {concept_text}.",
                    ],
                    related_urls=related,
                )
            )

        crowded_workspace = self._first_matching(
            contexts,
            lambda item: item.page_type == "Dashboard" and len(self._salient_actions(item.action_labels)) >= 4 and len(item.input_prompts) >= 1,
        )
        if crowded_workspace:
            visible_actions = self._salient_actions(crowded_workspace.action_labels)
            issues.append(
                UXReviewFinding(
                    key="workspace_density",
                    title="The workspace asks users to parse too much UI before they do one thing",
                    summary=(
                        "The captured dashboard surfaces expose multiple navigation concepts, action buttons, and monetization cues at once. "
                        "That creates a strong power-user feel, but also raises the first-run comprehension cost."
                    ),
                    why_it_matters="A high-density workspace can feel capable and intimidating at the same time; without progressive disclosure it slows task initiation.",
                    evidence=[
                        f"`{crowded_workspace.label}` includes visible actions such as {', '.join(f'`{label}`' for label in visible_actions[:5])}.",
                        *self._hint_evidence(crowded_workspace, limit=2),
                    ],
                    related_urls=[crowded_workspace.snapshot.url],
                )
            )

        input_issue = self._first_matching(contexts, lambda item: item.has_contenteditable and bool(item.input_prompts))
        if input_issue:
            issues.append(
                UXReviewFinding(
                    key="input_affordance",
                    title="The primary input relies on a light-weight contenteditable affordance",
                    summary=(
                        "The main task-entry area appears to be implemented as a contenteditable surface with placeholder-style guidance, "
                        "rather than a strongly framed input with explicit semantics."
                    ),
                    why_it_matters="This can weaken both perceived affordance and accessibility, especially for users who are unsure where to start typing.",
                    evidence=[
                        *[f"Observed input prompt: `{prompt}`." for prompt in input_issue.input_prompts[:2]],
                    ],
                    related_urls=[input_issue.snapshot.url],
                )
            )

        repeated_upgrade = [context for context in contexts if context.has_upgrade_cta]
        if len(repeated_upgrade) >= 2:
            issues.append(
                UXReviewFinding(
                    key="upgrade_pressure",
                    title="Upgrade messaging stays visible during core work surfaces",
                    summary=(
                        "Pricing and plan-upgrade cues remain visible across multiple in-product screens, even while the user is still learning the workspace."
                    ),
                    why_it_matters="Persistent monetization cues are not inherently bad, but they can compete with onboarding attention during the first-run experience.",
                    evidence=[
                        f"Upgrade or plan text appears on {len(repeated_upgrade)} captured surfaces, including {', '.join(f'`{context.label}`' for context in repeated_upgrade[:3])}.",
                    ],
                    related_urls=[context.snapshot.url for context in repeated_upgrade[:3]],
                )
            )

        return issues[:5]

    def _score(self, strengths: list[UXReviewFinding], issues: list[UXReviewFinding]) -> float:
        score = 7.0
        strength_weights = {
            "entry_capability_clarity": 0.4,
            "blank_state_guidance": 0.3,
            "next_step_discoverability": 0.4,
            "workflow_breadth": 0.3,
        }
        issue_weights = {
            "entry_overload": 0.8,
            "concept_density": 0.7,
            "workspace_density": 0.7,
            "input_affordance": 0.5,
            "upgrade_pressure": 0.3,
        }
        score += sum(strength_weights.get(item.key, 0.2) for item in strengths)
        score -= sum(issue_weights.get(item.key, 0.3) for item in issues)
        return round(max(4.5, min(score, 8.8)), 1)

    def _overall_assessment(
        self,
        score: float,
        strengths: list[UXReviewFinding],
        issues: list[UXReviewFinding],
    ) -> str:
        issue_keys = {item.key for item in issues}
        if {"entry_overload", "workspace_density"} & issue_keys:
            return (
                f"`{score:.1f} / 10`. The product already feels capable and ambitious, but the first-run experience still behaves more like a dense professional workbench than a clearly guided starting surface."
            )
        return f"`{score:.1f} / 10`. The captured experience is directionally strong, but still leaves visible gaps in guidance and workflow clarity."

    def _scope_notes(
        self,
        contexts: list[UXSnapshotContext],
        analysis: CompetitiveAnalysis,
        extraction_results: dict[str, dict],
    ) -> list[str]:
        notes: list[str] = []
        if contexts:
            notes.append(
                "Visited path set: " + ", ".join(f"`{context.label}`" for context in contexts[:6]) + "."
            )
        if not any("auth" in context.page_type.lower() for context in contexts):
            notes.append("No standalone sign-in or onboarding capture was included in the reviewed states; this pass is strongest on post-login UX.")
        if all(str(context.snapshot.metadata.get("capture_context", "")).lower() == "route" for context in contexts):
            notes.append("The run stayed mostly in route-to-route navigation; it did not complete a deep task flow such as prompt submission, file import, or end-to-end research execution.")
        successful_extractions = sum(1 for result in extraction_results.values() if result.get("status") == "success")
        if extraction_results and successful_extractions == 0:
            notes.append("Structured extraction was shallow on this pass, so the review leans more on interface evidence than content semantics.")
        if len(contexts) <= 6:
            notes.append("This was still a small-budget pass, so the findings should be treated as grounded but not exhaustive.")
        return notes[:4]

    def _new_user_judgment(
        self,
        score: float,
        strengths: list[UXReviewFinding],
        issues: list[UXReviewFinding],
    ) -> str:
        issue_keys = {item.key for item in issues}
        if "entry_overload" in issue_keys or "concept_density" in issue_keys:
            return (
                "New users are likely to feel that the product is powerful before they feel that it is easy to start. "
                "The opening workspace shows breadth and momentum, but it also asks them to choose and interpret several concepts at once."
            )
        return (
            "New users should be able to recognize the product's core purpose quickly, though deeper workflow confidence would still benefit from more guided first-run sequencing."
        )

    def _experienced_user_judgment(
        self,
        score: float,
        strengths: list[UXReviewFinding],
        issues: list[UXReviewFinding],
    ) -> str:
        if any(item.key in {"workspace_density", "workflow_breadth"} for item in strengths + issues):
            return (
                "Experienced or research-heavy users are more likely to appreciate the dense workbench model, because the same complexity that slows first-run onboarding also increases perceived flexibility."
            )
        return (
            "Experienced users would probably adapt quickly, but the current captures are not yet rich enough to judge advanced workflow efficiency confidently."
        )

    def _recommendations(self, issues: list[UXReviewFinding]) -> list[UXRecommendation]:
        items: list[UXRecommendation] = []
        issue_keys = [item.key for item in issues]
        if "entry_overload" in issue_keys:
            items.append(
                UXRecommendation(
                    title="Establish a single first-run start path",
                    action="Promote one clear primary CTA on the first workspace, and demote the other starting modes into secondary or templated options.",
                    rationale="This directly lowers choice cost on the first screen without removing product breadth.",
                )
            )
        if "concept_density" in issue_keys:
            items.append(
                UXRecommendation(
                    title="Explain the object model in-place",
                    action="Add short explanatory copy or lightweight affordances that clarify how concepts such as project, board, document, agent, editor, or playground relate to each other.",
                    rationale="Users can tolerate many concepts if the hierarchy is made explicit at the moment they encounter it.",
                )
            )
        if "workspace_density" in issue_keys:
            items.append(
                UXRecommendation(
                    title="Use progressive disclosure on the initial workspace",
                    action="Show the smallest useful set of first actions up front, and reveal advanced workspace controls after the user begins a task.",
                    rationale="This preserves power-user depth while reducing first-run cognitive load.",
                )
            )
        if "input_affordance" in issue_keys:
            items.append(
                UXRecommendation(
                    title="Strengthen the primary input affordance",
                    action="Give the main input a clearer visual frame and stronger accessible semantics rather than relying mostly on placeholder-style guidance inside a contenteditable region.",
                    rationale="A stronger input affordance improves both confidence and accessibility for first-time users.",
                )
            )
        if "upgrade_pressure" in issue_keys:
            items.append(
                UXRecommendation(
                    title="Reduce monetization competition during onboarding moments",
                    action="Keep upgrade messaging present but visually subordinate while the user is still learning the primary workspace.",
                    rationale="This helps early attention stay on task initiation rather than pricing posture.",
                )
            )
        return items[:5]

    def _conclusion(self, strengths: list[UXReviewFinding], issues: list[UXReviewFinding]) -> str:
        issue_keys = {item.key for item in issues}
        if {"entry_overload", "concept_density", "workspace_density"} & issue_keys:
            return (
                "The captured experience suggests a product that is already broad and serious, but still easier to admire than to enter smoothly. "
                "The most valuable next step is not adding more capability; it is making the first-run path simpler, clearer, and more opinionated."
            )
        return (
            "The captured experience suggests a promising product shape, but the next round of UX evidence should focus on one deeper task flow so the review can move beyond surface judgment."
        )

    def _visuals(
        self,
        contexts: list[UXSnapshotContext],
        strengths: list[UXReviewFinding],
        issues: list[UXReviewFinding],
    ) -> list[UXVisual]:
        visuals: list[UXVisual] = []
        related_order = [
            *(url for item in issues for url in item.related_urls),
            *(url for item in strengths for url in item.related_urls),
        ]
        seen_urls: set[str] = set()
        for url in related_order:
            context = self._first_matching(contexts, lambda item, url=url: item.snapshot.url == url)
            if not context or url in seen_urls:
                continue
            screenshot_path = context.screenshot_path
            if not screenshot_path or not Path(screenshot_path).exists():
                continue
            seen_urls.add(url)
            visuals.append(
                UXVisual(
                    title=context.label,
                    summary=f"{context.label} ({context.page_type})",
                    caption=self._visual_caption(context),
                    image_path=screenshot_path,
                    related_key=self._visual_related_key(context, strengths, issues),
                )
            )
            if len(visuals) >= 4:
                break
        return visuals

    def _visual_caption(self, context: UXSnapshotContext) -> str:
        if context.interaction_hints:
            return "Key visible cue: " + context.interaction_hints[0]
        if context.input_prompts:
            return "Key input cue: " + context.input_prompts[0]
        if context.action_labels:
            return "Visible actions include " + ", ".join(f"`{label}`" for label in context.action_labels[:3]) + "."
        return "Representative captured surface."

    def _visual_related_key(
        self,
        context: UXSnapshotContext,
        strengths: list[UXReviewFinding],
        issues: list[UXReviewFinding],
    ) -> str:
        for item in issues + strengths:
            if context.snapshot.url in item.related_urls:
                return item.key
        return "general"

    def _hint_evidence(self, context: UXSnapshotContext, limit: int) -> list[str]:
        return [f"Observed hint: `{item}`." for item in context.interaction_hints[:limit]]

    def _salient_actions(self, labels: list[str]) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for label in labels:
            text = clean_report_text(label)
            if not text or text in seen or self._is_low_signal_action(text):
                continue
            seen.add(text)
            items.append(text)
        return items

    def _is_low_signal_action(self, text: str) -> bool:
        lowered = clean_report_text(text).lower()
        if not lowered:
            return True
        low_signal_keywords = (
            "upgrade",
            "pricing",
            "free",
            "subscribe",
            "billing",
            "return",
            "back",
            "legacy",
            "home",
            "profile",
            "account",
            "settings",
            "help",
            "立即升级",
            "升级",
            "订阅",
            "返回",
            "旧版",
            "首页",
            "设置",
            "帮助",
        )
        return any(keyword in lowered for keyword in low_signal_keywords)

    def _urls_with_concepts(self, contexts: list[UXSnapshotContext], concepts: list[str]) -> list[str]:
        related: list[str] = []
        wanted = set(concepts)
        for context in contexts:
            if wanted.intersection(context.concepts):
                related.append(context.snapshot.url)
        return related[:3]

    def _capability_categories(self, texts: Iterable[str]) -> set[str]:
        categories: set[str] = set()
        for text in texts:
            lowered = clean_report_text(text).lower()
            for category, keywords in self.CAPABILITY_KEYWORDS.items():
                if any(keyword.lower() in lowered for keyword in keywords):
                    categories.add(category)
        return categories

    def _contains_any(self, text: str, keywords: Iterable[str]) -> bool:
        lowered = clean_report_text(text).lower()
        return any(keyword.lower() in lowered for keyword in keywords)

    def _first_matching(self, items: Iterable[UXSnapshotContext], predicate) -> UXSnapshotContext | None:
        for item in items:
            if predicate(item):
                return item
        return None

    def _insights_by_url(self, page_insights: dict[str, dict]) -> dict[str, dict]:
        deduped: dict[str, dict] = {}
        for insight in page_insights.values():
            url = str(insight.get("url", "")).strip()
            if not url:
                continue
            current = deduped.get(url)
            if current is None:
                deduped[url] = insight
                continue
            current_id = str(current.get("state_id", ""))
            candidate_id = str(insight.get("state_id", ""))
            if current_id.startswith("observe_") and not candidate_id.startswith("observe_"):
                deduped[url] = insight
        return deduped
