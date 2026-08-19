from __future__ import annotations

from scidoc_layout.detector import LayoutRegion


def remove_near_duplicates(
    regions: list[LayoutRegion], iou_threshold: float = 0.9
) -> list[LayoutRegion]:
    kept: list[LayoutRegion] = []
    for region in sorted(regions, key=lambda item: item.bbox.area, reverse=True):
        if not any(region.bbox.iou(existing.bbox) >= iou_threshold for existing in kept):
            kept.append(region)
    return kept
