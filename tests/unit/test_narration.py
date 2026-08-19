from __future__ import annotations

import asyncio
import wave
from io import BytesIO

import pytest
from scidoc_api.neural_voice import (
    kokoro_available,
    pcm_to_wav,
    split_narration_script,
    synthesize_narration_wav,
)
from scidoc_core.confidence import ConfidenceState
from scidoc_core.config import Settings
from scidoc_core.provenance import Provenance
from scidoc_exporters.narration import NarrationTargetError, build_narration_script
from scidoc_exporters.speech import equation_to_speech
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
) -> SdrElement:
    return SdrElement(
        id=element_id,
        type=element_type,
        bbox=(10, 10 + reading_order * 20, 500, 25 + reading_order * 20),
        reading_order=reading_order,
        content=content,
        confidence=0.99,
        confidence_source="test",
        provenance=Provenance(method="test", engine="test", source_page=1),
        review_status=ConfidenceState.ACCEPTED,
    )


def _document() -> SdrDocument:
    return SdrDocument(
        document=DocumentInfo(
            id="doc_narration",
            filename="equations.pdf",
            sha256="c" * 64,
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
                        ElementContent(text="Energy and mass"),
                    ),
                    _element(
                        "equation",
                        ElementType.EQUATION,
                        1,
                        ElementContent(
                            latex=r"E=mc^2",
                            mathml=(
                                "<math><mrow><mi>E</mi><mo>=</mo><mi>m</mi>"
                                "<msup><mi>c</mi><mn>2</mn></msup></mrow></math>"
                            ),
                        ),
                    ),
                ],
            )
        ],
        config_hash="d" * 64,
    )


def test_equation_speech_uses_mathml_and_latex_fallback() -> None:
    mathml = ElementContent(
        mathml="<math><mfrac><mi>x</mi><msup><mi>y</mi><mn>3</mn></msup></mfrac></math>"
    )
    latex = ElementContent(latex=r"\frac{x}{y^2}")

    assert equation_to_speech(mathml) == "fraction x over y cubed end fraction"
    assert equation_to_speech(latex) == "fraction x over y squared end fraction"


def test_page_and_selected_equation_narration_preserve_reading_order() -> None:
    document = _document()

    page_script = build_narration_script(document, page_number=1)
    equation_script = build_narration_script(document, page_number=1, element_id="equation")

    assert page_script.index("Heading. Energy and mass") < page_script.index("Equation.")
    assert "E equals m c squared" in page_script
    assert equation_script == "Equation. E equals m c squared. End equation."


def test_narration_rejects_unknown_target() -> None:
    with pytest.raises(NarrationTargetError, match="selected element"):
        build_narration_script(_document(), page_number=1, element_id="missing")


def test_long_narration_chunks_and_combines_pcm_as_wav() -> None:
    script = " ".join(["A measured scientific sentence."] * 400)
    chunks = split_narration_script(script, limit=240)

    assert len(chunks) > 1
    assert all(len(chunk) <= 240 for chunk in chunks)

    audio = pcm_to_wav(b"\x00\x00" * 240)
    with wave.open(BytesIO(audio), "rb") as rendered:
        assert rendered.getnchannels() == 1
        assert rendered.getsampwidth() == 2
        assert rendered.getframerate() == 24_000
        assert rendered.getnframes() == 240


def test_installed_kokoro_model_speaks_recovered_equation() -> None:
    settings = Settings(narration_provider="kokoro")
    if not kokoro_available(settings):
        pytest.skip("local Kokoro model is not installed")

    audio = asyncio.run(
        synthesize_narration_wav(
            "Equation. E equals m c squared. End equation.",
            voice="af_heart",
            settings=settings,
        )
    )

    with wave.open(BytesIO(audio), "rb") as rendered:
        assert rendered.getnchannels() == 1
        assert rendered.getsampwidth() == 2
        assert rendered.getframerate() == 24_000
        assert rendered.getnframes() > 24_000
