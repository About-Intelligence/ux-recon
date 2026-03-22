"""Agent state management — data models, enums, frontier tracking."""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentPhase(str, Enum):
    INITIALIZE = "initialize"
    AUTHENTICATE = "authenticate"
    OBSERVE = "observe"
    SELECT_ACTION = "select_action"
    EXECUTE = "execute"
    EVAL_NOVELTY = "eval_novelty"
    ANALYZE = "analyze"
    BACKTRACK_CONTINUE = "backtrack_continue"
    FINALIZE = "finalize"


class VisitStatus(str, Enum):
    PENDING = "pending"
    VISITING = "visiting"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK_ACTION = "click_action"
    CLICK_DROPDOWN_ITEM = "click_dropdown_item"
    OPEN_MODAL = "open_modal"
    EXPAND_ROW = "expand_row"
    SWITCH_TAB = "switch_tab"
    SCROLL = "scroll"
    BACKTRACK = "backtrack"


class TargetType(str, Enum):
    ROUTE = "route"
    MODAL = "modal"
    TAB_STATE = "tab_state"
    EXPANDED_ROW = "expanded_row"
    DROPDOWN = "dropdown"
    DROPDOWN_ITEM = "dropdown_item"
    SECTION = "section"


def _make_id(prefix: str = "") -> str:
    """Generate a short unique ID."""
    short = uuid.uuid4().hex[:8]
    return f"{prefix}_{short}" if prefix else short


@dataclass
class PageCoverage:
    """Tracks what interactive elements exist on a page vs what was explored."""
    page_url: str = ""
    page_label: str = ""
    target_id: str = ""  # which target this page corresponds to
    nav_items_found: int = 0
    nav_items_explored: int = 0
    action_buttons_found: int = 0
    action_buttons_clicked: int = 0
    dropdown_items_found: int = 0
    dropdown_items_explored: int = 0
    add_buttons_found: int = 0
    add_buttons_clicked: int = 0
    tabs_found: int = 0
    tabs_switched: int = 0
    expand_rows_found: int = 0
    expand_rows_expanded: int = 0
    dropdown_item_labels: list[str] = field(default_factory=list)
    tab_labels: list[str] = field(default_factory=list)

    @property
    def has_unexplored(self) -> bool:
        return (self.dropdown_items_found > self.dropdown_items_explored
                or self.tabs_found > self.tabs_switched
                or self.expand_rows_found > self.expand_rows_expanded
                or self.add_buttons_found > self.add_buttons_clicked)


@dataclass
class ExplorationTarget:
    """Something the agent can navigate to or interact with."""
    id: str
    target_type: TargetType
    locator: str  # CSS selector or URL
    label: str  # human-readable name
    parent_id: str | None = None
    depth: int = 0
    discovery_method: str = ""  # e.g. "sidebar_menu", "action_dropdown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, target_type: TargetType, locator: str, label: str, **kwargs) -> ExplorationTarget:
        return cls(id=_make_id("target"), target_type=target_type, locator=locator, label=label, **kwargs)


@dataclass
class StateSnapshot:
    """A captured state of the browser at a point in time."""
    id: str
    target_id: str
    url: str = ""
    title: str = ""
    timestamp: str = ""  # ISO format
    screenshot_path: str = ""
    html_path: str = ""
    dom_fingerprint: str = ""
    visit_status: VisitStatus = VisitStatus.PENDING
    novelty_score: float = 1.0
    parent_state_id: str | None = None
    depth: int = 0
    retry_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, target_id: str, **kwargs) -> StateSnapshot:
        return cls(
            id=_make_id("state"),
            target_id=target_id,
            timestamp=datetime.now().isoformat(),
            **kwargs,
        )


@dataclass
class TraversalEdge:
    """A transition between two states."""
    from_state_id: str
    to_state_id: str
    action: ActionType
    locator: str = ""
    label: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentState:
    """The agent's full runtime state."""

    def __init__(self, budget: int = 100, max_depth: int = 5):
        self.phase: AgentPhase = AgentPhase.INITIALIZE
        self.current_state_id: str | None = None
        self.current_target_id: str | None = None

        # Frontier (BFS queue of target IDs)
        self.frontier: deque[str] = deque()

        # Tracking sets
        self.visited: set[str] = set()  # target IDs processed
        self.skipped: set[str] = set()  # target IDs skipped (low novelty / budget)
        self.failed: dict[str, int] = {}  # target_id -> retry count

        # Registries
        self.targets: dict[str, ExplorationTarget] = {}
        self.states: dict[str, StateSnapshot] = {}
        self.edges: list[TraversalEdge] = []

        # Budget
        self.budget_total: int = budget
        self.budget_remaining: int = budget
        self.max_depth: int = max_depth

        # Counters
        self.step_counter: int = 0

        # Fingerprints seen (for novelty)
        self.seen_fingerprints: list[str] = []

        # Coverage tracking per page (target_id -> PageCoverage)
        self.coverage: dict[str, PageCoverage] = {}

        # Track which URLs have been fully observed (candidates extracted)
        self.observed_urls: set[str] = set()

        # Navigation stack for backtracking
        self.nav_stack: list[str] = []  # stack of state IDs

        # Deduplication: dedup_key -> target_id
        self._dedup_map: dict[str, str] = {}

    def _dedup_key(self, target: ExplorationTarget) -> str:
        """Generate a deduplication key for a target.
        Same interaction on the same page should not create duplicate targets."""
        if target.target_type == TargetType.ROUTE:
            loc = target.locator
            if loc.startswith(("http", "#", "/")):
                return f"route:{loc}"

        # For interactions, find the parent route URL to dedup by page context
        parent_route = self._find_parent_route_label(target)

        if target.target_type == TargetType.DROPDOWN_ITEM:
            # Dedup by item text + parent route (not by dropdown target ID)
            item_text = target.metadata.get("item_text", target.label)
            return f"dropdown_item:{item_text}@{parent_route}"

        # For dropdowns, modals, tabs, expand rows: dedup by type + parent route
        # Strip @target_xxxx from label to get the base label
        import re
        base_label = re.sub(r'@target_[a-f0-9]+', '', target.label)
        return f"{target.target_type.value}:{base_label}@{parent_route}"

    def _find_parent_route_label(self, target: ExplorationTarget) -> str:
        """Walk up the parent chain to find the nearest route target's label."""
        current_id = target.parent_id
        visited: set[str] = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            parent = self.targets.get(current_id)
            if not parent:
                break
            if parent.target_type == TargetType.ROUTE:
                return parent.label
            current_id = parent.parent_id
        return "root"

    def add_target(self, target: ExplorationTarget) -> bool:
        """Add a target to the registry and frontier if not already known. Returns True if new."""
        if target.depth > self.max_depth:
            return False
        # Check dedup
        key = self._dedup_key(target)
        if key in self._dedup_map:
            return False
        self._dedup_map[key] = target.id
        self.targets[target.id] = target
        if target.id not in self.visited and target.id not in self.skipped:
            self.frontier.append(target.id)
        return True

    def add_targets(self, targets: list[ExplorationTarget]) -> int:
        """Add multiple targets. Returns count of newly added."""
        return sum(1 for t in targets if self.add_target(t))

    def pop_frontier(self) -> ExplorationTarget | None:
        """Pop next target from BFS frontier. Returns None if empty."""
        while self.frontier:
            target_id = self.frontier.popleft()
            if target_id not in self.visited and target_id not in self.skipped:
                return self.targets.get(target_id)
        return None

    def mark_visited(self, target_id: str) -> None:
        self.visited.add(target_id)

    def mark_skipped(self, target_id: str) -> None:
        self.skipped.add(target_id)

    def mark_failed(self, target_id: str) -> int:
        """Increment failure count, return new count."""
        self.failed[target_id] = self.failed.get(target_id, 0) + 1
        return self.failed[target_id]

    def consume_budget(self) -> bool:
        """Consume one budget unit. Returns False if exhausted."""
        if self.budget_remaining <= 0:
            return False
        self.budget_remaining -= 1
        return True

    def has_budget(self) -> bool:
        return self.budget_remaining > 0

    def next_step(self) -> int:
        """Increment and return step counter."""
        self.step_counter += 1
        return self.step_counter

    def register_state(self, snapshot: StateSnapshot) -> None:
        """Register a captured state."""
        self.states[snapshot.id] = snapshot

    def add_edge(self, from_id: str, to_id: str, action: ActionType, locator: str = "", label: str = "") -> None:
        self.edges.append(TraversalEdge(
            from_state_id=from_id, to_state_id=to_id,
            action=action, locator=locator, label=label,
        ))

    def push_nav(self, state_id: str) -> None:
        """Push state onto nav stack for backtracking."""
        self.nav_stack.append(state_id)

    def pop_nav(self) -> str | None:
        """Pop last state from nav stack."""
        return self.nav_stack.pop() if self.nav_stack else None

    def get_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        return {
            "total_targets": len(self.targets),
            "visited": len(self.visited),
            "skipped": len(self.skipped),
            "failed": len(self.failed),
            "frontier_remaining": len(self.frontier),
            "states_captured": len(self.states),
            "budget_used": self.budget_total - self.budget_remaining,
            "budget_remaining": self.budget_remaining,
            "steps": self.step_counter,
        }
