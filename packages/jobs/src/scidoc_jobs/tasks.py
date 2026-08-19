from __future__ import annotations

from pathlib import Path

import dramatiq
from scidoc_core.config import get_settings
from scidoc_database.models import Document
from scidoc_database.session import configure_database, create_schema, session_scope
from scidoc_exporters.service import export_sdr
from scidoc_pipeline.document_pipeline import DocumentPipeline
from scidoc_schema.models import SdrDocument
from scidoc_storage.paths import DocumentPaths

from scidoc_jobs.queue import broker  # noqa: F401


def _prepare() -> None:
    configure_database(get_settings().database_url)
    create_schema()


@dramatiq.actor(queue_name="cpu", max_retries=2, min_backoff=2000, max_backoff=30000)
def process_document_task(document_id: str, job_id: str) -> None:
    _prepare()
    with session_scope() as session:
        DocumentPipeline(session, get_settings()).process(document_id, job_id)


@dramatiq.actor(queue_name="cpu", max_retries=1)
def process_page_task(document_id: str, job_id: str, page_number: int) -> None:
    _prepare()
    with session_scope() as session:
        DocumentPipeline(session, get_settings()).process(
            document_id, job_id, force_pages={page_number}
        )


@dramatiq.actor(queue_name="export", max_retries=1)
def export_document_task(document_id: str, format: str) -> str:
    _prepare()
    settings = get_settings()
    with session_scope() as session:
        document = session.get(Document, document_id)
        if document is None or document.sdr_path is None:
            raise ValueError("processed document does not exist")
        sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
        extension = {"markdown": "md", "latex": "tex", "searchable_pdf": "pdf"}.get(format, format)
        destination = settings.storage_root / DocumentPaths(document_id).export(extension)
        return str(export_sdr(sdr, destination, format, source_pdf=document.source_path))  # type: ignore[arg-type]
