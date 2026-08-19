from __future__ import annotations

from pathlib import Path
from typing import Literal

from scidoc_schema.models import SdrDocument

from scidoc_exporters.html import export_html
from scidoc_exporters.json_exporter import export_json
from scidoc_exporters.latex import export_latex
from scidoc_exporters.markdown import export_markdown
from scidoc_exporters.searchable_pdf import export_searchable_pdf

ExportFormat = Literal["json", "html", "markdown", "latex", "searchable_pdf"]


def export_sdr(
    sdr: SdrDocument,
    destination: str | Path,
    format: ExportFormat,
    *,
    source_pdf: str | Path | None = None,
) -> Path:
    if format == "json":
        return export_json(sdr, destination)
    if format == "html":
        return export_html(sdr, destination)
    if format == "markdown":
        return export_markdown(sdr, destination)
    if format == "latex":
        return export_latex(sdr, destination)
    if format == "searchable_pdf" and source_pdf:
        return export_searchable_pdf(sdr, source_pdf, destination)
    raise ValueError(
        "searchable_pdf requires source_pdf; otherwise choose json, html, markdown, or latex"
    )
