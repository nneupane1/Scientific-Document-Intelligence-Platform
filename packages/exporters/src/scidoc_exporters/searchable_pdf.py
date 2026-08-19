from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from scidoc_schema.models import ElementType, SdrDocument, SdrElement

_OCR_FONT_NAME = "ocr-unicode"
_OCR_FONT_BUFFER: bytes | None = None


def _ocr_font_buffer() -> bytes:
    global _OCR_FONT_BUFFER
    if _OCR_FONT_BUFFER is None:
        _OCR_FONT_BUFFER = fitz.Font(fontname="cjk").buffer
    return _OCR_FONT_BUFFER


def _selectable_text(element: SdrElement) -> str:
    content = element.content
    if element.type is ElementType.TABLE and content.rows:
        rows: list[list[str]] = []
        if content.columns:
            rows.append(content.columns)
        rows.extend(["" if value is None else str(value) for value in row] for row in content.rows)
        return "\n".join("\t".join(row) for row in rows)
    return next(
        (
            value.strip()
            for value in (
                content.text,
                content.unicode,
                content.normalized_latex,
                content.latex,
                content.alt_text,
            )
            if value and value.strip()
        ),
        "",
    )


def _insert_invisible_text(page: fitz.Page, rect: fitz.Rect, text: str) -> None:
    line_count = max(text.count("\n") + 1, 1)
    initial_size = max(4.0, min(14.0, rect.height / line_count * 0.7))
    font_sizes = (initial_size, initial_size * 0.8, initial_size * 0.6, 3.0)
    for font_size in font_sizes:
        shape = page.new_shape()
        remaining = shape.insert_textbox(
            rect,
            text,
            fontname=_OCR_FONT_NAME,
            fontsize=font_size,
            render_mode=3,
        )
        if remaining >= 0:
            shape.commit(overlay=True)
            return

    page.insert_text(
        (rect.x0, min(rect.y1, rect.y0 + 3.0)),
        text,
        fontname=_OCR_FONT_NAME,
        fontsize=3.0,
        render_mode=3,
        overlay=True,
    )


def export_searchable_pdf(
    sdr: SdrDocument, source_pdf: str | Path, destination: str | Path
) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source_pdf) as document:
        for sdr_page in sdr.pages:
            page = document[sdr_page.number - 1]
            overlays = [
                (fitz.Rect(*element.bbox), _selectable_text(element))
                for element in sorted(sdr_page.elements, key=lambda item: item.reading_order)
                if element.provenance.method != "native_pdf" and _selectable_text(element)
            ]
            if overlays:
                page.insert_font(
                    fontname=_OCR_FONT_NAME,
                    fontbuffer=_ocr_font_buffer(),
                )
                for rect, text in overlays:
                    _insert_invisible_text(page, rect, text)
        metadata = document.metadata
        metadata["title"] = sdr.document.title or Path(sdr.document.filename).stem
        metadata["subject"] = "Original visual PDF with a selectable OCR text layer"
        document.set_metadata(metadata)
        document.subset_fonts()
        document.save(output, garbage=4, deflate=True)
    return output
