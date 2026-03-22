# Progress Log

## Session 1 — 2026-03-19
- Built initial project: login, BFS crawl, deep interaction, analysis, Vue generation
- Captured 68 pages/interactions from labverix.com
- Fixed 94 robustness issues

## Session 2 — 2026-03-22
- Major refactor: linear script → agent framework (v2.0)
- Built 7 phases: data models, execution, observation, engine, artifacts, analyzer, CLI
- Live testing revealed 3 bugs:
  1. Sub-menu titles matched as nav targets (`.el-sub-menu__title` expands, doesn't navigate)
  2. No deduplication by href — frontier exploded to 1700+ targets
  3. Child menu-item filter incorrectly skipped `<a>` wrappers around `<li class="el-menu-item">`
- Fixed: dedup by href/label, removed child filter, added submenu expansion, parent-page navigation
- Successful run: 100 states captured, 28 routes, 12 novel analyses, 23 min duration
- All artifacts generated: inventory.json, sitemap.json, run_log.jsonl, exploration_report.md
