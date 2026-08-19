from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueueAssignment:
    task_type: str
    queue: str


ASSIGNMENTS = {
    "document_inspection": QueueAssignment("document_inspection", "cpu"),
    "page_processing": QueueAssignment("page_processing", "cpu"),
    "ocr": QueueAssignment("ocr", "ocr"),
    "formula": QueueAssignment("formula", "gpu"),
    "export": QueueAssignment("export", "export"),
}
