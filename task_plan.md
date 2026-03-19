# Task Plan: AI-Powered Website Frontend Mimic

## Goal
Build a project that uses AI to autonomously operate a browser, analyze a website's frontend structure (using a visitor account), produce a thorough summary, and replicate/recreate the frontend.

## Current Phase
Phase 2 — Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] Clarify target website and login details (visitor account)
- [x] Research available AI browser automation frameworks
- [x] Evaluate: Playwright + AI, Browser-Use, Stagehand, LaVague, etc.
- [x] Choose tech stack (language, framework, AI model)
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Project Setup & Architecture
- [x] Initialize project (pyproject.toml + requirements.txt)
- [x] Design module architecture:
  - `src/browser/controller.py` — Browser lifecycle, login, crawl, page capture
  - `src/analyzer/page_analyzer.py` — DOM analysis, component detection, design token extraction
  - `src/ai/client.py` — Claude + OpenAI API integration (vision + text)
  - `src/generator/vue_generator.py` — Vue 3 project scaffolding from analysis
  - `src/cli.py` — CLI entry point with click
  - `src/config.py` — YAML config loader with env var overrides
- [x] Set up configuration (config/settings.yaml)
- [ ] Install dependencies (user needs to run pip install)
- **Status:** complete

### Phase 3: Browser Automation & Login
- [ ] Implement browser launch + login flow (visitor account)
- [ ] Implement page navigation (sitemap crawl / link following)
- [ ] Screenshot capture at each page
- [ ] DOM snapshot extraction (HTML, CSS, assets)
- **Status:** pending

### Phase 4: Frontend Analysis Engine
- [ ] Extract page structure (layout, components, navigation)
- [ ] Capture styles (colors, fonts, spacing, responsive breakpoints)
- [ ] Identify UI components (buttons, forms, cards, modals, etc.)
- [ ] Map routing / page hierarchy
- [ ] Detect frameworks/libraries used (React, Vue, Tailwind, etc.)
- **Status:** pending

### Phase 5: AI Summary Generation
- [ ] Feed extracted data to AI model for analysis
- [ ] Generate structured summary:
  - Site map / page hierarchy
  - Component inventory
  - Design system (colors, typography, spacing)
  - Interaction patterns
  - Tech stack detected
- [ ] Output summary as markdown report
- **Status:** pending

### Phase 6: Frontend Replication
- [ ] Generate Vue 3 project scaffold
- [ ] Recreate layout and navigation structure
- [ ] Replicate component library
- [ ] Apply captured styles / design tokens
- [ ] Add placeholder content matching original structure
- **Status:** pending

### Phase 7: Testing & Delivery
- [ ] Visual comparison (screenshots original vs replica)
- [ ] Verify all major pages replicated
- [ ] Package deliverables (summary report + replicated frontend)
- [ ] Document usage instructions
- **Status:** pending

## Key Questions (Answered)
1. Target: https://www.labverix.com/#/login?redirect=/dashboard
2. Login: username/password form (visitor account)
3. AI: Claude API + OpenAI API (both)
4. Replicated frontend: Vue 3
5. Crawl depth: configurable (N links from main page)
6. TBD — discover during crawl
7. Python + Playwright

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Python 3.11+ | Required by browser-use, good ecosystem |
| Playwright for browser control | Most mature, SPA-friendly, great DOM access |
| browser-use for AI navigation | Built on Playwright, natural language tasks |
| Claude + OpenAI for analysis | Dual-model for better coverage (vision + text) |
| Vue 3 for replication | User preference, target site likely Vue/React SPA |
| Configurable crawl depth | User requirement — set N links from main page |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- This project has two main deliverables: (1) a detailed frontend analysis report, (2) replicated frontend code
- Must handle authentication (visitor account) before crawling
- Should respect rate limits and robots.txt
- Screenshots + DOM snapshots are the primary data sources for AI analysis
