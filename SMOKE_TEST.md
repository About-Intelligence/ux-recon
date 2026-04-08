# Smoke Test Guide

## Purpose
This smoke test is meant to answer one question first:

**Can the current browser-agent stack start, call the configured model API, and produce the main artifact layers without immediately failing?**

It is not meant to prove final quality.

## Pre-Check
Before the first live run, confirm:

- `OPENAI_API_KEY` is available in the current terminal or VS Code session
- if you use a compatible third-party gateway, `VISION_API_BASE_URL` is also set
- Playwright Chromium is installed
- [config/settings.local.yaml](/d:/FrontendRecon/frontend_recon_agent/config/settings.local.yaml) points to a real target URL
- `vision.model` is set to `gpt-5.4`

Current local config file:
- [config/settings.local.yaml](/d:/FrontendRecon/frontend_recon_agent/config/settings.local.yaml)

## Step 1: Use a Small Test Budget
For the first live run, keep the budget small:

```powershell
python -m src.cli --max-states 10 --max-depth 2 --headless
```

Recommended first target types:
- a simple public product site with a small number of pages
- a low-risk registration or onboarding flow
- not a site with destructive actions

## Step 2: Check Main Artifacts
After the run, confirm these exist:

- [output/artifacts/inventory.json](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/inventory.json)
- [output/artifacts/sitemap.json](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/sitemap.json)
- [output/artifacts/coverage.json](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/coverage.json)
- [output/artifacts/site_memory.json](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/site_memory.json)
- [output/artifacts/dataset.jsonl](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/dataset.jsonl)
- [output/artifacts/competitive_analysis.json](/d:/FrontendRecon/frontend_recon_agent/output/artifacts/competitive_analysis.json)
- [output/reports/exploration_report.md](/d:/FrontendRecon/frontend_recon_agent/output/reports/exploration_report.md)
- [output/reports/competitive_analysis.md](/d:/FrontendRecon/frontend_recon_agent/output/reports/competitive_analysis.md)

If `vision.enabled = true`, also check:
- `output/artifacts/vision/`
- `output/artifacts/page_insights/`

## Step 3: What to Inspect First
Do not start by reading every log line. First inspect:

1. Did the run complete or pause with a clear reason?
2. Did the model call succeed?
3. Did the agent capture at least one real state after acting?
4. Did `site_memory.json` record action outcomes?
5. Did the final artifacts contain non-empty, believable data?

## Common Failure Cases
- `missing api key`
  - the current process does not see `OPENAI_API_KEY`
- `http 404` or `model not found`
  - your provider does not support that model name
- `vision_error`
  - the provider endpoint may not support image chat payloads in the current format
- immediate `captcha_or_antibot_detected`
  - the agent hit a challenge state and paused by policy
- empty extraction / weak report
  - the run may still be valid as a smoke test; quality tuning is a later step

## Suggested First Sequence
Use this order:

1. Confirm `OPENAI_API_KEY` is visible in the current session
2. Keep `vision.model = gpt-5.4`
3. Run a tiny browser-agent smoke test
4. Review artifacts, then tune prompts or config
