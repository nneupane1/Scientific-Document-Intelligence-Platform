from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance


class ElementType(StrEnum):
    PARAGRAPH = "paragraph"
    TITLE = "title"
    HEADING = "heading"
    EQUATION = "equation"
    FIGURE = "figure"
    CAPTION = "caption"
    TABLE = "table"
    PAGE_NUMBER = "page_number"
    FOOTNOTE = "footnote"
    UNKNOWN = "unknown"
    CHEMICAL_EQUATION = "chemical_equation"
    MOLECULE = "molecule"
    CIRCUIT = "circuit"
    CHART = "chart"
    DIAGRAM = "diagram"
    BRAILLE = "braille"
    CODE = "code"
    REFERENCE = "reference"


class ElementContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    latex: str | None = None
    raw_latex: str | None = None
    normalized_latex: str | None = None
    mathml: str | None = None
    unicode: str | None = None
    label: str | None = None
    columns: list[str] | None = None
    rows: list[list[str | int | float | None]] | None = None
    alt_text: str | None = None
    words: list[dict[str, Any]] = Field(default_factory=list)
    spans: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class SdrElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: ElementType
    bbox: tuple[float, float, float, float]
    reading_order: int = Field(ge=0)
    content: ElementContent
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_source: str = "unavailable"
    provenance: Provenance
    review_status: ConfidenceState = ConfidenceState.UNCERTAIN
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def bbox_is_ordered(self) -> SdrElement:
        x0, y0, x1, y1 = self.bbox
        if min(self.bbox) < 0 or x1 < x0 or y1 < y0:
            raise ValueError("invalid bbox")
        return self


class PageMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rotation: int = 0
    text_blocks: int = 0
    text_coverage: float = Field(default=0, ge=0, le=1)
    embedded_images: int = 0
    image_coverage: float = Field(default=0, ge=0, le=1)
    vector_objects: int = 0
    fonts: list[str] = Field(default_factory=list)
    render_dpi: int | None = None
    quality: dict[str, float | int | str | bool | None] = Field(default_factory=dict)


class SdrPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    classification: Literal["native", "raster", "hybrid", "vector_heavy", "unknown"]
    elements: list[SdrElement] = Field(default_factory=list)
    metrics: PageMetrics = Field(default_factory=PageMetrics)


class DocumentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: int = Field(ge=1)
    title: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessingStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pages_processed: int = 0
    regions_processed: int = 0
    native_elements: int = 0
    ocr_elements: int = 0
    formula_elements: int = 0
    escalations: int = 0
    high_dpi_retries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    failed_regions: int = 0
    human_review_elements: int = 0
    elapsed_seconds: float = 0


class SdrDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    document: DocumentInfo
    pages: list[SdrPage]
    processing: ProcessingStats = Field(default_factory=ProcessingStats)
    pipeline_version: str = "0.1.0"
    config_hash: str
    model_versions: dict[str, str] = Field(default_factory=dict)
