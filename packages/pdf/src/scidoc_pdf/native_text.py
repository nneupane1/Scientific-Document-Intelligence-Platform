from __future__ import annotations

import re

import pymupdf as fitz
from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_engines.math.latex_mathml import latex_to_mathml
from scidoc_engines.math.normalization import unicode_math_to_latex
from scidoc_schema.models import ElementContent, ElementType, SdrElement

from scidoc_pdf.braille import contains_braille, translate_uncontracted_braille

_EQUATION_LABEL = re.compile(r"\s*\(([A-Za-z]?\d+(?:\.\d+)*)\)\s*$")
_CHEMICAL_TOKEN = re.compile(r"\b[A-Z][a-z]?(?:\d+)?\b")
_MATH_SYMBOLS = set(
    "=+−-×÷±∓∂∇∆∫∮∑∏√∞≈≠≡≤≥≪≫→↔⇌∝∈∉⊂⊆⊃⊇∪∩∀∃∧∨¬⊕ℏΩαβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨ^_{}[]|"
)
_MATH_COMMAND = re.compile(
    r"\\(?:frac|sqrt|sum|prod|int|lim|begin|partial|nabla|mathbf|mathbb|operatorname)"
)


def _element_type(
    text: str, bbox: tuple[float, float, float, float], page: fitz.Page, size: float
) -> ElementType:
    stripped = text.strip()
    if contains_braille(stripped):
        return ElementType.BRAILLE
    if (
        any(arrow in stripped for arrow in ("->", "→", "⇌", "↔"))
        and len(_CHEMICAL_TOKEN.findall(stripped)) >= 2
    ):
        return ElementType.CHEMICAL_EQUATION
    math_ratio = sum(char in _MATH_SYMBOLS for char in stripped) / max(len(stripped), 1)
    relation_present = any(symbol in stripped for symbol in ("=", "≈", "≠", "≤", "≥", "∝"))
    calculus_present = any(symbol in stripped for symbol in ("∫", "∮", "∑", "∏", "∂", "∇"))
    if (
        math_ratio >= 0.06
        or (relation_present and len(stripped) < 320)
        or (calculus_present and len(stripped) < 420)
        or bool(_MATH_COMMAND.search(stripped))
    ):
        return ElementType.EQUATION
    if bbox[1] < page.rect.height * 0.08 and len(stripped) < 120 and size >= 16:
        return ElementType.TITLE
    if size >= 14 and len(stripped) < 160:
        return ElementType.HEADING
    if bbox[1] > page.rect.height * 0.92 and stripped.isdigit():
        return ElementType.PAGE_NUMBER
    if stripped.lower().startswith(("figure ", "fig. ", "table ")):
        return ElementType.CAPTION
    if bbox[1] > page.rect.height * 0.85 and size <= 9:
        return ElementType.FOOTNOTE
    return ElementType.PARAGRAPH


def extract_native_elements(
    page: fitz.Page, *, pipeline_version: str = "0.1.0"
) -> list[SdrElement]:
    """Extract text blocks without OCR and preserve PDF geometry."""

    result: list[SdrElement] = []
    raw = page.get_text("dict", sort=True)
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines: list[str] = []
        sizes: list[float] = []
        spans: list[dict[str, object]] = []
        for line in block.get("lines", []):
            line_text = "".join(str(span.get("text", "")) for span in line.get("spans", []))
            if line_text.strip():
                lines.append(line_text.rstrip())
            sizes.extend(float(span.get("size", 0)) for span in line.get("spans", []))
            spans.extend(
                {
                    "text": str(span.get("text", "")),
                    "bbox": [float(value) for value in span.get("bbox", (0, 0, 0, 0))],
                    "font": str(span.get("font", "")),
                    "size": float(span.get("size", 0)),
                    "flags": int(span.get("flags", 0)),
                }
                for span in line.get("spans", [])
                if str(span.get("text", ""))
            )
        text = "\n".join(lines).strip()
        if not text:
            continue
        raw_bbox = block["bbox"]
        bbox = (
            float(raw_bbox[0]),
            float(raw_bbox[1]),
            float(raw_bbox[2]),
            float(raw_bbox[3]),
        )
        average_size = sum(sizes) / len(sizes) if sizes else 0
        element_type = _element_type(text, bbox, page, average_size)
        words = [
            {
                "text": word[4],
                "bbox": [float(word[0]), float(word[1]), float(word[2]), float(word[3])],
            }
            for word in page.get_text("words", clip=fitz.Rect(*bbox), sort=True)
        ]
        content = ElementContent(text=text, spans=spans, words=words)
        confidence_source = "deterministic_native_pdf"
        method = "native_pdf"
        review_status = ConfidenceState.ACCEPTED
        warnings: list[str] = []
        if element_type in {ElementType.EQUATION, ElementType.CHEMICAL_EQUATION}:
            label_match = _EQUATION_LABEL.search(text)
            expression = text[: label_match.start()].strip() if label_match else text
            latex = unicode_math_to_latex(expression)
            mathml, mathml_warning = latex_to_mathml(latex)
            content = ElementContent(
                text=text,
                raw_latex=latex,
                normalized_latex=latex,
                latex=latex,
                mathml=mathml,
                unicode=expression,
                label=label_match.group(1) if label_match else None,
                spans=spans,
                words=words,
            )
            if mathml_warning:
                warnings.append(mathml_warning)
        elif element_type is ElementType.BRAILLE:
            translation = translate_uncontracted_braille(text)
            content = ElementContent(
                text=text,
                unicode=text,
                alt_text=f"Uncontracted Braille transcription: {translation}",
                spans=spans,
                words=words,
            )
            confidence_source = "deterministic_unicode_braille"
            method = "native_pdf_braille"
            review_status = ConfidenceState.UNCERTAIN
            warnings.append(
                "Braille source cells are preserved; transcription is Grade 1 "
                "and does not expand contractions"
            )
        order = len(result)
        result.append(
            SdrElement(
                id=f"p{page.number + 1}-e{order + 1}",
                type=element_type,
                bbox=bbox,
                reading_order=order,
                content=content,
                confidence=1.0,
                confidence_source=confidence_source,
                provenance=Provenance(
                    method=method,
                    engine="pymupdf",
                    engine_version=fitz.VersionBind,
                    pipeline_version=pipeline_version,
                    source_page=page.number + 1,
                ),
                review_status=review_status,
                warnings=warnings,
            )
        )
    return result
