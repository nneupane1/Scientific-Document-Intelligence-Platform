from __future__ import annotations

from scidoc_core.config import Settings
from scidoc_database.session import session_scope
from scidoc_pipeline.document_pipeline import DocumentPipeline


def run_document(
    document_id: str, job_id: str, settings: Settings, force_pages: set[int] | None = None
) -> None:
    with session_scope() as session:
        DocumentPipeline(session, settings).process(document_id, job_id, force_pages=force_pages)


def dispatch_processing(
    document_id: str,
    job_id: str,
    settings: Settings,
    background: object | None = None,
    force_pages: set[int] | None = None,
) -> None:
    if settings.queue_mode == "dramatiq":
        if force_pages:
            from scidoc_jobs.tasks import process_page_task

            process_page_task.send(document_id, job_id, min(force_pages))
        else:
            from scidoc_jobs.dispatch import dispatch_document

            dispatch_document(document_id, job_id, settings)
    elif settings.queue_mode == "synchronous":
        run_document(document_id, job_id, settings, force_pages)
    else:
        if background is None or not hasattr(background, "add_task"):
            raise RuntimeError("background task dispatcher is unavailable")
        background.add_task(run_document, document_id, job_id, settings, force_pages)
