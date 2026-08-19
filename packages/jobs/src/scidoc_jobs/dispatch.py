from __future__ import annotations

from scidoc_core.config import Settings


def dispatch_document(document_id: str, job_id: str, settings: Settings) -> None:
    if settings.queue_mode != "dramatiq":
        raise ValueError("dispatch_document is only for Dramatiq mode")
    from scidoc_jobs.tasks import process_document_task

    process_document_task.send(document_id, job_id)
