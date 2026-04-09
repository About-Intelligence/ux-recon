"""Prompt builders for final competitive-analysis synthesis."""

from __future__ import annotations

import json
from typing import Any


def build_synthesis_system_prompt() -> str:
    """Return the system prompt for final LLM synthesis."""
    return (
        "You are a product strategist writing a concise, evidence-backed competitive analysis. "
        "You receive deterministic crawl and extraction artifacts from a general website analysis pipeline. "
        "Do not invent evidence. If evidence is weak, say so explicitly. "
        "Return strict JSON with keys: executive_summary, product_positioning, key_workflows, "
        "differentiators, risks_and_unknowns, recommended_followups, markdown_report. "
        "The markdown_report should be a concise, readable report with sections: Executive Summary, "
        "Product Positioning, Key Workflows, Differentiators, Risks And Unknowns, Recommended Follow-ups."
    )


def build_synthesis_user_prompt(
    competitive_analysis: dict[str, Any],
    page_insights: dict[str, dict],
    extraction_results: dict[str, dict],
) -> str:
    """Build the user prompt with compact structured evidence."""
    compact_payload = {
        "competitive_analysis": competitive_analysis,
        "page_insights_sample": list(page_insights.values())[:12],
        "successful_extractions_sample": [
            result for result in extraction_results.values()
            if result.get("status") == "success"
        ][:12],
        "failed_extractions_sample": [
            result for result in extraction_results.values()
            if result.get("status") in {"failed", "empty"}
        ][:8],
    }
    return (
        "Synthesize the following crawl and extraction evidence into a competitive-analysis narrative. "
        "Stay grounded in the provided data, mention uncertainty where applicable, and keep conclusions specific.\n\n"
        f"{json.dumps(compact_payload, ensure_ascii=False, indent=2, default=str)}"
    )
