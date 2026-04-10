# Task Plan

## Goal

Ship `frontend_recon_agent` as a credible competitive-analysis demo built on a Playwright-based browser agent runtime.

## Current Phase

Phase 13 - External reference review and architecture comparison

## Current Architecture

- Browser runtime: Playwright, local visible browser
- Control loop:
  - observe
  - decide
  - act
  - re-observe
- Main outputs:
  - screenshots and DOM snapshots
  - page insights and extraction artifacts
  - readable competitive-analysis reports
  - optional synthesized narrative report

## Completed Phases

### Phase 0 - Baseline Runtime
- [x] Confirm original BFS exploration framework
- [x] Confirm artifact, analyzer, and CLI foundations
- **Status:** complete

### Phase 1 - Competitive-Analysis Pivot
- [x] Reframe the project around evidence-backed competitive analysis
- [x] Add vision-aware page understanding and page insights
- [x] Add structured extraction and report-generation layers
- **Status:** complete

### Phase 2 - Agentic Runtime Upgrade
- [x] Add goal-aware decisions
- [x] Add action validation and site memory
- [x] Add re-observation after state changes
- [x] Add challenge handling and human assistance paths
- **Status:** complete

### Phase 3 - Demo Hardening
- [x] Add readable screenshot-rich report output
- [x] Add batch orchestration and comparison reporting
- [x] Add timing summaries and improved route discovery
- [x] Add first-pass registration / magic-link continuation support
- **Status:** complete

### Phase 4 - Review and Stabilization
- [x] Run a focused project code review
- [x] Fix nav-discovery over-pruning
- [x] Fix deferred-route goal matching brittleness
- [x] Replace unconditional overlay dismissal with overlay triage
- **Status:** complete

## Active Phase

### Phase 13 - External Reference Review and Architecture Comparison
- [x] Inspect `D:\web_access\web-access`
- [x] Understand whether it uses proxy/API browser access rather than local Playwright control
- [x] Compare that model against the current runtime
- [x] Decide what ideas are worth borrowing without changing the browser foundation prematurely
- **Status:** complete

## Open Risks

- Registration flow quality is still less proven than public-site analysis.
- Comparison reporting still needs stronger analyst-style quality.
- No automated regression suite exists for the runtime-critical paths.
- Competitive-analysis framing is still not fully consistent across all docs and outputs.

## Decision Filters

- Prefer borrowing ideas from external systems over replacing the runtime wholesale unless there is clear leverage.
- Preserve evidence quality and inspectability as first-class product traits.
- Avoid changes that make the demo look more agentic but less auditable.
