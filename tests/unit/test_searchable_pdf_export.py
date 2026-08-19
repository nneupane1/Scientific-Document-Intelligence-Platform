from pathlib import Path

import pymupdf as fitz
from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_exporters.searchable_pdf import _selectable_text, export_searchable_pdf
from scidoc_schema.models import (
    DocumentInfo,
    ElementContent,
    ElementType,
    SdrDocument,
    SdrElement,
    SdrPage,
)


def _element(
    element_type: ElementType,
    content: ElementContent,
    *,
    element_id: str = "element-1",
) -> SdrElement:
    return SdrElement(
        id=element_id,
        type=element_type,
        bbox=(20, 20, 180, 70),
        reading_order=0,
        content=content,
        confidence=0.95,
        confidence_source="test",
        provenance=Provenance(method="ocr", engine="test", source_page=1),
        review_status=ConfidenceState.ACCEPTED,
    )


def _sdr(element: SdrElement) -> SdrDocument:
    return SdrDocument(
        document=DocumentInfo(
            id="doc_selectable",
            filename="pixel-scan.pdf",
            sha256="a" * 64,
            page_count=1,
        ),
        pages=[
            SdrPage(
                number=1,
                width=200,
                height=200,
                classification="raster",
                elements=[element],
            )
        ],
        config_hash="b" * 64,
    )


def test_searchable_pdf_keeps_visuals_and_adds_selectable_text(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with fitz.open() as document:
        page = document.new_page(width=200, height=200)
        page.draw_rect(fitz.Rect(5, 5, 195, 195), color=(0.1, 0.4, 0.7), width=3)
        page.draw_circle((100, 120), 35, color=(0.8, 0.3, 0.1), fill=(0.95, 0.85, 0.7))
        document.save(source)

    destination = export_searchable_pdf(
        _sdr(_element(ElementType.PARAGRAPH, ElementContent(text="Selectable OCR text"))),
        source,
        tmp_path / "selectable.pdf",
    )

    with fitz.open(source) as original, fitz.open(destination) as selectable:
        assert "Selectable OCR text" in selectable[0].get_text()
        original_pixels = original[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).samples
        selectable_pixels = selectable[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).samples
        assert selectable_pixels == original_pixels


def test_selectable_text_includes_equations_and_structured_tables() -> None:
    equation = _element(
        ElementType.EQUATION,
        ElementContent(unicode="x squared plus y squared equals z squared"),
    )
    table = _element(
        ElementType.TABLE,
        ElementContent(columns=["Name", "Value"], rows=[["alpha", 42], ["beta", None]]),
    )

    assert _selectable_text(equation) == "x squared plus y squared equals z squared"
    assert _selectable_text(table) == "Name\tValue\nalpha\t42\nbeta\t"
