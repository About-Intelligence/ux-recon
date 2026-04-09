# Task Plan: General Browser Agent Pivot

## Goal
Evolve `frontend_recon_agent` from a deterministic exploration framework into a more general browser agent that can:

- accept a target URL and high-level task intent
- complete multi-step website onboarding flows such as registration and guided entry
- browse and understand product surfaces across a broader range of websites, not only admin dashboards
- handle more dynamic flows with repeated page understanding and step-by-step control
- preserve evidence and structured outputs for downstream competitive analysis when useful

## Current Phase
Phase 8 - General browser-agent pivot and general-site validation

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
- [x] Test on at least one representative general website target
- [x] Confirm final output is stronger than a generic browser-agent transcript for competitive analysis
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

### Phase 9: Evidence-Quality Validation
- [x] Define an explicit comparison frame between plain browser transcripts and this repo's evidence outputs
- [x] Inspect current artifact/report structure against that comparison frame
- [x] Identify the weakest gaps for general-website competitive analysis
- [x] Implement the highest-value reporting or aggregation improvements if needed
- [x] Document the proof points and remaining limitations
- **Status:** in_progress

### Phase 10: Evidence Schema Refactor
- [x] Define a concrete `EvidenceUnit` shape inside extraction outputs
- [x] Split general-site content extraction into collectors, normalization, and assembly steps
- [x] Preserve anchored page evidence in `dataset.jsonl`
- [x] Surface page-level evidence samples in competitive-analysis reporting
- [x] Reduce over-collection and low-value navigation noise, especially social/utility/auth duplicates
- [ ] Improve remaining mojibake cleanup for a few stubborn strings
- **Status:** in_progress

## Current Proof Points
- `run_log.jsonl` records step execution, but not reusable product structure
- `page_insights` now preserve general-site page semantics such as `landing`, `content`, and `docs`
- `dataset.jsonl` now captures structured `content_blocks` evidence including hero titles, CTAs, nav items, and content sections
- `competitive_analysis.json/.md` aggregate those signals into category guesses, strengths, gaps, differentiators, and evidence index entries
- A 2026-04-09 live run against `python.org` produced 6 route captures and 4 successful `content_blocks` extractions
- A later 2026-04-09 refactor pass upgraded `dataset.jsonl` to include `evidence_units` with anchors such as `locator`, `dom_path`, `html_fragment`, and `screenshot_ref`
- A later 2026-04-09 validation pass fixed route resolution for relative navigation targets, so `Downloads` and `About` now resolve to `www.python.org` pages instead of incorrect `docs.python.org/...` 404 routes
- The same pass reduced discovered targets from 14 to 12 and improved extraction results from 4 successful / 2 empty to 5 successful / 1 empty
- A final 2026-04-09 evidence pass tightened nav collection to top-level navigation and removed social/auth duplication from `dataset.jsonl`, reducing `nav_item_count` from 16 to 12 on the representative `python.org` pages
- A later 2026-04-09 generalization pass improved `content_section` coverage substantially on `python.org` content pages, while also replacing lingering admin-centric scoring/report wording with more general application-surface language
- A later 2026-04-09 vision-assisted docs pass used existing vision hints to rescue weak docs-section extraction on `https://docs.python.org/3/`, improving that page from `0 sections` to `10 sections` in a docs-only smoke test

## Today Scope Update
- Skip `vision disabled` and `vision graceful degradation` validation for now
- Treat repeated vision/API failure as retriable runtime failure that should eventually surface an explicit error
- Use a representative general website rather than an admin/SaaS target
- Prioritize proving that final outputs are more useful for competitive analysis than a plain action transcript
- Keep the shared rule layer site-agnostic:
  - prefer structural heuristics over target-site strings
  - treat textual keywords as weak hints instead of hard gates when possible
  - do not patch benchmark-site quirks directly into shared extractor logic
