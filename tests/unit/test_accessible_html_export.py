from pathlib import Path

from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_exporters.html import _safe_mathml, export_html
from scidoc_schema.models import (
    DocumentInfo,
    ElementContent,
    ElementType,
    SdrDocument,
    SdrElement,
    SdrPage,
)


def _element(
    element_id: str,
    element_type: ElementType,
    reading_order: int,
    content: ElementContent,
    *,
    review_status: ConfidenceState = ConfidenceState.ACCEPTED,
    warnings: list[str] | None = None,
) -> SdrElement:
    return SdrElement(
        id=element_id,
        type=element_type,
        bbox=(10, 20 + reading_order * 20, 500, 38 + reading_order * 20),
        reading_order=reading_order,
        content=content,
        confidence=0.96,
        confidence_source="test",
        provenance=Provenance(method="test_extract", engine="test", source_page=1),
        review_status=review_status,
        warnings=warnings or [],
    )


def _document() -> SdrDocument:
    return SdrDocument(
        document=DocumentInfo(
            id="doc_accessible",
            filename="accessible-science.pdf",
            title="Accessible science",
            sha256="a" * 64,
            page_count=1,
        ),
        pages=[
            SdrPage(
                number=1,
                width=612,
                height=792,
                classification="hybrid",
                elements=[
                    _element(
                        "heading",
                        ElementType.HEADING,
                        0,
                        ElementContent(text="Recovered results"),
                    ),
                    _element(
                        "paragraph",
                        ElementType.PARAGRAPH,
                        1,
                        ElementContent(text="Measured <script>alert('x')</script> safely."),
                    ),
                    _element(
                        "equation",
                        ElementType.EQUATION,
                        2,
                        ElementContent(
                            unicode="E equals m c squared",
                            latex="E=mc^2",
                            mathml=(
                                "<math><mrow><mi>E</mi><mo>=</mo><mi>m</mi>"
                                "<msup><mi>c</mi><mn>2</mn></msup>"
                                "<script>alert('math')</script></mrow></math>"
                            ),
                        ),
                    ),
                    _element(
                        "table",
                        ElementType.TABLE,
                        3,
                        ElementContent(
                            label="Experiment results",
                            columns=["Sample", "Value"],
                            rows=[["A", 42], ["B", 84]],
                        ),
                    ),
                    _element(
                        "figure",
                        ElementType.CHART,
                        4,
                        ElementContent(alt_text="Line chart of pressure increasing over time."),
                    ),
                    _element(
                        "braille",
                        ElementType.BRAILLE,
                        5,
                        ElementContent(
                            text="⠠⠓⠑⠇⠇⠕",
                            unicode="⠠⠓⠑⠇⠇⠕",
                            alt_text="Uncontracted Braille transcription: Hello",
                        ),
                        review_status=ConfidenceState.NEEDS_REVIEW,
                        warnings=["Check contractions against the source."],
                    ),
                ],
            )
        ],
        config_hash="b" * 64,
    )


def test_html_export_is_semantic_screen_reader_document(tmp_path: Path) -> None:
    destination = export_html(_document(), tmp_path / "document.html")
    rendered = destination.read_text(encoding="utf-8")

    assert '<html lang="en">' in rendered
    assert '<a class="skip-link" href="#main-content">' in rendered
    assert '<main id="main-content">' in rendered
    assert 'aria-label="Source pages"' in rendered
    assert '<section class="page" id="source-page-1"' in rendered
    assert '<th scope="col">Sample</th>' in rendered
    assert "<caption>Experiment results</caption>" in rendered
    assert '<math xmlns="http://www.w3.org/1998/Math/MathML"' in rendered
    assert 'aria-label="E equals m c squared"' in rendered
    assert "Line chart of pressure increasing over time." in rendered
    assert "Uncontracted Braille transcription: Hello" in rendered
    assert "Review status: needs review." in rendered
    assert "Check contractions against the source." in rendered


def test_html_export_escapes_text_and_removes_unsafe_mathml(tmp_path: Path) -> None:
    rendered = export_html(_document(), tmp_path / "safe.html").read_text(encoding="utf-8")

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in rendered
    assert "alert('math')" not in rendered


def test_html_export_preserves_recovered_reading_order(tmp_path: Path) -> None:
    rendered = export_html(_document(), tmp_path / "ordered.html").read_text(encoding="utf-8")

    assert rendered.index("Recovered results") < rendered.index("Measured")
    assert rendered.index("Measured") < rendered.index("E equals m c squared")
    assert rendered.index("E equals m c squared") < rendered.index("Experiment results")


def test_mathml_is_given_deterministic_spoken_mathematics() -> None:
    rendered = _safe_mathml(
        "<math><mfrac><mi>x</mi><msup><mi>y</mi><mn>3</mn></msup></mfrac></math>",
        "fallback",
    )

    assert rendered is not None
    mathml, spoken = rendered
    assert spoken == "fraction x over y cubed end fraction"
    assert 'aria-label="fraction x over y cubed end fraction"' in mathml
