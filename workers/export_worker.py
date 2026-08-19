"""Start with: dramatiq scidoc_jobs.tasks --queues export."""

from scidoc_jobs.tasks import export_document_task

__all__ = ["export_document_task"]
