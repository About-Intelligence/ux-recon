# Findings

## AI Browser Automation — Research Complete

### Decision: Playwright + browser-use + Claude/OpenAI APIs

| Component | Choice | Why |
|-----------|--------|-----|
| Browser engine | **Playwright** (v1.58.0) | Mature, fast, excellent Windows/SPA support |
| AI navigation | **browser-use** (v0.12.2) | Built on Playwright, natural language task orchestration |
| Deterministic steps | Raw Playwright calls | Login, screenshots, DOM extraction — predictable steps |
| Vision analysis | Claude API + OpenAI API | Send screenshots as base64 for structural analysis |
| Text analysis | Claude/OpenAI text API | Send extracted HTML for component identification |
| Python version | 3.11+ | Required by browser-use |

### Key Technical Notes
- browser-use wraps Playwright internally — they share the same Chrome instance via CDP
- SPA hash routing (`#/route`) works fine with `page.goto()` — just wait for render
- `page.content()` returns fully rendered DOM after JS execution
- `page.evaluate()` with `getComputedStyle` captures computed CSS
- For stylesheets, also extract `document.styleSheets` or intercept CSS files via `page.route()`
- Screenshots: base64 encode → send to Claude/OpenAI vision endpoints
- Claude: max 5MB/image, 8000x8000px, ~1334 tokens per 1000x1000px
- OpenAI: max 50MB payload, `detail: "high"` for full resolution

## Target Website
- URL: https://www.labverix.com/#/login?redirect=/dashboard
- Login: username/password form
- Hash-based routing → likely Vue or React SPA
- Crawl depth: configurable (N links from main page)

## Frontend Replication
- Output framework: Vue 3
- Will generate Vue project scaffold from analysis
