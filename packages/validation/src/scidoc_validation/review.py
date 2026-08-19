from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReviewItem:
    element_id: str
    reason: str
    source_crop_path: str | None = None
    candidates: list[dict[str, object]] = field(default_factory=list)
