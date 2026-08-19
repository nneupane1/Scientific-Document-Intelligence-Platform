from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from scidoc_core.bbox import BBox


class PageRenderer:
    """Deterministic PyMuPDF page and region rendering."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _matrix(dpi: int) -> fitz.Matrix:
        if dpi < 72 or dpi > 1200:
            raise ValueError("dpi must be between 72 and 1200")
        scale = dpi / 72
        return fitz.Matrix(scale, scale)

    def render_page(self, page: fitz.Page, dpi: int = 300) -> Path:
        destination = self.output_dir / f"page_{page.number + 1:04d}_{dpi}dpi.png"
        if not destination.exists():
            pixmap = page.get_pixmap(matrix=self._matrix(dpi), alpha=False, colorspace=fitz.csRGB)
            pixmap.save(destination)
        return destination

    def render_region(self, page: fitz.Page, bbox: BBox, region_id: str, dpi: int = 300) -> Path:
        region_dir = self.output_dir.parent / "regions" / f"page_{page.number + 1:04d}"
        region_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(
            character for character in region_id if character.isalnum() or character in "-_"
        )
        destination = region_dir / f"region_{safe_id}_{dpi}dpi.png"
        if not destination.exists():
            clip = fitz.Rect(*bbox.as_list()) & page.rect
            pixmap = page.get_pixmap(
                matrix=self._matrix(dpi), clip=clip, alpha=False, colorspace=fitz.csRGB
            )
            pixmap.save(destination)
        return destination
