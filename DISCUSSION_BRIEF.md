# Frontend Recon Agent: Direction and Implementation Plan

## 1. Current Direction
The project is no longer framed as a narrow admin-site analysis pipeline. It is being evolved into a more general browser agent that can:

- take a target URL and a high-level goal
- complete multi-step flows such as sign-up, sign-in, onboarding, and guided entry
- continue exploring and understanding the product surface after entry
- preserve evidence, structured outputs, and final analysis artifacts when useful

We will continue to use Playwright as the browser execution layer. The main change is in the control layer: moving from a fixed pipeline to an agent loop.

## 2. Target End-to-End Flow
The intended full loop is:

1. Open the target site
2. Observe the current page
3. Decide the next action based on:
   - task goal
   - current state
   - what has already worked on the same site
4. Act:
   - navigate
   - click
   - fill forms
   - submit
   - switch tabs
   - open modals
5. Validate whether the action actually changed state
6. Re-observe after meaningful state changes
7. Continue until:
   - the goal is complete
   - budget is exhausted
   - a blocking challenge appears
8. Save evidence, structured outputs, and final analysis

In short:

`observe -> decide -> act -> validate -> re-observe -> continue`

Budget note:
- `max_depth` limits how far discovered targets can expand from the starting point
- `max_states` limits the total number of captured states in the run
- together they control exploration scope, but they should not be confused with a single breadth cap

## 3. Core Architecture Choice
For broader website coverage, strict `DOM-first` is no longer a sufficient control strategy.

The working direction is:

**DOM-grounded, vision/LLM-guided**

Meaning:
- DOM remains important for execution and extraction
- vision/LLM helps with page understanding and semantic classification
- browser control stays deterministic where possible
- the system should not assume every site is an admin dashboard

## 4. What We Are Borrowing
The system keeps Playwright, but borrows several higher-level browser-agent ideas:

### Goal-driven control
- actions are not executed in pure FIFO order
- goal-relevant actions are prioritized

### Validate-after-action
- clicks and submits are not assumed successful
- the runtime checks whether state changed meaningfully

### Site memory
- the run records what tends to work on the current domain
- examples:
  - selector success/failure
  - label success/failure
  - action-type success/failure
  - challenge events

### Challenge as normal state
- captcha / anti-bot is treated as a first-class runtime state
- the current policy is pause-and-report rather than blind retry

## 5. Current Implementation State
The current runtime already includes:

- Playwright browser control
- no-login public-site support
- task-aware `observe -> decide -> execute` loop
- repeated page understanding after important state changes
- lightweight site memory persisted as `site_memory.json`
- optional vision-enhanced page understanding
- structured extraction
- final analysis artifacts and optional LLM synthesis

## 6. Vision and LLM Usage
The system uses model APIs in two places:

### Vision
Purpose:
- classify current page
- detect major regions
- identify interaction hints
- improve page understanding beyond raw DOM

Decision:
- `vision.model` is now standardized to `gpt-5.4`

### Final synthesis
Purpose:
- turn structured evidence into a more readable final analysis

Decision:
- `synthesis.model` remains `gpt-5.4`

Important note:
- these are API-backed integrations
- normal chat subscriptions are not enough for runtime use

## 7. Main Implementation Priorities
The next important work is:

1. Continue weakening route-first assumptions
2. Improve repeated understanding after state changes
3. Strengthen sign-up / sign-in / onboarding handling
4. Improve handoff / resume around captcha and anti-bot
5. Expand extraction and analysis beyond admin-style pages

## 8. General Website Taxonomy
The project now uses a broader website taxonomy instead of forcing most pages into `list/form/dashboard`.

Current high-level page types include:
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

This broader taxonomy is important because target sites may include:
- public product sites
- content-heavy sites
- docs portals
- registration-gated applications
- growth / ad-platform websites

## 9. Extraction Direction
The original extraction bias was too tied to admin-style surfaces.

Current structured extraction exists for:
- list/table
- detail/key-value
- form/schema

The next extraction expansion should support more general public/product websites, especially:
- landing/content/docs surfaces
- hero and CTA areas
- navigation sections
- resource cards and content blocks

Important guardrail:
- rule-based extraction should remain structure-first and site-agnostic
- hard-coded text rules should be treated as soft hints, not the main decision boundary
- benchmark-site quirks should not be patched directly into the shared extractor/runtime path

## 10. Acceptance Criteria
The implementation direction is successful when:

- the agent can run end-to-end on both public and gated sites
- it can handle sign-up / sign-in / onboarding flows more reliably
- it produces evidence-backed outputs, not just transcripts
- it no longer forces general websites into admin-only taxonomy
- it remains explainable and auditable

## 11. One-Line Summary
This project is now a Playwright-based general browser agent with:

- goal-driven control
- validate-after-action behavior
- repeated understanding
- site memory
- API-backed vision and synthesis
- evidence-preserving outputs
