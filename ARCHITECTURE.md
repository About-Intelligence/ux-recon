# Frontend Recon Agent Architecture

> A Playwright-based browser agent for evidence-backed website analysis and competitive reporting.

## 1. What This System Is

`frontend_recon_agent` is no longer best described as a route-first crawler for admin dashboards.

The current system is better understood as:

- a browser agent that can operate on general public websites
- a deterministic evidence pipeline layered under optional model assistance
- a competitive-analysis demo that produces reviewable artifacts, not just action logs

The core product claim is:

> We do not just browse pages. We preserve enough grounded evidence to support later analysis, comparison, and presentation.

## 2. Operating Model

The runtime has two cooperating flows.

### Control Flow

```text
observe -> decide -> act -> validate -> re-observe -> continue
```

This is the agent loop that decides what to do next.

### Evidence Flow

```text
collect -> normalize -> anchor -> assemble -> aggregate -> report
```

This is the analysis substrate that decides what to preserve.

These two flows are related, but they are not the same thing:

- the control flow optimizes action selection
- the evidence flow optimizes auditability and downstream insight

## 3. Architecture Overview

```text
                    AGENT CONTROL LOOP
      observe -> decide -> act -> validate -> re-observe
                           |
                           v
                 PAGE UNDERSTANDING LAYER
        DOM summary + screenshot + runtime context + vision
                           |
                           v
                  EVIDENCE COLLECTION LAYER
        structured page objects + anchors + normalized text
                           |
                           v
                 CROSS-PAGE AGGREGATION LAYER
        inventory + sitemap + dataset + page insights + summary
                           |
                           v
                    REPORTING AND HANDOFF
      readable report + structured report + JSON artifacts
```

## 4. Main Layers

### Execution Layer

The execution layer is Playwright-based and intentionally deterministic.

Responsibilities:

- launch and manage the browser
- navigate and click
- fill and submit forms
- capture screenshots and DOM snapshots
- detect whether actions caused meaningful state changes

This layer should stay tool-like. It executes. It does not decide product strategy.

### Observation And Understanding Layer

This layer turns the current browser state into grounded page understanding.

Inputs:

- URL
- DOM
- screenshot
- runtime context
- task goal
- site memory

Outputs:

- candidate routes and actions
- DOM summary
- page-type hints
- interaction hints
- page insight artifacts

This is the right place for optional vision and LLM support.

### Evidence Layer

This layer answers:

> What on this page is worth keeping as reusable evidence?

It preserves structured page evidence before higher-level summarization.

Typical evidence categories:

- executable evidence: nav items, CTAs, tabs, forms, submit actions
- content evidence: headlines, feature blocks, pricing cards, docs sections
- structural evidence: regions, lists, tables, section groups, page layout cues

### Aggregation And Reporting Layer

This layer converts page-level evidence into cross-page artifacts:

- `inventory.json`
- `sitemap.json`
- `dataset.jsonl`
- `page_insights/*.json`
- `competitive_analysis.json`
- `competitive_analysis_structured.md`
- `competitive_analysis_readable.md`
- optional `competitive_analysis.md`

This is where the project moves from "browser automation" to "analysis product."

## 5. Runtime Behavior

The practical loop is:

1. Observe the page
2. Generate grounded candidates
3. Choose the best next action
4. Execute the action
5. Validate whether state changed
6. Re-observe when the state meaningfully changed
7. Capture evidence and continue until stop conditions are hit

Important runtime traits:

- route discovery still matters, but it is no longer the only driver
- page-level actions can outrank frontier navigation
- repeated understanding after state change is first-class
- challenge states are treated explicitly
- site memory influences later decisions on the same domain

## 6. Budget Model

The runtime uses two distinct boundaries:

- `max_depth`: how far discovered routes may expand from the starting point
- `max_states`: how many states may be captured in total

These are complementary:

- `max_depth` constrains structural expansion
- `max_states` constrains total run budget

The system also uses named profiles:

- `smoke_fast`
- `demo`
- `full`

This is important because "the code still runs" and "the demo looks convincing" are different requirements.

## 7. Page Taxonomy

The current page taxonomy is intentionally broader than the original admin-only framing.

Current common types:

- `landing`
- `content`
- `docs`
- `list`
- `detail`
- `form`
- `dashboard`
- `auth`
- `modal`
- `unknown`

This matters because page type influences both:

- what we try to extract
- how we interpret the page in the final report

## 8. Key Technical Decisions

### Playwright Stays The Browser Foundation

Decision:

- keep the browser runtime explicit and Playwright-based

Why:

- execution remains inspectable
- artifact generation remains easy to audit
- deterministic capture is a core differentiator

Not chosen:

- replacing the runtime with a CDP-proxy-first system
- introducing a heavy framework-centric orchestration layer

### DOM-Grounded, Vision-Guided

Decision:

- use DOM and browser state as the grounding layer
- use vision to improve page interpretation, not raw execution

Why:

- general websites are too varied for DOM-only heuristics to be sufficient
- raw model control would weaken determinism and auditability

### Human-Readable Report As A First-Class Output

Decision:

- keep a deterministic stakeholder-facing readable report in addition to structured outputs

Why:

- JSON and structured markdown are useful, but not enough for demo storytelling
- a readable report improves presentation value while keeping claims anchored

### Multi-Site Concurrency Before Intra-Site Concurrency

Decision:

- run separate sites concurrently
- keep each site's internal loop mostly single-threaded

Why:

- independent targets map cleanly to separate engines
- per-site artifacts are naturally isolated
- intra-site parallelism would complicate reproducibility and state accounting

### Public Runner Ergonomics Matter

Decision:

- support configurable headless mode
- support bounded multi-site concurrency
- support direct CLI URL input for one to three public targets
- isolate outputs per site in batch mode
- throttle shared vision concurrency

Why:

- easier execution is part of demo credibility
- without these controls, multi-site comparison runs are operationally awkward

### Challenge Handling Should Freeze, Not Fight

Decision:

- when captcha / anti-bot / Cloudflare-style challenges appear, freeze automation and resume in the same session after human clearance

Why:

- continued automation often interferes with challenge resolution
- preserving session continuity is more valuable than forcing "full autonomy"

### Demo-Scoped Access Model

Decision:

- explicitly support `public`, `login`, `register`, and `auto`

Why:

- this covers the current demo story without pretending to solve general onboarding for every product

Known limit:

- registration and verification handling are still less proven than public browsing

## 9. Guardrails

The shared runtime should stay general-purpose.

Guardrails:

- prefer structural signals over site-specific phrases
- treat text rules as ranking hints, not hard allowlists, unless the text is generic UI chrome
- avoid patching one benchmark site directly into shared logic
- keep one-off site behavior in config or evaluation fixtures when possible

In short:

> The system should generalize across websites, not be tuned around the last demo target.

## 10. Current Strengths

- strong artifact discipline
- grounded evidence rather than raw transcript-only output
- general-website taxonomy instead of admin-only assumptions
- optional vision without giving up deterministic browser execution
- stakeholder-readable reporting
- first-pass multi-site comparison workflow
- improved public runner ergonomics

## 11. Current Weaknesses

- report quality is better, but still below strong human-written analyst memos
- public mode is more validated than registration mode
- no real automated regression suite yet
- some reporting noise and text cleanup issues remain
- direct URL mode still inherits assumptions from the chosen base config

## 12. Near-Term Priorities

1. Strengthen the presentation framing of the project as a competitive-analysis demo.
2. Improve report sharpness so cross-site differences are clearer.
3. Run more realistic validation on registration-gated targets.
4. Improve evidence cleanliness and screenshot selection quality.
5. Add stronger benchmarking against human-written comparison outputs.

## 13. One-Line Summary

`frontend_recon_agent` is a Playwright-based browser agent that combines explicit control, structured evidence capture, and report generation to support competitive website analysis.
