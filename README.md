# Frontend Mimic Agent

A browser agent for autonomous website interaction, evidence capture, and structured analysis. The current codebase started from admin-dashboard exploration, but is now being refactored toward a more general agent loop that can handle registration-first and multi-step product flows.

The current implementation already supports optional vision-assisted page understanding, structured extraction for list/detail/form pages, deterministic competitive-analysis artifacts, and an optional LLM synthesis layer for the final report.

The browser runtime remains Playwright-based. The current refactor direction is not to replace Playwright, but to make the control layer more agentic: goal-driven, step-by-step, re-observing after state changes, and preserving site memory for later steps in the same run.

## What It Does

1. **Opens and navigates** a target website using Playwright
2. **Captures evidence** — screenshots, DOM snapshots, logs, and state artifacts
3. **Understands pages repeatedly** with DOM analysis and optional vision calls after important state changes
4. **Extracts structured data** from list/detail/form-like surfaces
5. **Produces structured outputs** that can support product teardown and competitive analysis

## Architecture

```
Reasoning Layer  (Claude/ChatGPT via conversation — reviews artifacts, generates code)
       ↑ handoff
Observation Layer (Python — candidate detection, fingerprinting, novelty scoring)
       ↑ data
Execution Layer   (Playwright — navigate, click, capture)
```

The current runtime still uses a route-first exploration core, but is being shifted toward a more general:
1. `observe`
2. `decide`
3. `act`
4. `re-observe`
5. `continue`
loop suitable for broader browser-agent tasks.

Recent agent-loop upgrades include:
- goal-aware decision prioritization
- action-outcome validation after clicks and form submits
- lightweight site memory persisted as an artifact for the current domain
- captcha / anti-bot detection as a first-class runtime state

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

## Targeting a New Website

1. Copy the template config:
   ```bash
   cp config/settings.yaml config/settings.local.yaml
   ```

2. Edit `config/settings.local.yaml` with your target:

   ```yaml
   # Required — your target site
   target:
     url: "https://your-site.com/login"          # Login page URL
     dashboard_url: "https://your-site.com/home"  # Page after login (or leave empty)

   # Required — your credentials
   login:
     username: "your_username"
     password: "your_password"
   ```

   That's it for most Element Plus / Ant Design / Bootstrap admin sites. The defaults handle the rest.

3. **If the site uses a custom UI framework**, also configure selectors:

   ```yaml
   # Optional — customize for non-standard UI frameworks
   login:
     username_selector: "input#my-username"    # CSS selector for username field
     password_selector: "input#my-password"
     submit_selector: "button#login-btn"

   exploration:
     nav_selectors:                            # How to find sidebar/nav menu items
       - ".my-nav-item a[href]"
       - ".sidebar-link"
     submenu_expand_selectors:                 # How to expand collapsed sub-menus
       - ".my-submenu:not(.open) > .toggle"

   interaction:
     action_button_selectors:                  # Action/operation buttons on table rows
       - "button:has-text('Actions')"
     modal_selectors:                          # How to detect open modals/dialogs
       - ".my-modal:visible"
     modal_close_selectors:                    # How to close modals
       - ".my-modal .close-btn"
   ```

4. Run:
   ```bash
   python -m src.cli
   ```

## Configuration Reference

Edit `config/settings.local.yaml`:

| Section | Key Settings |
|---------|-------------|
| `target` | `url` (entry page), `dashboard_url` (optional post-login page) |
| `task` | `goal`, registration/login flow allowance, captcha policy |
| `login` | `username`, `password`, form element selectors |
| `crawl` | `wait_after_navigation`, `wait_for_spa`, `interaction_timeout` |
| `budget` | `max_states` (capture limit), `max_depth`, `retry_limit`, `novelty_threshold` |
| `exploration` | `nav_selectors`, `submenu_expand_selectors`, `skip_patterns`, `destructive_keywords` |
| `interaction` | Selectors for action buttons, modals, dropdowns, tabs, expand rows |
| `browser` | `headless`, `viewport_width/height`, `slow_mo` |
| `vision` | `enabled`, `provider`, `model`, `api_base_url`, `api_key_env`, `timeout_ms` |
| `synthesis` | `enabled`, `provider`, `model`, `api_base_url`, `api_key_env`, `timeout_ms` |

Important `task` settings:
- `goal` – high-level objective for the agent
- `goal_keywords` – optional extra terms that should bias action selection
- `allow_registration_flows` – allow multi-step signup / onboarding flows
- `captcha_policy` – how to behave when captcha or anti-bot is detected
- `use_site_memory` – preserve and reuse per-domain action outcomes during a run
- `validate_action_outcomes` – check whether a click or submit actually changed the state
- `reobserve_on_state_change` – refresh page understanding after meaningful state changes
- `use_vision_on_state_change` – allow vision on those repeated understanding passes

## Output

After a run, `output/` contains:

```
output/
├── screenshots/           # Full-page PNGs for every captured state
├── dom_snapshots/          # Rendered HTML for every captured state
├── artifacts/
│   ├── inventory.json      # Page inventory with status, paths, novelty scores
│   ├── sitemap.json        # Traversal graph (nodes, edges, groups)
│   ├── coverage.json       # Per-page coverage (what was explored vs missed)
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
- **Agent-loop foundation** – the main loop is being refactored from fixed exploration into observe/decide/act behavior
- **Goal-driven decisions** – pending actions are prioritized against the task goal and what has already worked on the current domain
- **Action validation** – the runtime checks for meaningful state change after important actions instead of assuming success
- **Site memory** – the agent records selector/label success and challenge events into `site_memory.json`
- **Repeated understanding** – the engine can refresh page understanding after route capture and key interaction captures
- **Captcha / anti-bot awareness** — the engine detects common challenge indicators and can pause/report instead of blindly continuing
- **Recovery** — retries on failure, re-authenticates on session expiry, backtracks on dead ends
- **Structured logging** — every action is logged with timestamp, duration, result, and reason
- **Works without APIs for the core path** — browser control and local analysis do not require model APIs
- **Framework-agnostic** — configurable selectors support Element Plus, Ant Design, Bootstrap, and custom UIs

## Workflow with Claude/ChatGPT

## Current Extensions

- Optional vision-enhanced page understanding
- Structured extraction for list/detail/form pages
- Optional LLM synthesis for the final competitive-analysis report
- Dataset artifacts:
  - `dataset.jsonl`
  - `dataset_summary.json`
  - `extraction_failures.json`
- Competitive-analysis outputs:
  - `competitive_analysis.json`
  - `competitive_analysis.md`
  - `competitive_analysis_structured.md`
  - `competitive_analysis_llm.json` when synthesis is enabled

Notes:
- Core browser control and local analysis work without API keys
- Vision enhancement requires API credentials because screenshot understanding is provider-backed
- Final-report LLM synthesis also requires API credentials if enabled

The intended workflow:

1. Run the agent: `python -m src.cli`
2. Review `exploration_report.md`, `dataset.jsonl`, and `competitive_analysis.md`
3. Bring the outputs to Claude Code or ChatGPT
4. Ask for a product teardown, frontend rebuild, or benchmark comparison using the generated artifacts

## Requirements

- Python 3.11+
- Playwright + Chromium
- A visitor/test account for the target website
