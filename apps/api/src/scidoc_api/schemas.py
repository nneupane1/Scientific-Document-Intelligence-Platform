from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NarrationVoice = Literal[
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
    "af_heart",
    "af_bella",
    "af_nicole",
    "bf_emma",
    "samantha",
    "daniel",
    "karen",
    "moira",
    "rishi",
    "tessa",
]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobResponse(OrmModel):
    id: str
    document_id: str
    job_type: str
    status: str
    attempts: int
    progress: float
    pages_completed: int
    pages_total: int
    stage: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class DocumentSummary(OrmModel):
    id: str
    filename: str
    sha256: str
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    latest_job: JobResponse | None = None
    summary: dict[str, object] | None = None


class UploadResponse(BaseModel):
    document_id: str
    job_id: str
    duplicate: bool
    status: str


class PageResponse(OrmModel):
    id: str
    document_id: str
    page_number: int
    width: float
    height: float
    classification: str
    status: str
    inspection: dict[str, object]


class ElementResponse(OrmModel):
    id: str
    page_id: str
    element_type: str
    bbox: list[float]
    reading_order: int
    content: dict[str, object]
    confidence: float | None
    confidence_source: str
    provenance: dict[str, object]
    review_status: str
    warnings: list[str]


class PageDetail(PageResponse):
    elements: list[ElementResponse]


class ProcessResponse(BaseModel):
    document_id: str
    job_id: str
    status: str = "queued"


class ExportRequest(BaseModel):
    format: Literal["json", "html", "markdown", "latex", "searchable_pdf"]


class ExportResponse(BaseModel):
    format: str
    download_url: str


class NarrationVoiceOption(BaseModel):
    id: NarrationVoice
    label: str
    recommended: bool = False


class NarrationCapabilities(BaseModel):
    configured: bool
    provider: Literal["kokoro", "macos", "openai", "unavailable"]
    model: str
    default_voice: NarrationVoice
    voices: list[NarrationVoiceOption]
    ai_generated: bool
    remote_processing: bool
    privacy_notice: str


class NarrationRequest(BaseModel):
    page_number: int = Field(ge=1)
    element_id: str | None = Field(default=None, max_length=200)
    voice: NarrationVoice | None = None


class SearchResponse(BaseModel):
    query: str
    count: int
    hits: list[dict[str, object]]


class Pagination(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
