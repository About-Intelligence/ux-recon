"""Typed models for structured extraction outputs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ExtractionKind = Literal["list_table", "detail_fields", "form_schema", "content_blocks", "unknown"]
ExtractionStatus = Literal["success", "empty", "failed", "skipped"]


class EvidencePaths(BaseModel):
    screenshot: str = ""
    html: str = ""


class EvidenceUnit(BaseModel):
    id: str = ""
    kind: str = "unknown"
    role: str = ""
    raw_text: str = ""
    normalized_text: str = ""
    url: str = ""
    page_type: str = "unknown"
    locator: str = ""
    dom_path: str = ""
    bbox: list[float] = Field(default_factory=list)
    html_fragment: str = ""
    screenshot_ref: str = ""
    confidence: float = 0.0
    source: str = "dom_rule"
    observed_at_step: int | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    state_id: str
    target_id: str
    url: str = ""
    page_type: str = "unknown"
    capture_label: str = ""
    capture_context: str = ""
    strategy: ExtractionKind = "unknown"
    status: ExtractionStatus = "empty"
    confidence: float = 0.0
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)
    records: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    evidence_paths: EvidencePaths = Field(default_factory=EvidencePaths)
    error: str = ""
