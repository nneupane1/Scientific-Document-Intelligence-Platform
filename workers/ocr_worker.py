"""OCR workers share the same actor module and select the `ocr` queue."""

from scidoc_jobs.queue import broker

__all__ = ["broker"]
