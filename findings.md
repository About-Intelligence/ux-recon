# Findings

## Architecture Design Decisions

### Three-Layer Separation
- **Execution** (Playwright): navigate, click, capture — no decisions
- **Observation** (Python): extract candidates, fingerprint DOM, score novelty — deterministic
- **Reasoning** (LLM via conversation): deep analysis, summarization, replication — expensive, selective

### Cheap Signals First
Novelty detection uses DOM structural fingerprinting (tag tree hash) to avoid wasting analysis budget on near-duplicate pages. Most admin panels have 20+ pages that are all "table + card + pagination" — fingerprinting catches this.

### Analysis Unit Flexibility
Not everything is a "page". The agent captures states:
- route (URL change)
- modal/drawer (overlay)
- tab state (same page, different tab)
- expanded row (table detail)
- dropdown (action menu)

Each gets its own StateSnapshot with novelty scoring.

### What Carries Over from v1
- Pydantic config models (extended with budget/exploration settings)
- Playwright capture logic (refactored into single-action interface)
- Page analyzer (component detection, design tokens)
- Interaction selectors (configurable via YAML)

### What's New
- State machine (8 states)
- Frontier management (BFS queue)
- Candidate detection (find clickable items on current page)
- DOM fingerprinting + novelty scoring
- Structured artifacts (inventory, sitemap, run log, per-state analysis)
- Retry/backtrack/recovery
- Budget awareness (max_states, max_depth, novelty_threshold)
