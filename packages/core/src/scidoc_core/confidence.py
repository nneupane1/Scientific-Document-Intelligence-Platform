from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceState(StrEnum):
    ACCEPTED = "accepted"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    ENGINE_UNAVAILABLE = "engine_unavailable"


class Confidence(BaseModel):
    """Normalized score plus the raw, engine-specific evidence."""

    model_config = ConfigDict(extra="forbid")

    score: float | None = Field(default=None, ge=0, le=1)
    raw_score: float | None = None
    source: str = "unavailable"
    state: ConfidenceState = ConfidenceState.UNCERTAIN
    threshold: float | None = Field(default=None, ge=0, le=1)


def decide_confidence(score: float | None, threshold: float) -> ConfidenceState:
    if score is None:
        return ConfidenceState.NEEDS_REVIEW
    return ConfidenceState.ACCEPTED if score >= threshold else ConfidenceState.UNCERTAIN
