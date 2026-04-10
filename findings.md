# Findings

## Project Snapshot

- Project: `frontend_recon_agent`
- Current positioning:
  - externally: competitive-analysis demo
  - internally: Playwright-based browser agent with evidence outputs
- Current runtime shape:
  - route-first frontier plus page-level decisions
  - DOM summary and optional vision understanding
  - structured extraction and human-readable report generation
  - public, login, and first-pass registration-oriented access support

## Confirmed Strengths

- Strong artifact discipline:
  - screenshots
  - DOM snapshots
  - run log
  - page insights
  - extraction outputs
  - readable competitive-analysis reports
- Good fit for evidence-backed analysis because outputs remain inspectable and reproducible.
- Public-site competitive-analysis runs already work on representative targets.
- Multi-site orchestration and comparison reporting now exist in first-pass form.

## Current Runtime Notes

- Playwright remains the browser runtime.
- The engine now includes:
  - goal-aware decision scoring
  - validate-after-action checks
  - lightweight site memory
  - challenge detection and human-assisted pause/resume
  - re-observation after meaningful state changes
- Vision is advisory and grounded by DOM snapshots rather than driving raw selectors directly.

## Recently Fixed Review Issues

- Nav discovery no longer shuts off completely after the first observed page.
  - Cheap nav discovery still runs on later pages.
  - Only expensive hover-menu discovery is cached by nav signature.
- Deferred-route consumption now normalizes common auth phrases such as:
  - `sign up`
  - `sign-up`
  - `signup`
  - `sign in`
  - `signin`
  - `login`
- Pre-observe overlay handling is now lightweight triage, not unconditional dismissal.
  - High-value auth/onboarding overlays are preserved.
  - Low-value cookie/privacy/newsletter overlays can be dismissed.

## Current Gaps Worth Tracking

- Report wording and acceptance criteria should still be framed more consistently around competitive analysis rather than generic browsing completeness.
- Registration mode has first-pass support, but real external validation is still thinner than public-mode validation.
- Comparison report quality still needs calibration against human-written competitive-analysis memos.
- Screenshot ranking is improved, but human-judged validation is still missing.
- Some mojibake / text cleanup remains in the reporting pipeline.

## Validation State

- `python -m compileall src` passed after the latest runtime fixes.
- No meaningful automated test suite is present in the repository right now.
- Runtime confidence still depends mainly on smoke runs.

## External Reference: `web-access`

- `web-access` is centered on a local CDP proxy that connects to the user's existing Chrome and exposes a small HTTP API for browser actions.
- Key traits observed:
  - CDP proxy + HTTP API surface for `new / navigate / eval / click / clickAt / setFiles / screenshot / close`
  - shared browser instance with tab-level isolation
  - environment bootstrap that auto-detects Chrome remote-debugging and auto-starts the proxy
  - site-pattern matching for reusable per-domain experience files
- Most relevant borrow candidates for this repo:
  - stronger site-pattern / domain-experience layer
  - clearer split between cheap DOM operations and user-gesture-like operations
  - explicit environment/bootstrap diagnostics for browser connectivity
- Less attractive borrow point for now:
  - replacing the current Playwright runtime with a CDP-proxy-first architecture would trade away isolation and reproducibility in exchange for easier access to existing user sessions
