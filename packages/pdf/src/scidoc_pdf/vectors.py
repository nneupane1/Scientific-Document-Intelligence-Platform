from __future__ import annotations

import pymupdf as fitz


def vector_summary(page: fitz.Page) -> dict[str, int]:
    drawings = page.get_drawings()
    return {
        "objects": len(drawings),
        "lines": sum(len(item.get("items", [])) for item in drawings),
    }
