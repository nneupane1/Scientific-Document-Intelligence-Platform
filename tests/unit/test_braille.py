import pymupdf as fitz
from PIL import Image, ImageDraw
from scidoc_pdf.braille import (
    contains_braille,
    detect_braille_dot_geometry,
    translate_uncontracted_braille,
)
from scidoc_pdf.native_text import _element_type
from scidoc_schema.models import ElementType


def test_unicode_braille_is_detected_and_transcribed_without_losing_source_cells() -> None:
    source = "⠠⠓⠑⠇⠇⠕⠀⠼⠁⠃⠉"
    assert contains_braille(source)
    assert translate_uncontracted_braille(source) == "Hello 123"
    assert not contains_braille("Hello 123")


def test_braille_takes_precedence_over_generic_text_classification() -> None:
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    assert _element_type("⠠⠓⠑⠇⠇⠕", (40, 60, 180, 90), page, 12) is ElementType.BRAILLE
    document.close()


def test_scanned_braille_like_dots_are_preserved_as_geometry(tmp_path) -> None:
    image_path = tmp_path / "braille-dots.png"
    image = Image.new("RGB", (180, 130), "white")
    drawing = ImageDraw.Draw(image)
    for x in (35, 55, 105, 125):
        for y in (25, 60, 95):
            drawing.ellipse((x - 6, y - 6, x + 6, y + 6), fill="black")
    image.save(image_path)

    dots = detect_braille_dot_geometry(image_path)
    assert len(dots) == 12
    assert all("bbox" in dot and "center" in dot for dot in dots)
