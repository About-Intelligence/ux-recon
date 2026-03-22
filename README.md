# Frontend Mimic Agent

A budget-aware, policy-driven browser agent for autonomous website exploration, artifact collection, and selective analysis. Optimized for admin dashboards, LIMS, ERP, and SaaS management applications.

## What It Does

1. **Logs into** a target website using configured credentials
2. **Autonomously explores** the site by detecting navigation menus, action buttons, modals, tabs, and expandable rows
3. **Captures artifacts** — full-page screenshots and DOM snapshots for every state
4. **Scores novelty** — uses DOM structural fingerprinting to avoid redundant analysis of near-duplicate pages
5. **Analyzes** pages locally — detects components, layout patterns, design tokens, and tech stack
6. **Produces structured reports** — inventory, site map, execution log, and exploration summary

## Architecture

```
Reasoning Layer  (Claude/ChatGPT via conversation — reviews artifacts, generates code)
       ↑ handoff
Observation Layer (Python — candidate detection, fingerprinting, novelty scoring)
       ↑ data
Execution Layer   (Playwright — navigate, click, capture)
```

The agent runs as a state machine with 8 phases:
`initialize → authenticate → observe → select_action → execute → eval_novelty → analyze → backtrack_continue → finalize`

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
cp config/settings.yaml config/settings.local.yaml
# Edit settings.local.yaml with your target URL and credentials

# Run
python -m src.cli
```

## CLI Options

```
python -m src.cli [OPTIONS]

  --config, -c PATH      Path to config YAML file
  --max-states, -s INT   Override max states budget
  --max-depth, -d INT    Override max exploration depth
  --headless             Run browser in headless mode
  --clear                Clear output before running
```

## Configuration

Edit `config/settings.local.yaml`:

| Section | Key Settings |
|---------|-------------|
| `target` | Login URL, dashboard URL |
| `login` | Username, password, form selectors |
| `budget` | `max_states`, `max_depth`, `retry_limit`, `novelty_threshold` |
| `exploration` | `skip_patterns`, `destructive_keywords`, `nav_selectors` |
| `interaction` | Selectors for action buttons, modals, dropdowns, tabs, expand rows |
| `browser` | Headless mode, viewport size, slow_mo |

## Output

After a run, `output/` contains:

```
output/
├── screenshots/           # Full-page PNGs for every captured state
├── dom_snapshots/          # Rendered HTML for every captured state
├── artifacts/
│   ├── inventory.json      # Page inventory with status, paths, novelty scores
│   ├── sitemap.json        # Traversal graph (nodes, edges, groups)
│   ├── run_log.jsonl       # Step-by-step execution log
│   └── analysis/           # Per-state analysis (components, layout, tokens)
│       ├── state_xxxx.json
│       └── ...
└── reports/
    └── exploration_report.md  # Human-readable exploration summary
```

## Key Features

- **Budget-aware** — stops after `max_states` captures, never runs forever
- **Novelty scoring** — DOM fingerprinting skips near-duplicate pages (e.g., 20 identical table views)
- **Autonomous navigation** — detects sidebar menus, nav items, tabs, action dropdowns automatically
- **Recovery** — retries on failure, re-authenticates on session expiry, backtracks on dead ends
- **Structured logging** — every action is logged with timestamp, duration, result, and reason
- **No API keys needed** — all analysis is local; LLM reasoning happens in your Claude/ChatGPT conversation
- **Framework-agnostic** — configurable selectors support Element Plus, Ant Design, Bootstrap, and custom UIs

## Workflow with Claude/ChatGPT

The intended workflow:

1. Run the agent: `python -m src.cli`
2. Bring the outputs to Claude Code or ChatGPT
3. Ask: "Review the exploration report and screenshots, then rebuild the frontend"
4. The LLM reads the structured artifacts and generates code

## Requirements

- Python 3.11+
- Playwright + Chromium
- A visitor/test account for the target website
