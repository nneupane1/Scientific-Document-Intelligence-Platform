from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest


@pytest.fixture
def tiny_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "scientific sample.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 90), "Scientific document intelligence", fontsize=16)
    page.insert_text((180, 220), "E = mc^2", fontsize=18)
    page.insert_text((72, 280), "A deterministic native paragraph.", fontsize=11)
    document.set_metadata({"title": "Synthetic scientific fixture"})
    document.save(path)
    document.close()
    return path
