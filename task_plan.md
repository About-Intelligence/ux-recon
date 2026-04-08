# Task Plan: General Browser Agent Pivot

## Goal
Evolve `frontend_recon_agent` from a deterministic exploration framework into a more general browser agent that can:

- accept a target URL and high-level task intent
- complete multi-step website onboarding flows such as registration and guided entry
- browse and understand product surfaces across a broader range of websites, not only admin dashboards
- handle more dynamic flows with repeated page understanding and step-by-step control
- preserve evidence and structured outputs for downstream competitive analysis when useful

## Current Phase
Phase 8 - General browser-agent pivot and live validation

## Phases

### Phase 0: Existing Recon Framework Baseline
- [x] Review current project architecture and runtime behavior
- [x] Confirm current route-first BFS exploration model
- [x] Confirm current artifacts, analyzer, and logging capabilities
- **Status:** complete

### Phase 1: Product Direction and External Research
- [x] Define new end goal as competitive analysis, not generic browser automation
- [x] Research browser-agent product patterns across Stagehand, Browser Use, Skyvern, Firecrawl, OpenClaw
- [x] Clarify Ponder as artifact/workflow inspiration rather than direct browser-agent competitor
- [x] Write implementation strategy and comparison framing
- **Status:** complete

### Phase 2: Planning and Implementation Breakdown
- [x] Create and maintain a single combined direction + implementation document in `DISCUSSION_BRIEF.md`
- [x] Record vision-augmented discovery as the first major increment
- [x] Record two future skill candidates:
  - `competitive-analysis-review`
  - `browser-agent-benchmark`
- **Status:** complete

### Phase 3: Vision Foundation
- [x] Add `vision` configuration section
- [x] Add vision artifact directories and save helpers
- [x] Add typed models for vision results and page insights
- [x] Add prompt builder and placeholder vision client
- [x] Integrate vision into `OBSERVE`
- [x] Generate DOM summary for multimodal calls
- [x] Persist per-page vision artifacts during real runs
- [x] Replace placeholder vision client with real OpenAI-compatible API path
- **Status:** in_progress

### Phase 4: Page Insight and Candidate Reranking
- [x] Create per-page insight artifacts that merge DOM and vision understanding
- [x] Add route-candidate reranking rules driven by page type and regions
- [ ] Preserve route frontier semantics while improving prioritization
- **Status:** pending

### Phase 5: Structured Extraction
- [x] Add extraction subsystem
- [x] Implement list/table extractor
- [x] Implement detail/key-value extractor
- [x] Implement form/schema extractor
- [x] Emit `dataset.jsonl`, `dataset_summary.json`, `extraction_failures.json`
- **Status:** complete

### Phase 6: Competitive Analysis Artifacts
- [x] Add `competitive_analysis.json`
- [x] Add `competitive_analysis.md`
- [x] Aggregate evidence-backed feature, entity, and workflow findings
- [x] Ensure the report is readable without raw log inspection
- [x] Add optional LLM synthesis layer for the final competitive-analysis report
- **Status:** complete

### Phase 7: Validation and Demo Readiness
- [x] Fix page-type fallback so report/extraction layers do not get stuck on `unknown`
- [x] Include interaction captures in structured extraction
- [x] Honor `vision.max_image_side` and use viewport screenshots for vision understanding
- [x] Remove internal extraction strategy names from competitive-analysis module inference
- [x] Deduplicate page-insight aggregation by URL in report and competitive-analysis layers
- [x] Preserve interaction identity in extraction artifacts
- [x] Improve feature-module inference for hash-routed admin SPAs
- [x] Reduce vision-call amplification by using DOM-only page understanding for interaction captures
- [ ] Verify the system still runs when vision is disabled
- [ ] Verify the system degrades gracefully when vision API fails
- [ ] Test on at least one representative admin/SaaS target
- [ ] Confirm final output is stronger than a generic browser-agent transcript for competitive analysis
- **Status:** in_progress

### Phase 8: General Browser-Agent Pivot
- [ ] Reframe system from `DOM-grounded competitive-analysis pipeline` to `general browser agent with evidence outputs`
- [x] Record borrow points from `web-access` while keeping Playwright as the browser runtime
- [x] Add goal-driven decision prioritization instead of pure FIFO step execution
- [x] Add validate-after-action checks so clicks and submits must show meaningful state change
- [x] Add first-pass site memory so the run can remember what works on the current domain
- [x] Reduce reliance on route-first DOM discovery as the only decision source by adding page-level decision planning
- [x] Design repeated page-understanding / re-observation triggers after key state changes
- [x] Add first-pass support for broader end-to-end flows such as form fill and submit
- [x] Define first-pass approach for captcha / anti-bot detection and pause-and-report handling
- [x] Select a simple public website for first live API smoke test
- [x] Add a smoke-test runbook for the first live validation pass
- [x] Run a minimal external smoke test with the newly obtained API key
- [x] Standardize `vision.model` to `gpt-5.4`
- **Status:** in_progress
