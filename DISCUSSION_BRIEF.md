# Frontend Recon Agent Presentation Brief

## 1. The Short Version

`frontend_recon_agent` is a Playwright-based browser agent for competitive website analysis.

Its core value is not just that it can browse websites. Its value is that it can:

- explore a site with an explicit agent loop
- preserve grounded evidence while it explores
- turn that evidence into structured and readable competitive-analysis outputs

The most important framing is:

> This is not a screenshot bot and not just a crawler. It is an evidence-backed browser analysis system.

## 2. The Problem We Are Solving

Most website analysis pipelines fall into one of two buckets:

- they are deterministic crawlers that collect pages but do not understand product surfaces well
- or they are highly agentic systems that act flexibly but leave weak audit trails

For competitive analysis, both are incomplete.

What we actually need is a system that can:

- move through real websites
- handle more than static link collection
- preserve enough evidence to justify later claims
- produce outputs that are useful to both engineers and stakeholders

## 3. Our Positioning

The project started closer to an admin-dashboard exploration tool.

The current positioning is broader:

- general public websites, not just admin apps
- agentic control loop, not only frontier crawling
- evidence-first outputs, not only automation traces
- competitive-analysis reports, not only engineering logs

So the right mental model is:

**browser agent + evidence pipeline + reporting layer**

## 4. How The System Works

There are two cooperating flows.

### Agent Loop

```text
observe -> decide -> act -> validate -> re-observe
```

This is how the system decides what to do next.

### Evidence Flow

```text
collect -> normalize -> anchor -> assemble -> aggregate -> report
```

This is how the system decides what to keep.

That distinction matters because browsing alone is not enough for a credible analysis product.

## 5. Why The Architecture Matters

The key design choice is:

**DOM-grounded, vision-guided**

That means:

- Playwright stays the execution layer
- DOM and browser state remain the grounding layer
- vision helps interpret page structure and product surfaces
- final reporting is built on preserved evidence

This gives us a middle path:

- more flexible than a pure DOM crawler
- more auditable than a model-only agent

## 6. What The System Can Do Today

Current implemented capabilities:

- public-site exploration
- first-pass login and registration support
- repeated understanding after meaningful state changes
- challenge detection with human-assisted freeze and resume
- site memory within a run
- structured extraction and aggregation
- readable competitive-analysis reports
- multi-site comparison workflow


## 7. What Makes It More Than A Crawler

There are four differentiators worth emphasizing in a presentation.

### 1. Explicit Action Validation

The system does not assume a click worked just because the browser executed it.
It checks whether the page state actually changed.

### 2. Re-Observation After State Change

The system can re-understand the page after meaningful transitions instead of treating each page as a one-shot snapshot.

### 3. Evidence Preservation

Outputs are not just logs. They include:

- screenshots
- DOM snapshots
- page insights
- datasets
- inventory and sitemap artifacts
- competitive-analysis summaries and reports

### 4. Report Layer

The system can turn crawl artifacts into a human-readable report instead of forcing reviewers to inspect raw JSON.


## 8. What Is Still Not Convincing Enough

The project already proves:

- the architecture is viable
- the runtime can complete meaningful public-site analysis
- the output chain is real

But it does not yet fully prove:

- analyst-quality report sharpness
- strong reliability on registration-gated products
- benchmark-grade repeatability across many targets


## 9. Main Risks To Surface

- report quality still needs calibration against strong human-written analyst memos
- registration and verification flows are less validated than public browsing


## 10. Questions And Answers

### Why use Playwright instead of the user's local browser?

Short answer:

- we chose Playwright because it gives us a cleaner execution boundary, better reproducibility, and stronger artifact control

Longer answer:

- For this project, the browser is not just a UI surface. It is also the execution substrate for evidence capture.
- We need stable control over:
  - navigation
  - DOM capture
  - screenshots
  - state-change validation
  - per-run artifact ownership
- Using an existing local browser session is attractive for login continuity, but it introduces tradeoffs:
  - weaker reproducibility
  - more environment coupling
  - more variability across runs
  - harder isolation of site-specific artifacts
- For a competitive-analysis demo, inspectability and repeatability matter a lot.
- So the current choice is:
  - keep Playwright as the default runtime
  - prefer a controlled browser environment
  - accept that existing-session reuse may become a later integration path, not the foundation

The honest tradeoff:

- this choice is better for evidence quality
- it is worse than a local-browser/CDP approach when the main goal is inheriting an already-authenticated user session

### Why are login and registration flows still not adapted well enough?

Short answer:

- because auth flows are the least standardized part of the web, and our current implementation is intentionally still conservative and selector-driven

Longer answer:

- Public browsing generalizes relatively well because link discovery, content capture, and page understanding have recurring patterns.
- Login and registration do not generalize as easily because they vary heavily in:
  - form layout
  - field naming
  - multi-step sequencing
  - OTP / magic-link verification
  - anti-bot pressure
  - region / provider-specific widgets
- Our current auth layer is a first-pass, demo-scoped system:
  - `public`
  - `login`
  - `register`
  - `auto`
- It works best on standard email/password forms and basic verification flows.
- It is intentionally not presented as a fully general onboarding agent.

The real reason this area is weaker than public mode:

- public exploration benefits from many repeated page patterns
- auth flows contain product-specific edge cases that are harder to abstract safely without overfitting

What we have done already:

- multi-step auth progression
- first-pass verification-step detection
- manual verification continuation
- challenge freeze and resume

What is still missing:

- stronger semantic form planning
- more real-site validation
- clearer support boundaries for multi-step onboarding and verification-heavy flows

### What is the novelty score, and what does it do?

Short answer:

- novelty score is a structural DOM-difference score, not a business-value score and not a visual-quality score

How it works:

- Each page state is fingerprinted based on DOM structure.
- The fingerprint includes:
  - a shallow tag-tree shape
  - UI component-class inventory
  - counts of structural elements
- A new page state is compared against previously seen states.
- Novelty is calculated as:
  - `1.0` for a completely new structure
  - `0.0` for an exact duplicate
  - intermediate values for partial similarity

What it is used for:

- skipping low-value duplicate interaction captures
- reducing repeated capture of nearly identical states
- helping screenshot selection in reports
- improving coverage efficiency under a finite state budget

What it is not:

- not a measure of business importance
- not a measure of product quality
- not a semantic understanding score

Why that distinction matters:

- If someone hears "novelty," they may assume it means "interesting."
- In this system it really means:
  - "structurally different from what we already saw"

So the right defense is:

- novelty is a deduplication and coverage-efficiency heuristic
- it is one ranking signal, not the definition of importance

### How is this different from a typical browser-use agent?

Short answer:

- the main difference is that this project is optimized for evidence-backed analysis, not just task completion

Typical browser-use systems optimize for:

- finishing a task
- taking flexible actions
- following natural-language goals

This project also cares about taskful browsing, but it adds a second requirement:

- preserve enough structured evidence to justify later claims

That leads to several differences:

- explicit artifact system
  - screenshots
  - DOM snapshots
  - page insights
  - structured datasets
  - inventory and sitemap artifacts
- explicit action validation instead of assuming execution success
- explicit re-observation after state change
- structured extraction and aggregation, not just transcripts
- readable report generation as a first-class output

So the practical difference is:

- a browser-use agent proves it can act
- this system tries to prove both that it can act and that its conclusions are reviewable

### Why not just use screenshots plus an LLM?

Because screenshots alone are too weak for reliable downstream analysis.

We need:

- DOM-grounded anchors
- repeatable state capture
- route and interaction history
- structured evidence that can be aggregated across pages

An LLM-only screenshot pipeline may look impressive in a demo, but it usually weakens:

- traceability
- reproducibility
- failure analysis
- confidence in cross-page aggregation


### How do we know the report is grounded instead of made up?

Because the report is downstream of preserved artifacts rather than generated from memory alone.

The system keeps:

- page screenshots
- DOM snapshots
- page insights
- extracted datasets
- inventory and sitemap artifacts

That means the report can be audited against captured evidence.

The current weakness is not total lack of grounding. The current weakness is:

- report sharpness and prioritization still need improvement

So the honest defense is:

- grounding is already a strength
- final narrative quality is improving, but not finished

### Why not use a framework like LangGraph or a more complex multi-agent setup?

Because the main bottleneck right now is not orchestration complexity. It is evidence quality, runtime reliability, and report usefulness.

The current loop is still naturally expressible as:

- observe
- decide
- act
- validate
- re-observe

Keeping that explicit has benefits:

- easier auditing
- easier debugging
- easier artifact ownership
- lower architectural overhead

This may change later, but at the current stage the simpler architecture is a feature, not a limitation.
