# Architecture: Frontend Recon Agent

> A Playwright-based browser agent that preserves evidence, produces structured page understanding, and supports downstream competitive analysis.

## Current Position

The project is no longer best described as a route-first admin-dashboard crawler.

The current direction is:

- a more agentic browser-control loop
- broader support for general websites, not only admin/SaaS products
- deterministic evidence capture as a core differentiator
- optional vision/LLM understanding layered on top of grounded browser execution

The system should be understood as two cooperating flows:

- control flow: `observe -> decide -> act -> validate -> re-observe`
- evidence flow: `collect -> normalize -> anchor -> assemble -> aggregate`

## System Model

```text
                     AGENTIC CONTROL LOOP
      observe -> decide -> act -> validate -> re-observe -> continue
                               |
                               v
                    PAGE UNDERSTANDING LAYER
        DOM summary + screenshot + runtime state + optional vision/LLM
                               |
                               v
                   EVIDENCE COLLECTION LAYER
      collect raw nodes -> normalize -> anchor -> assemble evidence
                               |
        ---------------------------------------------------------
        |                         |                            |
        v                         v                            v
  Executable Evidence       Content Evidence           Structural Evidence
  CTA / nav / form / tab    hero / docs / sections     layout / regions / TOC
        \                         |                            /
         \                        |                           /
          \                       v                          /
           -------------> PAGE EVIDENCE PACK <--------------
                               |
                               v
                    CROSS-PAGE AGGREGATION
       category / modules / workflows / strengths / gaps / evidence index
                               |
                               v
                 REPORTS + JSON ARTIFACTS + REVIEW HANDOFF
```

## Architectural Layers

### 1. Execution Layer

The execution layer remains Playwright-based.

Its job is to:

- launch and manage the browser
- navigate and click
- fill forms and submit actions
- capture screenshots and HTML
- detect whether an action produced meaningful state change

This layer should stay deterministic and tool-like. It should not decide strategy by itself.

### 2. Observation and Understanding Layer

This layer turns the current browser state into grounded page understanding.

Inputs:

- current URL
- DOM
- screenshot
- runtime context
- optional task goal and site memory

Outputs:

- candidate actions
- DOM summary
- page type hints
- high-value signals
- page insight artifacts

This layer is where optional vision/LLM support belongs. The model should help interpret the page, not directly replace grounded browser execution.

### 3. Evidence Collection Layer

This layer answers:

> What on this page is worth preserving as reusable, reviewable evidence?

It should preserve as much rule-grounded evidence as possible before any higher-level summarization.

Its job is to:

- collect raw page objects from DOM and runtime captures
- normalize noisy text
- attach DOM and screenshot anchors
- assemble structured evidence units
- persist page-level evidence for later aggregation

This layer is not the control loop. It is the memory and evidence substrate for later analysis.

### 4. Aggregation and Reporting Layer

This layer converts page-level evidence into cross-page artifacts such as:

- inventory
- sitemap
- dataset rows
- page insights
- competitive-analysis summaries
- markdown reports

This is where the project differentiates from a generic browser transcript.

## Core Runtime Loop

The modern runtime should be thought of as:

```text
1. OBSERVE
2. DECIDE
3. ACT
4. VALIDATE
5. RE-OBSERVE
6. COLLECT EVIDENCE
7. CONTINUE OR STOP
```

Important notes:

- route discovery is still present, but should no longer be the only decision source
- page-level actions can be chosen before frontier navigation
- repeated understanding after meaningful state changes is a first-class behavior
- site memory should influence future action selection on the same domain
- challenge states such as captcha or anti-bot should be surfaced explicitly

### Budget Controls

The current runtime uses two different exploration constraints:

- `max_depth`
  limits how many target layers away from the starting point a discovered target may be
- `max_states`
  limits the total number of captured states in a run

These work together, but they are not the same thing:

- `max_depth` constrains frontier expansion by level
- `max_states` constrains the overall run budget regardless of where those states came from

This means the system is not using a single "breadth limit"; it is using:

- a structural boundary
- plus a total capture budget

## Evidence Collection Design

The evidence layer should be designed around anchors, not just prose summaries.

Each important page object should be preserved as an evidence unit with enough information to:

- locate it again
- inspect it manually
- compare it later
- cite it in a report

### Evidence Flow

```text
raw DOM and screenshot
  -> collectors
  -> text normalization
  -> DOM / visual anchoring
  -> evidence assembly
  -> page evidence pack
  -> cross-page aggregation
```

### Evidence Unit Shape

Each evidence unit should aim to preserve:

- `kind`
- `role`
- `raw_text`
- `normalized_text`
- `url`
- `page_type`
- `locator`
- `dom_path`
- `bbox`
- `html_fragment`
- `screenshot_ref`
- `confidence`
- `observed_at_step`
- `tags`

The exact schema can evolve, but the core principle is stable:

> Every important conclusion should be traceable back to anchored evidence.

### Rule-Layer Guardrails

The shared rule layer must stay general-purpose.

That means:

- prefer structural signals over site-specific text whenever possible
- use text phrases as weak ranking hints, not hard allowlists, unless the phrase is truly generic UI chrome
- do not add site-name-specific strings or one-site blacklists to core collectors or candidate extraction
- when a special case is genuinely needed for one benchmark site, keep it in config or evaluation fixtures, not in the shared runtime heuristics

In short:

> The rule layer should generalize across websites, not be patched around the last validation target.

### Evidence Categories

#### Executable Evidence

These support the agent loop and future replay:

- CTA
- nav item
- tab
- modal trigger
- form field
- submit action

#### Content Evidence

These support competitive analysis and product understanding:

- hero headline
- feature block
- content section
- docs section
- pricing card
- FAQ item

#### Structural Evidence

These support page interpretation and region-level reasoning:

- page region
- section group
- table
- list group
- table of contents
- layout pattern

## Page Understanding vs Evidence Collection

These are related but distinct concerns.

### Agentic Loop

The loop answers:

> What should we do next?

Examples:

- follow a route
- click a primary CTA
- fill a form
- switch a tab

### Evidence Collection

The evidence layer answers:

> What did we find here that is worth preserving?

Examples:

- homepage entry points
- docs navigation structure
- product claims
- onboarding prompts
- pricing blocks

The project should not force these concerns into one module.

## Page Taxonomy

The current high-level taxonomy is intentionally broader than the earlier admin-only framing.

Current common page types:

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

This taxonomy is useful because it changes both:

- what evidence we try to preserve
- how we interpret the page in the final analysis

Notes:

- `landing/content/docs` are important for general websites
- `list/detail/form/dashboard` remain useful for application-style products
- future categories may include `pricing`, `article`, `support`, `directory`, or `workspace`
- categories should only be added when they materially change extraction or reporting behavior

## Why Evidence Matters in an Agentic System

More agentic control does not remove the need for structured evidence.

Without the evidence layer, the system mostly produces:

- action logs
- screenshots
- raw HTML

That is enough for replay, but not enough for good competitive analysis.

With a structured evidence layer, the system can additionally produce:

- reusable page semantics
- extracted entry points and content structures
- grounded report claims
- cross-page comparison inputs

In short:

- agentic control decides how to move
- evidence collection decides what to keep

## Why We Are Not Centering LangChain or LangGraph

This project does not fundamentally need a framework-centric orchestration layer yet.

Current reasons to stay framework-light:

- the runtime is already naturally expressed as a small explicit state machine
- Playwright control, artifact generation, and evidence persistence are easier to audit when the flow is direct
- deterministic evidence capture is a core goal, and framework abstraction can hide important runtime details
- the project still needs architectural clarity more than orchestration flexibility
- broad agent frameworks often add cognitive overhead before they add clear product value

That does not mean such frameworks are never useful. They may become helpful later if we need:

- more complex branching or multi-agent coordination
- resumable long-running workflows across many tools
- graph-level observability beyond the current explicit engine

For now, the chosen design is:

- keep the browser runtime explicit
- keep the state transitions explicit
- keep the evidence pipeline explicit
- add model assistance only where it clearly improves page understanding or reporting

## Folder Structure

```text
frontend_recon_agent/
  config/
    settings.yaml
    settings.local.yaml
  src/
    cli.py
    config.py
    agent/
      engine.py
      state.py
      logger.py
    browser/
      controller.py
      authenticator.py
    observer/
      extractor.py
      fingerprint.py
      novelty.py
    analyzer/
      page_analyzer.py
    vision/
      client.py
      prompts.py
      types.py
    extraction/
      engine.py
      list_extractor.py
      detail_extractor.py
      form_extractor.py
      content_extractor.py
      types.py
    analysis/
      competitive_report.py
      synthesis_client.py
      prompts.py
    artifacts/
      manager.py
      inventory.py
      sitemap.py
      report.py
  output/
    screenshots/
    dom_snapshots/
    artifacts/
    reports/
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `agent/engine.py` | Orchestrates the explicit agent loop and finalization flow |
| `browser/controller.py` | Executes browser actions and captures runtime artifacts |
| `observer/extractor.py` | Detects candidate interactions and cheap page signals |
| `vision/client.py` | Optional model-backed page understanding |
| `analyzer/page_analyzer.py` | Local DOM/layout/component analysis |
| `extraction/engine.py` | Dispatches page evidence extraction by strategy |
| `extraction/content_extractor.py` | Preserves general-website content evidence such as hero, CTA, nav, and sections |
| `analysis/competitive_report.py` | Aggregates page evidence into cross-page competitive-analysis artifacts |
| `artifacts/report.py` | Produces human-readable exploration report |

## Current Artifact Set

Important artifacts currently include:

- `inventory.json`
- `sitemap.json`
- `coverage.json`
- `site_memory.json`
- `run_log.jsonl`
- `dataset.jsonl`
- `dataset_summary.json`
- `extraction_failures.json`
- `competitive_analysis.json`
- `competitive_analysis.md`
- `page_insights/*.json`
- `vision/*.json`

Together these artifacts form the review surface for later teardown and comparison work.

## Near-Term Architecture Priorities

The most important next architectural steps are:

1. Continue reducing route-first assumptions in the control loop.
2. Expand page evidence collection for general websites.
3. Improve text normalization and evidence cleanliness.
4. Tighten the mapping between page taxonomy and extraction strategy.
5. Keep reports grounded in anchored evidence rather than free-form summaries.
