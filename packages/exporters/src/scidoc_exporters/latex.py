from __future__ import annotations

from pathlib import Path

from scidoc_schema.models import ElementType, SdrDocument


def _escape(value: str) -> str:
    for source, target in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
    ):
        value = value.replace(source, target)
    return value


def export_latex(sdr: SdrDocument, destination: str | Path) -> Path:
    lines = [
        r"\documentclass{article}",
        r"\usepackage{amsmath,amssymb}",
        r"\begin{document}",
        rf"\section*{{{_escape(sdr.document.filename)}}}",
    ]
    for page in sdr.pages:
        lines.append(rf"% Source page {page.number}")
        for element in sorted(page.elements, key=lambda item: item.reading_order):
            if element.type is ElementType.EQUATION and element.content.latex:
                lines.extend([r"\[", element.content.latex, r"\]"])
            elif element.content.text:
                lines.append(_escape(element.content.text) + "\n")
    lines.append(r"\end{document}")
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
