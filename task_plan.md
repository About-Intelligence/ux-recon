# Task Plan: Frontend Mimic Agent Framework

## Goal
Build a budget-aware, policy-driven browser agent framework for autonomous website exploration, artifact collection, and selective analysis.

## Current Phase
Phase 7 — Testing (ready to test)

## Phases

### Phase 0: Architecture Discussion & Design
- [x] Review user requirements
- [x] Propose revised architecture
- [x] User approval of ARCHITECTURE.md
- **Status:** complete

### Phase 1: Data Models + State Machine Shell
- [x] Pydantic/dataclass models in `agent/state.py`
- [x] Engine loop with phase transitions in `agent/engine.py`
- [x] JSONL logger in `agent/logger.py`
- [x] Updated config.py with budget/exploration settings
- **Status:** complete

### Phase 2: Execution Layer
- [x] Refactor `browser/controller.py` — clean single-action interface
- [x] Extract `browser/authenticator.py`
- **Status:** complete

### Phase 3: Observation Layer
- [x] `observer/extractor.py` — candidate detection
- [x] `observer/fingerprint.py` — DOM structural hashing
- [x] `observer/novelty.py` — novelty scoring
- **Status:** complete

### Phase 4: Wire It Together
- [x] Complete `agent/engine.py` with real browser + observer
- [x] BFS frontier, retry/backtrack logic
- [x] `cli.py` entry point
- **Status:** complete

### Phase 5: Artifact Generation
- [x] `artifacts/manager.py` — save/load, path management
- [x] `artifacts/inventory.py` — page inventory JSON
- [x] `artifacts/sitemap.py` — traversal graph JSON
- [x] `artifacts/report.py` — markdown report
- **Status:** complete

### Phase 6: Analyzer Integration
- [x] Port existing `page_analyzer.py` (new single-page interface)
- [x] Hook into ANALYZE phase
- [x] Per-state analysis outputs
- **Status:** complete

### Phase 7: Testing + Polish
- [x] All 21 Python files pass syntax check
- [x] All imports verified
- [x] Data model unit tests pass
- [x] Fingerprint/novelty scoring verified
- [x] Page analyzer verified
- [x] Updated README, pyproject.toml, requirements.txt, config files
- [x] Removed old ai/ and generator/ modules
- [ ] Test on labverix.com (live run)
- **Status:** in_progress
