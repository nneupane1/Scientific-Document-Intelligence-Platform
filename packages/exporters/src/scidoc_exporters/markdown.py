from __future__ import annotations

from pathlib import Path

from scidoc_schema.models import ElementType, SdrDocument


def export_markdown(sdr: SdrDocument, destination: str | Path) -> Path:
    lines = [f"# {sdr.document.filename}", ""]
    for page in sdr.pages:
        lines.extend([f"<!-- page {page.number} -->", ""])
        for element in sorted(page.elements, key=lambda item: item.reading_order):
            if element.type is ElementType.EQUATION and element.content.latex:
                lines.extend(["$$", element.content.latex, "$$", ""])
            elif element.content.text:
                prefix = "## " if element.type in {ElementType.TITLE, ElementType.HEADING} else ""
                lines.extend([prefix + element.content.text, ""])
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
