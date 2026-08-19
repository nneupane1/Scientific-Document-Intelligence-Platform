"""Start with: dramatiq scidoc_jobs.tasks --queues cpu."""

from scidoc_jobs.tasks import process_document_task, process_page_task

__all__ = ["process_document_task", "process_page_task"]
