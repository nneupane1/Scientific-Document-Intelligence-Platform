from __future__ import annotations

from scidoc_core.confidence import ConfidenceState
from scidoc_schema.models import ElementContent, ElementType, SdrDocument, SdrElement, SdrPage

from scidoc_exporters.speech import equation_to_speech

_VISUAL_TYPES = {
    ElementType.CHART,
    ElementType.CIRCUIT,
    ElementType.DIAGRAM,
    ElementType.FIGURE,
    ElementType.MOLECULE,
}
_REVIEW_STATES = {
    ConfidenceState.ENGINE_UNAVAILABLE,
    ConfidenceState.NEEDS_REVIEW,
    ConfidenceState.REJECTED,
    ConfidenceState.UNCERTAIN,
}


class NarrationTargetError(ValueError):
    """Raised when the requested page or element does not exist in an SDR."""


def _first_text(content: ElementContent) -> str:
    return next(
        (
            " ".join(value.split())
            for value in (
                content.text,
                content.alt_text,
                content.unicode,
                content.label,
                content.normalized_latex,
                content.latex,
            )
            if value and value.strip()
        ),
        "",
    )


def _table_speech(element: SdrElement) -> str:
    content = element.content
    parts = ["Table."]
    caption = content.label or content.alt_text or content.text
    if caption:
        parts.append(" ".join(caption.split()))
    if content.columns:
        parts.append("Columns: " + ", ".join(str(column) for column in content.columns) + ".")
    for index, row in enumerate(content.rows or [], start=1):
        cells = ["blank" if cell is None else str(cell) for cell in row]
        parts.append(f"Row {index}: " + "; ".join(cells) + ".")
    if not content.rows:
        parts.append("No table cells were recovered; review the source page.")
    return " ".join(parts)


def element_to_narration(element: SdrElement) -> str:
    """Build an evidence-preserving spoken description for one SDR element."""

    if element.type in {ElementType.EQUATION, ElementType.CHEMICAL_EQUATION}:
        label = "Chemical equation" if element.type is ElementType.CHEMICAL_EQUATION else "Equation"
        narration = f"{label}. {equation_to_speech(element.content)}. End {label.lower()}."
    elif element.type is ElementType.TABLE:
        narration = _table_speech(element)
    elif element.type in _VISUAL_TYPES:
        kind = element.type.value.replace("_", " ").capitalize()
        description = element.content.alt_text or element.content.text or element.content.label
        narration = (
            f"{kind}. {' '.join(description.split())}"
            if description
            else f"{kind}. No accessible description was recovered; review the source page."
        )
    elif element.type is ElementType.BRAILLE:
        transcription = element.content.alt_text or element.content.text
        narration = (
            f"Braille. {' '.join(transcription.split())}"
            if transcription
            else "Braille. No transcription was recovered; review the source page."
        )
    else:
        text = _first_text(element.content)
        if not text:
            return ""
        prefix = {
            ElementType.TITLE: "Title.",
            ElementType.HEADING: "Heading.",
            ElementType.CAPTION: "Caption.",
            ElementType.CODE: "Code block.",
            ElementType.FOOTNOTE: "Footnote.",
            ElementType.REFERENCE: "Reference.",
        }.get(element.type, "")
        narration = f"{prefix} {text}".strip()

    if element.review_status in _REVIEW_STATES:
        narration += " Recognition is marked for review."
    return narration


def _page_by_number(sdr: SdrDocument, page_number: int) -> SdrPage:
    page = next((candidate for candidate in sdr.pages if candidate.number == page_number), None)
    if page is None:
        raise NarrationTargetError(f"page {page_number} was not found")
    return page


def build_narration_script(
    sdr: SdrDocument, *, page_number: int, element_id: str | None = None
) -> str:
    """Build exact narration for one page or selected element in source reading order."""

    page = _page_by_number(sdr, page_number)
    elements = sorted(page.elements, key=lambda element: element.reading_order)
    if element_id:
        element = next((candidate for candidate in elements if candidate.id == element_id), None)
        if element is None:
            raise NarrationTargetError("the selected element was not found on this page")
        script = element_to_narration(element)
        if not script:
            raise NarrationTargetError("the selected element has no recoverable narration")
        return script

    parts = [f"Page {page.number}."]
    parts.extend(filter(None, (element_to_narration(element) for element in elements)))
    if len(parts) == 1:
        parts.append("No readable content was recovered on this page.")
    return "\n\n".join(parts)
