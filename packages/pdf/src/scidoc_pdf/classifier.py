from __future__ import annotations

from scidoc_core.page import PageClassification


def classify_page(
    *, text_coverage: float, image_coverage: float, text_blocks: int, vector_objects: int
) -> PageClassification:
    """Classify a page using cheap, documented geometry heuristics."""

    has_text = text_blocks > 0 and text_coverage >= 0.002
    image_dominant = image_coverage >= 0.72
    has_images = image_coverage >= 0.04
    vector_heavy = vector_objects >= 250 and text_coverage < 0.08

    if has_text and (has_images or image_coverage >= 0.18):
        return PageClassification.HYBRID
    if has_text:
        return PageClassification.NATIVE
    if image_dominant or (image_coverage >= 0.35 and text_blocks == 0):
        return PageClassification.RASTER
    if vector_heavy:
        return PageClassification.VECTOR_HEAVY
    return PageClassification.UNKNOWN


def has_reliable_native_text(*, text: str, text_coverage: float, min_characters: int = 8) -> bool:
    printable = sum(character.isprintable() and not character.isspace() for character in text)
    replacement_ratio = text.count("\ufffd") / max(len(text), 1)
    return printable >= min_characters and text_coverage >= 0.002 and replacement_ratio < 0.02
