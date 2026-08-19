# ruff: noqa: E501

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from scidoc_core.confidence import ConfidenceState
from scidoc_schema.models import ElementContent, ElementType, SdrDocument, SdrElement

from scidoc_exporters.speech import mathml_element_to_speech

_MATHML_NAMESPACE = "http://www.w3.org/1998/Math/MathML"
_MATHML_TAGS = {
    "annotation",
    "maction",
    "math",
    "menclose",
    "merror",
    "mfenced",
    "mfrac",
    "mi",
    "mlabeledtr",
    "mmultiscripts",
    "mn",
    "mo",
    "mover",
    "mpadded",
    "mphantom",
    "mprescripts",
    "mroot",
    "mrow",
    "ms",
    "mspace",
    "msqrt",
    "mstyle",
    "msub",
    "msubsup",
    "msup",
    "mtable",
    "mtd",
    "mtext",
    "mtr",
    "munder",
    "munderover",
    "none",
    "semantics",
}
_MATHML_ATTRIBUTES = {
    "accent",
    "accentunder",
    "columnalign",
    "columnspan",
    "columnspacing",
    "dir",
    "display",
    "displaystyle",
    "fence",
    "form",
    "largeop",
    "linethickness",
    "lspace",
    "mathbackground",
    "mathcolor",
    "mathsize",
    "mathvariant",
    "maxsize",
    "minsize",
    "movablelimits",
    "notation",
    "rowalign",
    "rowspan",
    "rowspacing",
    "rspace",
    "scriptlevel",
    "separator",
    "stretchy",
    "symmetric",
}
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


def _escape_text(value: str | None) -> str:
    return html.escape(value or "").replace("\n", "<br>")


def _plain_content(content: ElementContent) -> str:
    return next(
        (
            value.strip()
            for value in (
                content.alt_text,
                content.text,
                content.unicode,
                content.normalized_latex,
                content.latex,
                content.raw_latex,
                content.label,
            )
            if value and value.strip()
        ),
        "",
    )


def _safe_id(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return normalized or fallback


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _copy_safe_mathml(node: ET.Element) -> ET.Element | None:
    name = _local_name(node.tag)
    if name not in _MATHML_TAGS:
        return None
    cleaned = ET.Element(f"{{{_MATHML_NAMESPACE}}}{name}")
    for attribute, value in node.attrib.items():
        local_attribute = _local_name(attribute)
        if local_attribute in _MATHML_ATTRIBUTES:
            cleaned.set(local_attribute, value)
    cleaned.text = node.text
    for child in node:
        safe_child = _copy_safe_mathml(child)
        if safe_child is not None:
            safe_child.tail = child.tail
            cleaned.append(safe_child)
    return cleaned


def _safe_mathml(raw_mathml: str | None, accessible_label: str) -> tuple[str, str] | None:
    if not raw_mathml:
        return None
    try:
        root = ET.fromstring(raw_mathml)
    except ET.ParseError:
        return None
    if _local_name(root.tag) != "math":
        return None
    cleaned = _copy_safe_mathml(root)
    if cleaned is None:
        return None
    spoken_label = (
        mathml_element_to_speech(cleaned) or accessible_label or "Mathematical expression"
    )
    cleaned.set("display", "block")
    cleaned.set("aria-label", spoken_label)
    cleaned.set("tabindex", "0")
    ET.register_namespace("", _MATHML_NAMESPACE)
    return ET.tostring(cleaned, encoding="unicode", method="xml"), spoken_label


def _review_note(element: SdrElement, element_id: str) -> str:
    if element.review_status not in _REVIEW_STATES and not element.warnings:
        return ""
    messages = [
        f"Review status: {element.review_status.value.replace('_', ' ')}.",
        *element.warnings,
    ]
    return (
        f'<aside class="review-note" id="{element_id}-review" role="note">'
        + " ".join(_escape_text(message) for message in messages)
        + "</aside>"
    )


def _render_table(element: SdrElement, element_id: str) -> str:
    columns = element.content.columns or []
    rows = element.content.rows or []
    caption = element.content.label or element.content.alt_text or element.content.text
    if not rows:
        fallback = caption or "Table structure was detected, but no cells were recovered."
        return f'<p class="table-fallback" id="{element_id}">{_escape_text(fallback)}</p>'

    column_count = max(len(columns), max((len(row) for row in rows), default=0))
    normalized_columns = [
        columns[index] if index < len(columns) and columns[index] else f"Column {index + 1}"
        for index in range(column_count)
    ]
    head = "".join(f'<th scope="col">{_escape_text(label)}</th>' for label in normalized_columns)
    body_rows: list[str] = []
    for row in rows:
        cells = list(row) + [None] * (column_count - len(row))
        body_rows.append(
            "<tr>"
            + "".join(
                f"<td>{_escape_text('' if cell is None else str(cell))}</td>"
                for cell in cells[:column_count]
            )
            + "</tr>"
        )
    rendered_caption = (
        f"<caption>{_escape_text(caption)}</caption>"
        if caption
        else "<caption>Recovered table</caption>"
    )
    return (
        f'<div class="table-scroll" id="{element_id}" tabindex="0" '
        'aria-label="Scrollable recovered table">'
        f"<table>{rendered_caption}<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _render_equation(element: SdrElement, element_id: str) -> str:
    content = element.content
    label = next(
        (
            value.strip()
            for value in (
                content.alt_text,
                content.unicode,
                content.normalized_latex,
                content.latex,
                content.text,
            )
            if value and value.strip()
        ),
        "Mathematical expression",
    )
    mathml_result = _safe_mathml(content.mathml, label)
    expression = (
        content.normalized_latex or content.latex or content.unicode or content.text or label
    )
    kind = "Chemical equation" if element.type is ElementType.CHEMICAL_EQUATION else "Equation"
    if mathml_result:
        visual, label = mathml_result
    else:
        visual = (
            f'<div class="math-fallback" role="math" tabindex="0" '
            f'aria-label="{html.escape(label)}">'
            f'<code aria-hidden="true">{html.escape(expression)}</code></div>'
        )
    return (
        f'<figure class="equation" id="{element_id}">{visual}'
        f'<figcaption><span class="sr-only">{kind}: </span>{_escape_text(label)}</figcaption>'
        "</figure>"
    )


def _render_visual(element: SdrElement, element_id: str, page_number: int) -> str:
    type_name = element.type.value.replace("_", " ").capitalize()
    description = element.content.alt_text or element.content.text or element.content.label
    if not description:
        description = (
            f"{type_name} on source page {page_number}. No text alternative was recovered; "
            "review the original PDF."
        )
    return (
        f'<figure class="visual-region" id="{element_id}" aria-labelledby="{element_id}-caption">'
        f'<div class="visual-placeholder" aria-hidden="true">{html.escape(type_name)}</div>'
        f'<figcaption id="{element_id}-caption">{_escape_text(description)}</figcaption></figure>'
    )


def _render_braille(element: SdrElement, element_id: str) -> str:
    unicode_value = element.content.unicode or element.content.text or ""
    transcription = element.content.alt_text or "Braille content; no transcription was recovered."
    return (
        f'<section class="braille" id="{element_id}" aria-labelledby="{element_id}-label">'
        f'<h3 id="{element_id}-label">Braille</h3>'
        f'<p class="braille-cells" aria-hidden="true">{_escape_text(unicode_value)}</p>'
        f"<p>{_escape_text(transcription)}</p></section>"
    )


def _render_element(element: SdrElement, page_number: int, index: int) -> str:
    element_id = _safe_id(element.id, f"page-{page_number}-element-{index}")
    attributes = (
        f' class="document-element type-{element.type.value}" data-source-page="{page_number}" '
        f'data-review-status="{element.review_status.value}"'
    )
    if element.confidence is not None:
        attributes += f' data-confidence="{element.confidence:.6f}"'

    if element.type in {ElementType.EQUATION, ElementType.CHEMICAL_EQUATION}:
        content = _render_equation(element, element_id)
    elif element.type is ElementType.TABLE:
        content = _render_table(element, element_id)
    elif element.type in _VISUAL_TYPES:
        content = _render_visual(element, element_id, page_number)
    elif element.type is ElementType.BRAILLE:
        content = _render_braille(element, element_id)
    elif element.type is ElementType.CODE:
        content = (
            f'<pre id="{element_id}" tabindex="0"><code>'
            f"{html.escape(_plain_content(element.content))}</code></pre>"
        )
    elif element.type is ElementType.FOOTNOTE:
        content = (
            f'<aside class="footnote" id="{element_id}" role="note">'
            f'<span class="sr-only">Footnote: </span>'
            f"{_escape_text(_plain_content(element.content))}</aside>"
        )
    elif element.type is ElementType.PAGE_NUMBER:
        value = _plain_content(element.content)
        content = (
            f'<p class="source-page-number" id="{element_id}" '
            f'aria-label="Printed page number {html.escape(value)}">{_escape_text(value)}</p>'
        )
    else:
        tag = "h3" if element.type in {ElementType.TITLE, ElementType.HEADING} else "p"
        content = (
            f'<{tag} id="{element_id}">{_escape_text(_plain_content(element.content))}</{tag}>'
        )

    note = _review_note(element, element_id)
    provenance = element.provenance
    source_label = provenance.source_page or page_number
    return (
        f"<div{attributes}>{content}{note}"
        f'<span class="sr-only">Source page {source_label}. Extraction method: '
        f"{html.escape(provenance.method)}.</span></div>"
    )


def export_html(sdr: SdrDocument, destination: str | Path) -> Path:
    title = sdr.document.title or Path(sdr.document.filename).stem or sdr.document.filename
    page_navigation = "".join(
        f'<li><a href="#source-page-{page.number}">Page {page.number}</a></li>'
        for page in sdr.pages
    )
    pages: list[str] = []
    for page in sdr.pages:
        elements = "".join(
            _render_element(element, page.number, index)
            for index, element in enumerate(
                sorted(page.elements, key=lambda item: item.reading_order), start=1
            )
        )
        pages.append(
            f'<section class="page" id="source-page-{page.number}" '
            f'aria-labelledby="source-page-{page.number}-title">'
            f'<h2 id="source-page-{page.number}-title">Source page {page.number}</h2>'
            f"{elements}</section>"
        )

    styles = """
:root{color-scheme:light;--ink:#18231e;--muted:#56645d;--paper:#f5f3ec;--surface:#fffefa;--line:#d7ddd8;--accent:#176e50;--warn:#8a561a}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{background:var(--paper);color:var(--ink);font:18px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0}
a{color:#075f8f;text-decoration-thickness:.1em;text-underline-offset:.16em}a:focus-visible,button:focus-visible,[tabindex]:focus-visible{outline:3px solid #d77b2e;outline-offset:4px}
.skip-link{background:#fff;border:2px solid var(--ink);left:1rem;padding:.7rem 1rem;position:fixed;top:1rem;transform:translateY(-180%);z-index:10}.skip-link:focus{transform:none}
.document-header,.page,.document-footer,.page-navigation{background:var(--surface);border:1px solid var(--line);border-radius:1rem;margin:1.25rem auto;max-width:70rem;padding:clamp(1.25rem,3vw,2.5rem)}
.document-header{margin-top:2rem}.eyebrow{color:var(--accent);font-size:.78rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.document-header h1{font-family:Georgia,serif;font-size:clamp(2.1rem,5vw,4rem);line-height:1.05;margin:.35rem 0 1rem}.summary{color:var(--muted);max-width:54rem}
.metadata{display:grid;gap:.6rem 1.5rem;grid-template-columns:max-content 1fr;margin:1.5rem 0 0}.metadata dt{font-weight:700}.metadata dd{margin:0;overflow-wrap:anywhere}
.page-navigation details{max-width:54rem}.page-navigation summary{cursor:pointer;font-weight:750}.page-navigation ol{columns:4;margin-bottom:0}.page-navigation li{break-inside:avoid}
main{display:block}.page{scroll-margin-top:1rem}.page>h2{border-bottom:1px solid var(--line);font-family:Georgia,serif;font-size:1.45rem;margin:0 0 2rem;padding-bottom:.75rem}.document-element{margin:1.25rem 0}.document-element h3{font-family:Georgia,serif;font-size:1.65rem;line-height:1.25;margin:2rem 0 .7rem}.document-element p{white-space:normal}
.equation,.visual-region{border-left:4px solid var(--accent);margin:1.6rem 0;padding:1rem 1.25rem}.equation math{font-size:1.25em;max-width:100%;overflow:auto}.equation figcaption,.visual-region figcaption{color:var(--muted);font-size:.92rem;margin-top:.75rem}.math-fallback{overflow:auto;padding:.5rem;text-align:center}.math-fallback code{font-size:1.05rem;white-space:pre}
.visual-placeholder{align-items:center;background:#eaf1ed;border:1px dashed #9fb4a9;border-radius:.7rem;color:#355c49;display:flex;font-weight:750;justify-content:center;min-height:6rem}.braille{background:#f0f5f2;border-radius:.75rem;padding:1rem 1.25rem}.braille h3{font-size:1.15rem;margin:0}.braille-cells{font-family:"Apple Braille",sans-serif;font-size:1.6rem;letter-spacing:.1em}
.table-scroll{overflow-x:auto}.table-scroll:focus-visible{border-radius:.25rem}table{border-collapse:collapse;min-width:100%}caption{font-weight:750;padding:.6rem;text-align:left}th,td{border:1px solid #bcc8c1;padding:.65rem;text-align:left;vertical-align:top}th{background:#e9efeb}.table-fallback,.review-note{border-left:4px solid #c57a2c;padding:.8rem 1rem}.review-note{background:#fff5df;color:#624113;font-size:.92rem}.footnote{border-top:1px solid var(--line);font-size:.92rem;padding-top:.8rem}.source-page-number{color:var(--muted);font-size:.9rem;text-align:center}
pre{background:#202923;border-radius:.65rem;color:#f3f5f3;overflow:auto;padding:1rem}.document-footer{color:var(--muted);font-size:.92rem;margin-bottom:2rem}.sr-only{clip:rect(0,0,0,0);clip-path:inset(50%);height:1px;overflow:hidden;position:absolute;white-space:nowrap;width:1px}
@media(max-width:45rem){body{font-size:17px}.document-header,.page,.document-footer,.page-navigation{border-radius:0;border-left:0;border-right:0}.page-navigation ol{columns:2}.metadata{grid-template-columns:1fr}.metadata dt{margin-top:.5rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media(forced-colors:active){.equation,.visual-region,.review-note,.table-fallback{border-left-color:CanvasText}.visual-placeholder{border:1px solid CanvasText}}
@media print{body{background:white}.skip-link,.page-navigation{display:none}.document-header,.page,.document-footer{border:0;margin:0;max-width:none;padding:1rem 0}.page{break-after:page}}
"""
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — accessible document</title><style>{styles}</style></head>
<body><a class="skip-link" href="#main-content">Skip to document content</a>
<header class="document-header"><p class="eyebrow">Accessible document export</p>
<h1>{html.escape(title)}</h1><p class="summary">This semantic HTML follows the recovered reading order and is designed for browser screen readers. Any uncertain recognition remains explicitly marked for review.</p>
<dl class="metadata"><dt>Source file</dt><dd>{html.escape(sdr.document.filename)}</dd><dt>Source pages</dt><dd>{sdr.document.page_count}</dd><dt>Integrity</dt><dd>SHA-256 {html.escape(sdr.document.sha256)}</dd><dt>Representation</dt><dd>SDR {html.escape(sdr.schema_version)}</dd></dl></header>
<nav class="page-navigation" aria-label="Source pages"><details><summary>Navigate by source page</summary><ol>{page_navigation}</ol></details></nav>
<main id="main-content">{"".join(pages)}</main>
<footer class="document-footer"><p>Generated from the canonical Scientific Document Representation. The original PDF remains the visual source of truth; review notices identify content that may need human verification.</p></footer></body></html>"""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output
