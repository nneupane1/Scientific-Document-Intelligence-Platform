from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

from scidoc_core.bbox import BBox


class HasBox(Protocol):
    bbox: BBox


T = TypeVar("T", bound=HasBox)


def sort_reading_order[T: HasBox](regions: Sequence[T], page_width: float) -> list[T]:
    """Sort common one/two-column pages with a deterministic spatial policy."""

    if not regions:
        return []
    midpoint = page_width / 2

    def column(region: T) -> int:
        bbox = region.bbox
        x0, x1 = float(bbox.x0), float(bbox.x1)
        if x0 < midpoint * 0.8 and x1 > midpoint * 1.2:
            return -1
        return 0 if (x0 + x1) / 2 < midpoint else 1

    spanning = [region for region in regions if column(region) == -1]
    columns = [region for region in regions if column(region) != -1]
    spanning.sort(key=lambda item: (float(item.bbox.y0), float(item.bbox.x0)))
    columns.sort(
        key=lambda item: (
            column(item),
            float(item.bbox.y0),
            float(item.bbox.x0),
        )
    )
    header_cutoff = min((float(item.bbox.y0) for item in columns), default=float("inf"))
    headers = [item for item in spanning if float(item.bbox.y0) <= header_cutoff]
    tail = [item for item in spanning if item not in headers]
    return headers + columns + tail
