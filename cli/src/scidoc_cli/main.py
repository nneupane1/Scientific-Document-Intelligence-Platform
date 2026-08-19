from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from scidoc_core.config import get_settings
from scidoc_database.models import Document
from scidoc_database.session import configure_database, create_schema, session_scope
from scidoc_exporters.service import export_sdr
from scidoc_pdf.inspector import inspect_document
from scidoc_pipeline.document_pipeline import DocumentPipeline
from scidoc_schema.models import SdrDocument
from scidoc_storage.local import LocalStorage
from scidoc_storage.paths import DocumentPaths

app = typer.Typer(
    help="Local-first scientific PDF inspection, processing, export, and benchmarking.",
    no_args_is_help=True,
)


def _database() -> None:
    settings = get_settings()
    configure_database(settings.database_url)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    create_schema()


@app.command()
def inspect(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Inspect a PDF without invoking OCR or models."""

    report = inspect_document(pdf, include_text=False)
    typer.echo(f"Document: {report.filename}")
    typer.echo(f"Pages: {report.page_count}\n")
    for key, label in (
        ("native", "Native"),
        ("hybrid", "Hybrid"),
        ("raster", "Raster"),
        ("vector_heavy", "Vector-heavy"),
        ("unknown", "Unknown"),
    ):
        typer.echo(f"{label + ' pages:':20} {report.classifications.get(key, 0)}")
    typer.echo(f"\n{'Embedded images:':20} {report.embedded_images}")
    typer.echo(f"{'Fonts:':20} {len(report.fonts)}")


@app.command()
def process(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Run the complete local pipeline and persist canonical SDR."""

    _database()
    settings = get_settings()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        ingest_result = pipeline.ingest(pdf)
        typer.echo(f"Document: {ingest_result.document_id}")
        typer.echo(f"Job: {ingest_result.job_id}")
        sdr = pipeline.process(ingest_result.document_id, ingest_result.job_id)
        typer.echo(f"Pages processed: {sdr.processing.pages_processed}")
        typer.echo(f"Native elements: {sdr.processing.native_elements}")
        typer.echo(f"OCR elements: {sdr.processing.ocr_elements}")
        typer.echo(f"Formula elements: {sdr.processing.formula_elements}")
        typer.echo(f"Needs review: {sdr.processing.human_review_elements}")
        typer.echo(f"SDR: {settings.storage_root / DocumentPaths(ingest_result.document_id).sdr}")


@app.command(name="export")
def export_command(
    document_id: Annotated[str, typer.Argument()],
    format: Annotated[
        str, typer.Option("--format", "-f", help="json, html, markdown, latex, or searchable_pdf")
    ] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Export a processed document from SDR."""

    if format not in {"json", "html", "markdown", "latex", "searchable_pdf"}:
        raise typer.BadParameter("unsupported export format")
    _database()
    settings = get_settings()
    with session_scope() as session:
        document = session.get(Document, document_id)
        if document is None or not document.sdr_path:
            raise typer.BadParameter("processed document not found")
        sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
        extension = {"markdown": "md", "latex": "tex", "searchable_pdf": "pdf"}.get(format, format)
        destination = output or LocalStorage(settings.storage_root).resolve(
            DocumentPaths(document_id).export(extension)
        )
        result = export_sdr(sdr, destination, format, source_pdf=document.source_path)  # type: ignore[arg-type]
        typer.echo(str(result))


@app.command()
def benchmark(
    dataset: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)],
) -> None:
    """Process every PDF in a directory and report real routing/performance statistics."""

    _database()
    settings = get_settings()
    rows: list[dict[str, object]] = []
    for pdf in sorted(dataset.rglob("*.pdf")):
        with session_scope() as session:
            pipeline = DocumentPipeline(session, settings)
            result = pipeline.ingest(pdf)
            sdr = pipeline.process(result.document_id, result.job_id)
            rows.append(
                {"file": str(pdf), "document_id": result.document_id, **sdr.processing.model_dump()}
            )
            typer.echo(f"processed {pdf.name}: {sdr.processing.pages_processed} page(s)")
    if not rows:
        raise typer.BadParameter("dataset contains no PDF files")
    report_dir = Path("benchmark/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "latest.json"
    report.write_text(json.dumps({"documents": rows}, indent=2), encoding="utf-8")
    typer.echo(f"Report: {report}")


if __name__ == "__main__":
    app()
