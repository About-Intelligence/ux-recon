# Architecture: Frontend Mimic Agent Framework

> A budget-aware, policy-driven browser agent framework for autonomous website exploration,
> artifact collection, and selective analysis — optimized for admin dashboards, LIMS, ERP,
> and SaaS management applications.

## Three-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│  REASONING LAYER (external — Claude/ChatGPT via conversation)│
│  - Selective deep analysis                                   │
│  - Architecture summarization                                │
│  - Frontend replication                                      │
│  - Triggered only when justified by novelty/budget           │
└──────────────────────────┬──────────────────────────────────┘
                           │ handoff (structured artifacts)
┌──────────────────────────▼──────────────────────────────────┐
│  OBSERVATION LAYER (Python — deterministic)                  │
│  - Page metadata extraction                                  │
│  - Candidate interaction detection                           │
│  - DOM structural fingerprinting                             │
│  - Novelty scoring (cheap signals)                           │
│  - Component/pattern detection                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ data
┌──────────────────────────▼──────────────────────────────────┐
│  EXECUTION LAYER (Playwright — browser control)              │
│  - Navigate, click, wait, scroll                             │
│  - Screenshot capture                                        │
│  - HTML/DOM capture                                          │
│  - Route transitions                                         │
│  - Login/authentication                                      │
└─────────────────────────────────────────────────────────────┘
```

## State Machine

8 states, simple enum FSM with a `while` loop:

```
    ┌──────────┐
    │INITIALIZE│
    └────┬─────┘
         ▼
    ┌──────────┐
    │AUTHENTICATE│
    └────┬─────┘
         ▼
    ┌──────────┐◄─────────────────────────────┐
    │ OBSERVE  │  (extract page signals,       │
    │          │   detect candidates)           │
    └────┬─────┘                               │
         ▼                                     │
    ┌──────────────┐                           │
    │SELECT_ACTION │  (pick next from frontier, │
    │              │   check budget/stop)       │
    └────┬────┬────┘                           │
         │    │ (budget exhausted              │
         │    │  or frontier empty)            │
         ▼    ▼                                │
    ┌────────┐ ┌──────────┐                    │
    │EXECUTE │ │ FINALIZE │                    │
    │        │ └──────────┘                    │
    └────┬───┘                                 │
         ▼                                     │
    ┌──────────────┐                           │
    │EVAL_NOVELTY  │  (is this state new       │
    │              │   or near-duplicate?)      │
    └────┬────┬────┘                           │
         │    │ (low novelty → skip deep)      │
         ▼    ▼                                │
    ┌─────────┐  ┌───────────────────┐         │
    │ ANALYZE │  │BACKTRACK_CONTINUE │─────────┘
    │(optional│  └───────────────────┘
    │ deep)   │─────────────────────────────────┘
    └─────────┘
```

### State Details

| State | What happens | Deterministic? |
|-------|-------------|----------------|
| INITIALIZE | Load config, create output dirs, launch browser | Yes |
| AUTHENTICATE | Login using configured selectors | Yes |
| OBSERVE | Extract metadata, find candidate interactions, compute DOM fingerprint | Yes |
| SELECT_ACTION | Pick next target from frontier (BFS), check budget/stop conditions | Yes |
| EXECUTE | Navigate/click/scroll, capture screenshot + HTML | Yes |
| EVAL_NOVELTY | Compare DOM fingerprint to seen states, score novelty | Yes |
| ANALYZE | Local DOM analysis (components, layout, design tokens). Deep analysis flagged for LLM handoff | Mostly yes |
| BACKTRACK_CONTINUE | Pop back to parent context or continue frontier | Yes |
| FINALIZE | Generate artifacts, write reports, package handoff | Yes |

## Folder Structure

```
frontend_mimic/
├── config/
│   ├── settings.yaml              # Default config
│   └── settings.local.yaml        # User overrides (gitignored)
├── src/
│   ├── __init__.py
│   ├── cli.py                     # Thin CLI entry point
│   │
│   ├── agent/                     # Core agent framework
│   │   ├── __init__.py
│   │   ├── engine.py              # State machine loop + orchestration
│   │   ├── state.py               # AgentState, enums, frontier management
│   │   └── logger.py              # Structured run log (JSONL)
│   │
│   ├── browser/                   # Execution layer
│   │   ├── __init__.py
│   │   ├── controller.py          # Playwright lifecycle (launch/close/navigate)
│   │   └── authenticator.py       # Login flow (separated for reuse)
│   │
│   ├── observer/                  # Observation layer
│   │   ├── __init__.py
│   │   ├── extractor.py           # Page metadata, candidate detection
│   │   ├── fingerprint.py         # DOM structural fingerprinting
│   │   └── novelty.py             # Novelty scoring (cheap signals)
│   │
│   ├── analyzer/                  # Local analysis (no LLM)
│   │   ├── __init__.py
│   │   └── page_analyzer.py       # Component detection, design tokens, layout
│   │
│   ├── artifacts/                 # Output generation
│   │   ├── __init__.py
│   │   ├── manager.py             # Artifact save/load, path management
│   │   ├── inventory.py           # Page/state inventory
│   │   ├── sitemap.py             # Traversal graph / site map
│   │   └── report.py              # Final consolidated report (markdown)
│   │
│   └── config.py                  # Pydantic models, YAML loader
│
├── output/                        # All run outputs (gitignored)
│   ├── screenshots/
│   ├── dom_snapshots/
│   ├── artifacts/
│   │   ├── inventory.json         # Page inventory
│   │   ├── sitemap.json           # Traversal graph
│   │   ├── run_log.jsonl          # Execution log
│   │   └── analysis/              # Per-state analysis results
│   │       ├── state_001.json
│   │       └── ...
│   └── reports/
│       └── exploration_report.md  # Final human-readable report
│
├── requirements.txt
├── pyproject.toml
├── README.md
└── ARCHITECTURE.md                # This file
```

## Core Data Models

```python
# ── Enums ──

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
    SKIPPED = "skipped"       # low novelty or budget exhausted

class ActionType(str, Enum):
    NAVIGATE = "navigate"     # click sidebar/nav link → new route
    CLICK_ACTION = "click_action"  # click action dropdown item
    OPEN_MODAL = "open_modal"      # click add/edit button → modal
    EXPAND_ROW = "expand_row"      # expand table row
    SWITCH_TAB = "switch_tab"      # click tab
    SCROLL = "scroll"
    BACKTRACK = "backtrack"

class TargetType(str, Enum):
    ROUTE = "route"           # URL/hash change
    MODAL = "modal"           # dialog/drawer overlay
    TAB_STATE = "tab_state"   # same page, different tab
    EXPANDED_ROW = "expanded_row"
    DROPDOWN = "dropdown"     # action menu opened
    SECTION = "section"       # scroll-to section

# ── Core Models ──

class ExplorationTarget:
    """Something the agent can navigate to or interact with."""
    id: str                   # unique identifier
    target_type: TargetType
    locator: str              # CSS selector or URL
    label: str                # human-readable name (menu text, button text)
    parent_id: str | None     # parent target (for hierarchy)
    depth: int                # distance from root
    discovery_method: str     # "sidebar_menu", "action_dropdown", "tab_bar", etc.
    metadata: dict            # extra info (href, aria-label, etc.)

class StateSnapshot:
    """A captured state of the browser at a point in time."""
    id: str                   # e.g. "state_001"
    target_id: str            # which ExplorationTarget produced this
    url: str
    title: str
    timestamp: datetime
    screenshot_path: str
    html_path: str
    dom_fingerprint: str      # structural hash for novelty comparison
    visit_status: VisitStatus
    novelty_score: float      # 0.0 = exact duplicate, 1.0 = completely new
    parent_state_id: str | None
    depth: int
    retry_count: int
    error: str | None
    metadata: dict            # extracted signals (element counts, text density, etc.)

class TraversalEdge:
    """A transition between two states."""
    from_state_id: str
    to_state_id: str
    action: ActionType
    locator: str
    label: str
    timestamp: datetime

class RunLogEntry:
    """One line in the execution log."""
    step: int
    timestamp: datetime
    phase: AgentPhase
    action: str               # human-readable description
    target: str               # what was acted on
    result: str               # "success", "failed", "skipped", "retry"
    reason: str               # why this result
    duration_ms: int

class AgentState:
    """The agent's full runtime state (serializable for resume)."""
    phase: AgentPhase
    current_state_id: str | None
    frontier: deque[str]      # BFS queue of target IDs
    visited: set[str]         # target IDs already processed
    skipped: set[str]         # target IDs skipped (low novelty / budget)
    failed: dict[str, int]    # target_id → retry count
    states: dict[str, StateSnapshot]
    targets: dict[str, ExplorationTarget]
    edges: list[TraversalEdge]
    budget_remaining: int     # max states to capture
    step_counter: int
```

## Module Responsibilities

### Deterministic (no LLM, always runs)

| Module | Responsibility |
|--------|---------------|
| `agent/engine.py` | State machine loop. Calls other modules per phase. |
| `agent/state.py` | AgentState management, frontier ops, visited tracking |
| `agent/logger.py` | Append RunLogEntry to JSONL file |
| `browser/controller.py` | Playwright launch/close, navigate, click, screenshot, save HTML |
| `browser/authenticator.py` | Login flow using configured selectors |
| `observer/extractor.py` | Find candidate interactions on current page (nav items, buttons, tabs, dropdowns) |
| `observer/fingerprint.py` | Generate DOM structural hash (tag tree, ignoring text content) |
| `observer/novelty.py` | Compare fingerprint to seen states, return novelty score 0-1 |
| `analyzer/page_analyzer.py` | Component detection, design tokens, layout pattern extraction |
| `artifacts/manager.py` | Save/load artifacts, manage output paths |
| `artifacts/inventory.py` | Generate page inventory JSON from agent state |
| `artifacts/sitemap.py` | Generate traversal graph JSON from targets + edges |
| `artifacts/report.py` | Generate markdown report from all artifacts |

### Configurable (behavior changes via settings.yaml)

| Setting | What it controls |
|---------|-----------------|
| `budget.max_states` | Total states to capture before stopping |
| `budget.max_depth` | Maximum BFS depth |
| `budget.novelty_threshold` | Below this score, skip deep analysis |
| `crawl.page_timeout` | How long to wait for page load |
| `crawl.retry_count` | Max retries per target |
| `interaction.selectors.*` | CSS selectors for detecting nav items, action buttons, modals, tabs |
| `exploration.skip_patterns` | URL patterns to skip (logout, external links) |
| `exploration.destructive_keywords` | Button text to never click |

### LLM-assisted (only via conversation handoff)

| What | When |
|------|------|
| Deep page interpretation | After run, when reviewing artifacts |
| Architecture summarization | Final report enrichment |
| Frontend replication | Separate conversation task |
| Policy tuning | "Go back and also check X, Y, Z" |

## Data Flow

```
Engine.run()
  │
  ├─ INITIALIZE
  │   └─ Controller.launch() → browser ready
  │
  ├─ AUTHENTICATE
  │   └─ Authenticator.login() → logged in
  │
  ├─ OBSERVE ◄──────────────────────────────────────┐
  │   ├─ Extractor.extract_candidates(page) → targets│
  │   ├─ Fingerprint.compute(page) → hash            │
  │   └─ AgentState.add_targets(targets)              │
  │                                                    │
  ├─ SELECT_ACTION                                     │
  │   ├─ AgentState.pop_frontier() → next target       │
  │   ├─ check budget remaining                        │
  │   └─ if empty/exhausted → FINALIZE                 │
  │                                                    │
  ├─ EXECUTE                                           │
  │   ├─ Controller.execute(target) → page state       │
  │   ├─ Controller.capture_screenshot() → png         │
  │   ├─ Controller.capture_html() → html              │
  │   └─ ArtifactManager.save(snapshot)                │
  │                                                    │
  ├─ EVAL_NOVELTY                                      │
  │   ├─ Fingerprint.compute(page) → new_hash          │
  │   ├─ Novelty.score(new_hash, seen_hashes) → score  │
  │   └─ if score < threshold → mark SKIPPED           │
  │                                                    │
  ├─ ANALYZE (if novelty > threshold)                  │
  │   ├─ PageAnalyzer.analyze(html) → components, etc. │
  │   └─ ArtifactManager.save_analysis(result)         │
  │                                                    │
  └─ BACKTRACK_CONTINUE ──────────────────────────────┘
      ├─ if target was overlay → close it, restore parent
      └─ continue to OBSERVE

  FINALIZE
  ├─ Inventory.generate(agent_state) → inventory.json
  ├─ Sitemap.generate(agent_state) → sitemap.json
  ├─ Report.generate(all_artifacts) → exploration_report.md
  └─ Logger.close() → run_log.jsonl complete
```

## Artifact Schemas

### inventory.json
```json
[
  {
    "id": "state_001",
    "target_id": "target_dashboard",
    "url": "https://example.com/#/dashboard",
    "title": "Dashboard",
    "target_type": "route",
    "parent_path": ["root"],
    "depth": 0,
    "discovery_method": "initial_page",
    "visit_status": "success",
    "novelty_score": 1.0,
    "screenshot": "screenshots/001_dashboard.png",
    "html": "dom_snapshots/001_dashboard.html",
    "analysis": "artifacts/analysis/state_001.json",
    "timestamp": "2026-03-22T14:30:00Z",
    "retries": 0,
    "error": null
  }
]
```

### sitemap.json
```json
{
  "nodes": [
    {"id": "target_dashboard", "label": "Dashboard", "type": "route", "depth": 0},
    {"id": "target_business_trust", "label": "委托单列表", "type": "route", "depth": 1, "parent": "target_business"}
  ],
  "edges": [
    {"from": "target_dashboard", "to": "target_business_trust", "action": "navigate", "label": "sidebar click"}
  ],
  "groups": [
    {"id": "target_business", "label": "业务管理", "children": ["target_business_trust", "target_business_task", "target_business_qc"]}
  ]
}
```

### run_log.jsonl
```json
{"step": 1, "timestamp": "2026-03-22T14:30:00Z", "phase": "initialize", "action": "launch_browser", "target": "", "result": "success", "reason": "chromium started", "duration_ms": 2340}
{"step": 2, "timestamp": "2026-03-22T14:30:02Z", "phase": "authenticate", "action": "login", "target": "https://example.com/#/login", "result": "success", "reason": "dashboard loaded", "duration_ms": 3210}
{"step": 3, "timestamp": "2026-03-22T14:30:05Z", "phase": "observe", "action": "extract_candidates", "target": "dashboard", "result": "success", "reason": "found 12 nav items", "duration_ms": 450}
```

### exploration_report.md
```markdown
# Exploration Report

## Run Summary
- Target: https://example.com
- Duration: 4m 32s
- States captured: 45 / 60 budget
- States skipped (low novelty): 8
- Failed: 2 (timeout)
- Unique routes: 28
- Interaction states: 17

## Site Architecture
[tree of discovered menu structure]

## Page Patterns
- 24/28 routes use table + card + pagination layout
- 16 pages have action dropdowns with 2-5 items
- 12 pages have add/create modals
- ...

## Coverage Gaps
- Settings page: access denied (role-restricted)
- Report export: skipped (destructive keyword "导出")

## Artifacts
- inventory.json: 45 entries
- sitemap.json: 28 nodes, 40 edges
- run_log.jsonl: 156 steps
- analysis/: 37 state analyses
```

## Implementation Plan

### Phase 1: Data Models + State Machine Shell
Files: `agent/state.py`, `agent/engine.py`, `agent/logger.py`, `config.py`
- All Pydantic/dataclass models
- Engine loop with phase transitions (no real browser yet, just structure)
- JSONL logger
- Updated config with budget/exploration settings

### Phase 2: Execution Layer
Files: `browser/controller.py`, `browser/authenticator.py`
- Refactor existing controller — strip out BFS/interaction logic
- Make it a clean "do this one thing" interface
- Authenticator extracted from controller

### Phase 3: Observation Layer
Files: `observer/extractor.py`, `observer/fingerprint.py`, `observer/novelty.py`
- Candidate extractor (find nav items, action buttons, tabs on current page)
- DOM fingerprinting (structural hash)
- Novelty scorer (compare hashes, return 0-1)

### Phase 4: Wire It Together
Files: `agent/engine.py` (complete), `cli.py`
- Connect engine to real browser + observer
- BFS frontier management
- Retry/backtrack logic
- CLI entry point

### Phase 5: Artifact Generation
Files: `artifacts/manager.py`, `artifacts/inventory.py`, `artifacts/sitemap.py`, `artifacts/report.py`
- Inventory from agent state
- Site map from targets + edges
- Markdown report
- Analysis outputs per state

### Phase 6: Analyzer Integration
Files: `analyzer/page_analyzer.py`
- Port existing analyzer (component detection, design tokens)
- Hook into ANALYZE phase
- Per-state analysis output files

### Phase 7: Testing + Polish
- Test on labverix.com
- Fix edge cases
- Update README
- Clean up old code
