# Findings

## Current Project Reality

### Core exploration model
- The engine is not a generic agent loop; it is a deterministic route-first exploration pipeline
- Only `ROUTE` targets enter the BFS frontier
- Page-local interactions such as dropdown items, tabs, add modals, and expanded rows are explored inline after a route is captured

### New direction after leader sync
- The current DOM-grounded / route-first model is no longer sufficient as the long-term control strategy
- The project now needs to move toward a more general browser-agent architecture
- Target websites may include:
  - multi-step LLM experience websites
  - ad-platform or growth-tool websites
  - registration-first products where access requires completing onboarding before browsing
- The system may need to handle captcha / anti-bot friction and should be prepared for human-in-the-loop or fallback handling

### Current strengths
- Strong artifact discipline already exists: screenshots, HTML snapshots, inventory, sitemap, run log, analysis
- The project is well-suited to admin/SaaS/backoffice environments
- DOM fingerprinting and novelty scoring already reduce redundant captures
- The current codebase is more explainable and reproducible than prompt-first browser agents

### Current gap relative to the new goal
- The system now outputs competitive-analysis artifacts, but live validation with a real vision provider is still pending
- Vision-assisted page understanding is integrated, but prompt quality and provider compatibility still need calibration on real targets
- Structured extraction exists for list/detail/form patterns, but heuristics still need tuning on representative general websites
- The competitive-analysis layer is functional, but final demo quality still depends on end-to-end validation and evidence quality checks

## 2026-04-09 Scope Update

### Validation scope narrowed by user
- We are not treating `vision disabled` behavior or `vision API graceful degradation` as today's acceptance criteria
- Runtime policy for vision/API failures is now:
  - retry repeated calls
  - if repeated attempts still fail, surface an explicit error
- This means today's work should focus on artifact quality and general-website validation, not fallback UX

### Validation target broadened beyond admin/SaaS
- The next real validation target should be a more general website rather than an admin/SaaS product
- This aligns with the current direction shift away from admin-first assumptions
- Any remaining heuristics or report framing that still center admin/SaaS should be treated as quality debt

### Main proof obligation for today
- The most important thing to demonstrate is not merely that the browser run completes
- We need to show that the repo's outputs are more useful for competitive analysis than a plain browser transcript because they preserve:
  - structured page insights
  - extracted entities and workflows
  - evidence-backed summaries
  - reusable artifacts for follow-up comparison

## 2026-04-09 Live Validation Result

### Representative general-site run completed
- We ran a new live validation pass against `https://www.python.org/` with a 6-state budget
- The run completed successfully after rerunning outside the sandbox so Playwright could launch Chromium
- Final result:
  - 6 states captured
  - 14 targets discovered
  - 6 extraction results generated
  - 4 successful extractions

### Highest-value gap found and fixed
- The main weakness for general websites was not browser control
- It was that page understanding had become broader (`landing/content/docs`), while structured extraction still only supported `list/detail/form`
- This caused general-site pages to fall back to `unknown` extraction strategy or produce weak evidence
- We fixed that by adding a new `content_blocks` extraction path for:
  - hero titles
  - primary CTAs
  - navigation items
  - content sections

### Why the outputs are now stronger than a plain transcript
- A plain transcript tells us the agent clicked `root -> Community -> Docs -> Downloads -> About -> Documentation`
- The updated artifacts now additionally tell us:
  - the site looks like `content_or_marketing`, not `admin_saas`
  - the page mix is `landing/content/docs`
  - the homepage exposes concrete entry points such as sign-in, sign-up, getting started, downloads, and documentation
  - docs surfaces expose concrete informational sections and build/setup themes
  - the final report can cite evidence rows instead of relying only on procedural narration

### Current remaining limitations
- Some extracted strings still contain noisy glyphs from page text normalization
- Some pages still return empty `content_blocks` results, especially when their DOM is sparse or atypical
- Category scoring still slightly overweights old admin-style signals through `admin_maturity_score`

## 2026-04-09 Evidence Schema Refactor

### What changed
- We added a concrete `EvidenceUnit` structure to extraction outputs
- The general-site extraction path is no longer a single monolithic extractor pass
- It now follows:
  - collectors
  - normalizer
  - assembler
- This gives each extracted item:
  - a kind
  - a role
  - raw and normalized text
  - a locator
  - a DOM path
  - an HTML fragment
  - a screenshot reference

### Why this matters
- The project now stores page-level evidence in a form that is closer to the intended long-term evidence model
- Reports can now show sample evidence rows instead of only count summaries
- The extraction layer is more aligned with the agentic architecture discussion:
  - the loop decides what to do
  - the evidence layer decides what to preserve

### Live validation after the refactor
- We reran the same `python.org` validation after the schema refactor
- The live run still completed successfully
- The resulting outputs now include:
  - `evidence_units` inside `dataset.jsonl`
  - `Evidence Samples` in `competitive_analysis.md`
  - cleaner normalized titles such as:
    - `Build using make / make.bat`
    - `Getting started`
    - `Introduction`

### Remaining issues after the refactor
- A few mojibake strings still remain, for example `All the Flow You鈥檇 Expect`
- Some pages still produce empty evidence because current collectors are not broad enough for those DOM shapes
- Navigation evidence is still somewhat noisy on pages with utility controls or accessibility toggles

## 2026-04-09 Route Resolution and Nav Filtering Follow-Up

### Root cause behind the old `downloads/about` empties
- The weakest `downloads/about` results were not only an extraction-coverage issue
- We found that some captured HTML snapshots for those routes were actually `404 Not Found` pages
- The navigation extractor was storing relative hrefs and later navigation resolved them against the current page host
- This produced wrong-domain URLs such as `docs.python.org/downloads/` instead of `www.python.org/downloads/`

### Fix applied
- Route candidates are now normalized to absolute URLs at discovery time
- This keeps later navigation anchored to the source page where the link was discovered
- We also added a first pass of low-value navigation filtering in both:
  - `src/observer/extractor.py`
  - `src/extraction/content_collectors.py`

### Validation result after the fix
- A fresh 2026-04-09 live run against `python.org` now reaches:
  - `https://www.python.org/downloads/`
  - `https://www.python.org/about/`
  - `https://www.python.org/doc/`
- Current result:
  - 6 states captured
  - 12 targets discovered
  - 5 successful extractions
  - 1 empty extraction

### Main remaining issue
- The biggest remaining evidence-quality issue is no longer route correctness
- It is over-collection inside `nav_item` evidence:
  - social links
  - utility controls
  - auth links duplicated across CTA and nav evidence
- That is now the most valuable next cleanup target

### Follow-up result after collector tightening
- We tightened `content_collectors.py` to prioritize top-level navigation selectors instead of sweeping all `header a` links
- We also explicitly filtered:
  - social links
  - chat/community links that behave like social follow-ons
  - auth labels and auth URLs already represented as CTAs
- A fresh live rerun showed the intended improvement:
  - `nav_item_count` dropped from 16 to 12
  - `LinkedIn`, `Mastodon`, `Twitter`, `Chat on IRC`, `Sign In`, and `Sign Up / Register` no longer appear as `nav_item` evidence
- The remaining navigation evidence is still broad, but it is now much closer to a useful site-structure summary than before

## 2026-04-09 Overfit Guardrail Update

### New concern raised
- Some of the latest rule-layer changes improved the `python.org` benchmark result, but they also risked overfitting the shared heuristics to one validation target
- The most obvious smell was site-specific text appearing directly in shared filters

### Updated stance
- Shared collectors and candidate extractors should stay structure-first
- Site-specific strings should not live in the core runtime path
- Textual phrases can still exist, but should be treated as weak scoring hints rather than hard inclusion/exclusion rules whenever possible

### Immediate fix applied
- Removed the explicit `the python network` special case from shared low-value navigation filters
- Removed hard CTA allowlist behavior and replaced it with a more general scoring approach:
  - DOM position
  - button/CTA class hints
  - href validity
  - short action-oriented labels as a soft boost
- This keeps the rule layer broader and lowers the chance that future benchmark runs will distort the shared extractor

## 2026-04-09 Section Coverage and Analysis Reframing

### Section coverage improved
- We broadened `content_section` extraction from narrow container selectors into heading-and-container assembly
- This improved coverage materially on the representative `python.org` run:
  - root: `content_section_count` 0 -> 9
  - community: 0 -> 8
  - about: 0 -> 7
  - documentation: 0 -> 7
- The remaining weak spot is `docs.python.org/3/`, which still produced 0 sections in this small-budget run

### Analysis wording updated
- The competitive-analysis layer no longer uses the old `admin_maturity_score` label
- It now reports `application_surface_score`
- The synthesis prompt was also updated so the final narrative no longer frames the whole system as an `admin/SaaS` pipeline

### New residual risk
- The broader CTA scorer now generalizes better than a hard keyword allowlist
- But it also captures some promotional or download links that are not always the most important user entry points
- This is a healthier failure mode than benchmark-specific overfit, but it is still a ranking-quality issue worth refining later

## 2026-04-09 Vision-Assisted Docs Section Rescue

### Why this was the right place to use vision
- The weakest remaining page was `https://docs.python.org/3/`
- Its screenshot was visually clear, and the existing vision output already described it as:
  - a docs landing page
  - with main blue link titles acting as documentation section navigation
- So the best fit was not to replace DOM extraction, but to let vision trigger a DOM-grounded rescue path

### What changed
- We now pass the persisted `vision_result` into content extraction
- When a page is classified as `docs` and generic section extraction yields no `content_section` units:
  - vision hints can trigger a docs-specific rescue path
  - the rescue path looks for:
    - strong-label section headers followed by grouped docs tables/lists
    - `p.biglink` style docs index entries with short descriptions
- The resulting evidence still lands as anchored DOM evidence, not free-floating vision summaries

### Targeted validation result
- Added a docs-only smoke config targeting `https://docs.python.org/3/`
- A focused rerun produced:
  - `content_section_count = 10`
  - docs section groups such as:
    - `Documentation sections`
    - `Indices, glossary, and search`
    - `Project information`
    - `Tutorial`
    - `Library reference`
    - `Language reference`

### Remaining tradeoff
- The fix solved the `0 sections` problem cleanly
- But the page still shows another quality issue:
  - CTA evidence is broad and overlaps with docs navigation links
- That is now a separate ranking/role-classification problem rather than a section-detection failure

## Product Research Takeaways

### Stagehand
- Strongest idea to borrow: explicit high-level primitives such as observe/act/extract
- Best fit for this repo: clarify internal runtime boundaries, not switch to prompt-led control flow

### Browser Use
- Strongest idea to borrow: session and observability product mindset
- Best fit for this repo: better insight artifacts and run traceability

### Skyvern
- Strongest idea to borrow: computer-vision-based page understanding for messy frontends
- Best fit for this repo: visual page understanding in `OBSERVE`, not vision-led clicking

### Firecrawl
- Strongest idea to borrow: schema-first extraction and data-product framing
- Best fit for this repo: produce structured dataset artifacts instead of only reports

### OpenClaw
- Strongest idea to borrow: controlled browser-tool boundaries
- Best fit for this repo: keep execution deterministic and well-isolated

### Ponder
- Ponder appears more relevant as an artifact/workflow inspiration than as a browser-agent competitor
- Best fit for this repo: make outputs persistent, structured, and reusable for follow-up analysis

## Architecture Decisions for This Upgrade

### Vision role
- Chosen role: vision-enhanced discovery, not vision fallback, not vision-led execution
- Reason: fallback thresholds are ambiguous, while a fixed vision step in `OBSERVE` is easier to reason about and evaluate

### Vision input shape
- Screenshot + URL + lightweight DOM summary
- Avoid sending full HTML in v1 to control cost and complexity

### Vision output shape
- Structured JSON only
- Minimum fields:
  - `page_type`
  - `confidence`
  - `regions`
  - `interaction_hints`
  - `extraction_hints`
  - `notes`

### Vision merge strategy
- DOM remains the primary source of executable candidates
- Vision is used to:
  - annotate page semantics
  - rerank DOM-derived route candidates
  - guide later extraction strategy

### Direction change implied by new scope
- For broader website coverage, vision should no longer be treated only as advisory page classification
- The next architecture likely needs repeated page understanding and step-level planning
- This pushes the system closer to mainstream browser-use agents:
  - observe
  - decide next action
  - act
  - re-observe
  - continue until task or budget ends
- Deterministic evidence capture still remains a differentiator and should be preserved
- A practical migration path is:
  - keep the current browser control and artifact stack
  - introduce a generic decision object and loop skeleton first
  - progressively reduce hard-coded route-first assumptions
  - later add onboarding, captcha handling, and human-in-the-loop states

### Borrow points now adopted from `web-access`
- Keep the browser runtime on Playwright, but move the control logic toward a goal-driven browser agent
- Treat each step as `observe -> decide -> act -> validate -> continue`, not just `act and assume success`
- Preserve lightweight site memory inside the run so the agent can bias toward selectors, labels, and action types that already worked on the same domain
- Treat captcha / anti-bot and similar blockers as normal runtime states that should be surfaced and remembered

### First agent-loop migration step now implemented
- The main engine loop now uses an explicit `observe -> decide -> execute` structure
- Route navigation is still the current execution behavior, but the control surface is no longer tied directly to route selection
- Re-observation after meaningful state changes is now part of the runtime
- Captcha / anti-bot detection has a first-pass pause-and-report implementation
- The runtime now has two decision sources:
  - route frontier
  - page-level planned actions such as tabs, add/create buttons, and onboarding-style primary CTAs
- The runtime now also has a first-pass form action:
  - detect visible auth/onboarding-like forms
  - heuristically fill fields from task/login profile values
  - submit and capture the resulting state

### Additional loop upgrades now implemented
- Pending decisions are no longer consumed in pure FIFO order; they are scored against:
  - the current task goal
  - optional goal keywords
  - per-domain action memory from the current run
- Important clicks and form submits now validate whether they produced meaningful state change
- The runtime now persists `site_memory.json`, including:
  - selector success / failure counts
  - label success / failure counts
  - action-type success / failure counts
  - challenge events

### First live-validation utilities now added
- Added `SMOKE_TEST.md` so the first live validation run has a fixed, repeatable checklist

### Current model decision
- Current practical local default:
  - `vision.model = gpt-5.4`
  - `synthesis.model = gpt-5.4`

### Public-site smoke test compatibility
- The authenticator now degrades gracefully for public websites:
  - when no credentials are configured, it navigates to the target URL and continues
  - session checks and re-login no longer block public-site runs
- This makes first live smoke tests possible on simple public targets before trying registration-gated products

### First live smoke test result
- A full smoke test against `https://www.python.org/` completed successfully with:
  - browser launch
  - vision-enabled observation
  - route capture
  - artifact generation
  - final competitive-analysis outputs
- The run captured 8 states and produced:
  - inventory
  - sitemap
  - coverage
  - site memory
  - dataset artifacts
  - competitive-analysis artifacts
- The test also confirmed an important limitation:
  - current heuristics are still too admin-biased for general public websites
  - the system classified `python.org` as `admin_saas`
  - page typing and extraction strategy selection over-classified pages as `form`
  - framework / UI-library inference produced false positives

### Post-bias-reduction position
- After broadening taxonomy and normalizing loose vision outputs, the system no longer collapses `python.org` into `admin_saas`
- Vision-model probing and comparison utilities have been removed to keep the runtime path simpler
- We are standardizing on `gpt-5.4` for vision going forward

### Skillization boundary
- Good future skill candidates:
  - `competitive-analysis-review`
  - `browser-agent-benchmark`
- Not suitable as skills:
  - browser execution
  - vision API runtime calls
  - extraction engine
  - artifact persistence
  - candidate reranking logic

### Final analysis boundary
- Deterministic aggregation should remain the stable, auditable base layer
- Final competitive-analysis prose is a good place to add optional LLM synthesis
- This keeps browser control deterministic while still improving the quality of the final report

## Code Changes Completed So Far
- Added `vision` config skeleton in `src/config.py` and `config/settings.yaml`
- Added artifact manager support for:
  - `output/artifacts/vision/`
  - `output/artifacts/page_insights/`
- Added typed models in:
  - `src/vision/types.py`
  - `src/analysis/competitive_report.py`
- Added prompt and placeholder client in:
  - `src/vision/prompts.py`
  - `src/vision/client.py`
- Consolidated the project direction and implementation plan into:
  - `DISCUSSION_BRIEF.md`
- Integrated vision-aware observation into `src/agent/engine.py`
- Added lightweight DOM summary generation during `OBSERVE`
- Added per-page insight persistence and report-level page semantics summary
- Added structured extraction subsystem in `src/extraction/`
- Hooked extraction into route capture flow after page analysis
- Added dataset artifacts:
  - `dataset.jsonl`
  - `dataset_summary.json`
  - `extraction_failures.json`
- Added competitive-analysis generator and final outputs:
  - `competitive_analysis.json`
  - `competitive_analysis.md`

## Runtime Integration Notes

### What is implemented now
- During `OBSERVE`, the engine now:
  - extracts DOM candidates
  - builds a lightweight DOM summary
  - calls the vision client when `vision.enabled = true`
  - persists page insight artifacts
  - reranks route candidates using page-type hints

## Review Fixes Applied

### Page-type fallback
- The runtime, exploration report, and competitive-analysis layer now explicitly fall back from `page_type_vision = "unknown"` to DOM-derived page type
- This prevents `unknown` from overwriting valid DOM classifications in extraction and final reporting

### Interaction extraction
- Captured interaction states now flow through structured extraction, not only analyzer output
- This improves coverage for modal, tabbed, drawer, and inline-detail workflows

### Vision payload control
- Vision understanding now uses viewport screenshots instead of full-page screenshots
- The client also resizes screenshots to respect `vision.max_image_side` before upload

### Competitive-analysis cleanup
- `feature_modules` no longer mixes internal extraction strategy names into module inference
- Report and competitive-analysis aggregation now deduplicate page insights by URL, preferring captured states over `observe_*` placeholders

## Additional Pre-Flight Review Findings

### SPA/hash-route module inference is still too weak
- Fixed by teaching `competitive_report.py` to derive module paths from hash-router fragments before falling back to `urlparse(url).path`

### Interaction extraction still loses interaction identity
- Fixed by adding `capture_label` and `capture_context` to extraction artifacts
- This now preserves which tab, dropdown item, modal, or route produced each extracted result

### Vision cost can still spike during extraction-heavy runs
- Reduced by making interaction-derived extraction fall back to DOM-only page understanding instead of always invoking multimodal vision
- Route captures still use vision when enabled; interaction captures now avoid unnecessary extra API calls
- The runtime still keeps route discovery DOM-first
- Vision is advisory and does not create new executable selectors

### Current limitation
- `VisionClient` now supports an OpenAI-compatible multimodal chat-completions path
- It resolves credentials from `VISION_API_KEY` or the configured env var
- It still degrades safely when:
  - provider is unsupported
  - API key is missing
  - network/API request fails
  - JSON parsing fails
- Runtime network behavior has not yet been live-validated in this session

## Vision Provider Notes
- Current provider path: OpenAI-compatible `/chat/completions`
- Current payload style:
  - system prompt
  - user text prompt
  - inline `data:image/png;base64,...` screenshot
  - `response_format: json_object`
- Current implementation intentionally avoids adding a new SDK dependency
- This keeps setup lighter, but means compatibility depends on provider support for OpenAI-style vision chat payloads

## Open Decisions Still Ahead
- Exact vision provider API integration details
- Whether the engine should move from route-first BFS to a more general step-based agent loop
- How to trigger repeated page understanding after navigation, modal open, tab switch, form progress, or failed action
- How to handle captcha / anti-bot challenges:
  - human-in-the-loop
  - pause and surface evidence
  - fallback retry logic
- Which public site should be used for first live API smoke test
- Extraction confidence and failure taxonomy refinement
- Final competitive-analysis scoring/summary heuristics

## Extraction Design Notes
- Extraction currently runs only on captured route pages
- The dispatcher uses page insight strategy:
  - `list_table`
  - `detail_fields`
  - `form_schema`
- Empty results are preserved as artifacts instead of being silently discarded
- This keeps the system auditable and useful for later competitive-analysis synthesis
- Captured route pages now generate a page insight on demand before extraction if one does not already exist
- This prevents extraction from falling back to `unknown` strategy simply because `OBSERVE` has not revisited that route yet

## Competitive Analysis Layer Notes
- Competitive analysis is now generated from:
  - runtime state
  - page insights
  - extraction results
  - analysis results
- Current summary includes:
  - product category guess
  - admin maturity score
  - data density score
  - workflow complexity score
  - observed strengths and gaps
  - key differentiators
- Current implementation is heuristic but already produces structured outputs suitable for iteration
