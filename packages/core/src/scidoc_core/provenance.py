from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    engine: str
    engine_version: str | None = None
    model: str | None = None
    model_version: str | None = None
    pipeline_version: str = "0.1.0"
    source_page: int | None = Field(default=None, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class Provenance(BaseModel):
    """Current recognition provenance plus append-only earlier attempts."""

    model_config = ConfigDict(extra="forbid")

    method: str
    engine: str
    engine_version: str | None = None
    model: str | None = None
    model_version: str | None = None
    pipeline_version: str = "0.1.0"
    source_page: int | None = Field(default=None, ge=1)
    cache_hit: bool = False
    cache_key: str | None = None
    history: list[ProvenanceEvent] = Field(default_factory=list)

    def append_attempt(self, event: ProvenanceEvent) -> None:
        self.history.append(event)
