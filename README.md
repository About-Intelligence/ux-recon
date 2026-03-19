# Frontend Mimic

AI-powered tool that crawls a website, analyzes its frontend structure, and generates a Vue 3 replica project.

## What It Does

1. **Logs in** to a target website using your credentials
2. **Crawls pages** via BFS with configurable depth — captures screenshots, HTML, CSS, and computed styles
3. **Deep interaction** — clicks action buttons, opens modals/drawers, expands table rows, switches tabs
4. **Analyzes** the DOM to detect UI components, design tokens, tech stack, layout patterns, and routing structure
5. **Generates a summary** using Claude or OpenAI vision + text APIs (optional — you can use Claude Code instead)
6. **Scaffolds a Vue 3 project** with matching routes, layouts, components, and design tokens

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the generated Vue project)

### Installation

```bash
git clone https://github.com/your-username/frontend-mimic.git
cd frontend-mimic

pip install -r requirements.txt
playwright install chromium
```

### Configuration

```bash
cp config/settings.yaml config/settings.local.yaml
```

Edit `config/settings.local.yaml`:

```yaml
target:
  url: "https://example.com/login"
  dashboard_url: "https://example.com/dashboard"  # Optional: page to start crawling from

login:
  username: "your_username"
  password: "your_password"
```

For AI-powered summary (optional):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

### Run

```bash
# Full pipeline (crawl + analyze + AI summary + Vue generation)
python -m src.cli

# Crawl + analyze only (no API key needed)
python -m src.cli --skip-ai --skip-generate

# Custom crawl depth
python -m src.cli --depth 3 --max-pages 100

# Headless mode (no browser window)
python -m src.cli --headless

# Re-run analysis on existing crawl data
python -m src.cli --skip-crawl
```

## CLI Options

| Flag | Description |
|------|-------------|
| `--config`, `-c` | Path to custom config YAML file |
| `--depth`, `-d` | Override crawl depth (default: 2) |
| `--max-pages`, `-m` | Override max pages to crawl (default: 50) |
| `--headless` | Run browser without visible window |
| `--skip-crawl` | Skip crawl, use existing data from `output/reports/` |
| `--skip-ai` | Skip AI summary generation |
| `--skip-generate` | Skip Vue project generation |

## Output

```
output/
├── screenshots/       # Full-page screenshots of every page + interaction
├── dom_snapshots/     # Rendered HTML of every captured state
├── reports/
│   ├── crawl_data.json       # Raw crawl data (URLs, styles, links, metadata)
│   ├── analysis.json         # Structured analysis (components, design tokens, routes)
│   └── frontend_summary.md   # AI-generated frontend architecture summary
└── vue_project/       # Generated Vue 3 project (npm install && npm run dev)
```

## Deep Interaction

Beyond just visiting pages, Frontend Mimic interacts with the UI to discover hidden content:

- **Action dropdowns** — clicks operation/action buttons to reveal dropdown menus
- **Modal dialogs** — opens add/edit/review forms and captures them
- **Drawer panels** — captures slide-out panels
- **Table row expansion** — expands collapsible rows
- **Tab switching** — clicks through tab panels

All interaction selectors are configurable in `settings.yaml` under the `interaction:` section.

## Adapting for Different Websites

The default selectors support **Element Plus**, **Ant Design**, and **Bootstrap** out of the box. For other UI frameworks, customize the `interaction` section in your config:

```yaml
interaction:
  action_button_selectors:
    - "button:has-text('Actions')"
    - ".my-custom-action-btn"
  add_button_selectors:
    - "button:has-text('Create')"
    - ".btn-add"
  modal_selectors:
    - ".my-modal:visible"
    - "[role='dialog']:visible"
  destructive_keywords:
    - "delete"
    - "remove"
    - "destroy"
```

### Login Customization

If the default login selectors don't work for your site:

```yaml
login:
  username_selector: "#email-input"
  password_selector: "#password-input"
  submit_selector: "#login-btn"
  success_indicator: ".dashboard-header"  # Element visible only after login
```

## Architecture

```
src/
├── config.py              # YAML config loader with validation
├── cli.py                 # Click-based CLI entry point
├── browser/
│   └── controller.py      # Playwright browser control, login, BFS crawl, deep interaction
├── analyzer/
│   └── page_analyzer.py   # DOM parsing, component detection, design token extraction
├── ai/
│   └── client.py          # Claude + OpenAI API client (vision + text)
└── generator/
    └── vue_generator.py   # Vue 3 project scaffolding from analysis data
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Browser automation | [Playwright](https://playwright.dev/python/) |
| AI analysis | [Claude API](https://docs.anthropic.com/) / [OpenAI API](https://platform.openai.com/) |
| HTML parsing | BeautifulSoup + lxml |
| Config | PyYAML + Pydantic |
| CLI | Click + Rich |
| Generated output | Vue 3 + Vite + Element Plus / Ant Design |

## License

MIT
