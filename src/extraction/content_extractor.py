"""Content/marketing/docs extractor for general websites."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from src.extraction.content_collectors import ContentCollectors
from src.extraction.evidence_normalizer import EvidenceNormalizer
from src.extraction.types import EvidencePaths, ExtractionResult


class ContentExtractor:
    """Collects, normalizes, and assembles evidence for general websites."""

    def __init__(self) -> None:
        self._collectors = ContentCollectors()
        self._normalizer = EvidenceNormalizer()

    def extract(
        self,
        html: str,
        state_id: str,
        target_id: str,
        url: str,
        page_type: str,
        evidence_paths: EvidencePaths,
        page_insight: dict[str, Any] | None = None,
        vision_result: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        soup = BeautifulSoup(html, "lxml")

        raw_units = self._collectors.collect(
            soup=soup,
            url=url,
            page_type=page_type,
            screenshot_ref=evidence_paths.screenshot,
        )
        if self._should_attempt_docs_rescue(page_type, raw_units, vision_result):
            raw_units.extend(self._collectors.collect_docs_rescue_units(
                soup=soup,
                url=url,
                page_type=page_type,
                screenshot_ref=evidence_paths.screenshot,
            ))
        evidence_units = self._normalizer.normalize_units(raw_units)
        records = self._assemble_records(evidence_units)

        status = "success" if evidence_units else "empty"
        confidence = 0.72 if records else 0.3

        return ExtractionResult(
            state_id=state_id,
            target_id=target_id,
            url=url,
            page_type=page_type,
            strategy="content_blocks",
            status=status,
            confidence=confidence,
            evidence_units=evidence_units,
            records=records,
            summary=self._build_summary(evidence_units),
            evidence_paths=evidence_paths,
        )

    def _should_attempt_docs_rescue(
        self,
        page_type: str,
        raw_units: list,
        vision_result: dict[str, Any] | None,
    ) -> bool:
        if page_type != "docs":
            return False
        if any(unit.kind == "content_section" for unit in raw_units):
            return False
        if not vision_result:
            return False

        extraction_hints = [str(item).lower() for item in vision_result.get("extraction_hints", [])]
        interaction_labels = [
            str(item.get("label", "")).lower()
            for item in vision_result.get("interaction_hints", [])
            if isinstance(item, dict)
        ]
        text = " ".join(extraction_hints + interaction_labels)
        return any(
            hint in text for hint in [
                "section links",
                "documentation landing",
                "group each blue heading",
                "primary navigation targets to documentation sections",
                "main documentation home content",
            ]
        )

    def _assemble_records(self, evidence_units: list) -> list[dict[str, object]]:
        hero_titles = [unit.normalized_text for unit in evidence_units if unit.kind == "hero"]
        primary_ctas = [
            {
                "label": unit.normalized_text,
                "href": str(unit.metadata.get("href", "")),
                "locator": unit.locator,
            }
            for unit in evidence_units if unit.kind == "cta"
        ]
        nav_items = [
            {
                "label": unit.normalized_text,
                "href": str(unit.metadata.get("href", "")),
                "locator": unit.locator,
            }
            for unit in evidence_units if unit.kind == "nav_item"
        ]
        content_sections = [
            {
                "title": unit.normalized_text,
                "summary": str(unit.metadata.get("summary", "")),
                "locator": unit.locator,
            }
            for unit in evidence_units if unit.kind == "content_section"
        ]

        records: list[dict[str, object]] = []
        if hero_titles:
            records.append({"kind": "hero_titles", "items": hero_titles})
        if primary_ctas:
            records.append({"kind": "primary_ctas", "items": primary_ctas})
        if nav_items:
            records.append({"kind": "nav_items", "items": nav_items})
        if content_sections:
            records.append({"kind": "content_sections", "items": content_sections})
        return records

    def _build_summary(self, evidence_units: list) -> dict[str, int]:
        return {
            "hero_title_count": sum(1 for unit in evidence_units if unit.kind == "hero"),
            "primary_cta_count": sum(1 for unit in evidence_units if unit.kind == "cta"),
            "nav_item_count": sum(1 for unit in evidence_units if unit.kind == "nav_item"),
            "content_section_count": sum(1 for unit in evidence_units if unit.kind == "content_section"),
            "evidence_unit_count": len(evidence_units),
        }
