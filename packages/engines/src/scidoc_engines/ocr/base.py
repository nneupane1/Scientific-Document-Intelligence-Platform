from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OcrWord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    bbox: tuple[float, float, float, float]
    confidence: float | None = Field(default=None, ge=0, le=1)
