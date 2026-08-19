from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from scidoc_core.bbox import BBox


class RegionType(StrEnum):
    TEXT = "text"
    EQUATION = "equation"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Region:
    id: str
    page_number: int
    bbox: BBox
    region_type: RegionType
    image_path: Path | None = None
    native_content: dict[str, Any] | None = None
    native_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
