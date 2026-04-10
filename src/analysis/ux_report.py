"""Reviewer-style UX report built from captured artifacts."""

from __future__ import annotations

import os
from pathlib import Path

from src.agent.state import AgentState
from src.analysis.competitive_report import CompetitiveAnalysis
from src.analysis.ux_review import UXReviewFinding, UXReviewMemo, UXReviewOrchestrator


class UserExperienceReportGenerator:
    """Generate a richer UX review from the artifact-backed review memo."""

    def __init__(self) -> None:
        self.orchestrator = UXReviewOrchestrator()

    def generate(
        self,
        state: AgentState,
        analysis: CompetitiveAnalysis,
        page_insights: dict[str, dict] | None,
        extraction_results: dict[str, dict] | None,
        reports_dir: Path,
    ) -> str:
        memo = self.orchestrator.build(state, analysis, page_insights, extraction_results)

        lines = [
            "# User Experience Report",
            "",
            "## Overview",
            f"- Target: `{memo.target}`",
            f"- Evaluation mode: {memo.evaluation_mode}",
            f"- Evaluation lens: {', '.join(memo.evaluation_lens)}",
            f"- Overall assessment: {memo.overall_assessment}",
            "",
            self._overview_paragraph(memo),
            "",
            "## Exploration Scope",
        ]

        if memo.scope_paths:
            for path in memo.scope_paths:
                lines.append(f"- `{path}`")
        else:
            lines.append("- No captured paths were available for review.")

        if memo.scope_notes:
            lines.extend(["", *[f"- {note}" for note in memo.scope_notes]])

        lines.extend(["", "## Main Strengths"])
        if memo.strengths:
            lines.extend(self._finding_sections(memo.strengths))
        else:
            lines.append("The current artifact set did not surface strong UX strengths confidently.")

        lines.extend(["", "## Main Issues"])
        if memo.issues:
            lines.extend(self._finding_sections(memo.issues))
        else:
            lines.append("No strong UX issues were derived automatically from the current artifact set.")

        lines.extend([
            "",
            "## User Experience Judgment",
            "### For New Users",
            memo.new_user_judgment or "The current evidence is too thin to separate first-time user experience from general product quality.",
            "",
            "### For Experienced Users",
            memo.experienced_user_judgment or "The current evidence is too thin to judge expert-user efficiency reliably.",
        ])

        lines.extend(["", "## Highest-Priority Recommendations"])
        if memo.recommendations:
            for index, item in enumerate(memo.recommendations, start=1):
                lines.extend([
                    "",
                    f"### {index}. {item.title}",
                    item.action,
                    "",
                    f"Why this is high priority: {item.rationale}",
                ])
        else:
            lines.append("Capture a deeper task flow before making prescriptive UX changes.")

        lines.extend(["", "## Visual Evidence"])
        if memo.visuals:
            for item in memo.visuals:
                image_path = self._relative_path(Path(item.image_path), reports_dir)
                lines.extend([
                    "",
                    f"### {item.title}",
                    item.summary,
                    "",
                    f"![{item.title}]({image_path})",
                    "",
                    f"Why this screenshot matters: {item.caption}",
                ])
        else:
            lines.append("No report screenshots were selected from the current run.")

        lines.extend([
            "",
            "## Conclusion",
            memo.conclusion,
        ])
        return "\n".join(lines).strip() + "\n"

    def _overview_paragraph(self, memo: UXReviewMemo) -> str:
        top_strength = memo.strengths[0].title if memo.strengths else "no clear strength surfaced"
        top_issue = memo.issues[0].title if memo.issues else "no clear issue surfaced"
        return (
            f"This report is intentionally judgment-first rather than artifact-first. "
            f"The strongest positive signal from the current pass is that {top_strength.lower()}. "
            f"The main drag on the experience is that {top_issue.lower()}."
        )

    def _finding_sections(self, findings: list[UXReviewFinding]) -> list[str]:
        lines: list[str] = []
        for index, item in enumerate(findings, start=1):
            lines.extend([
                "",
                f"### {index}. {item.title}",
                item.summary,
                "",
                f"Why it matters: {item.why_it_matters}",
            ])
            if item.evidence:
                lines.extend([
                    "",
                    "Evidence observed:",
                    *[f"- {evidence}" for evidence in item.evidence],
                ])
        return lines

    def _relative_path(self, path: Path, reports_dir: Path) -> str:
        return os.path.relpath(path, reports_dir).replace("\\", "/")
