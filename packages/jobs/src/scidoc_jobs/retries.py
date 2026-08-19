from enum import StrEnum


class FailureKind(StrEnum):
    TRANSIENT_QUEUE = "transient_queue"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CORRUPT_PDF = "corrupt_pdf"
    INVALID_REGION = "invalid_region"
    MODEL_UNAVAILABLE = "model_unavailable"
    DETERMINISTIC = "deterministic"


def is_retryable(kind: FailureKind) -> bool:
    return kind in {FailureKind.TRANSIENT_QUEUE, FailureKind.RESOURCE_EXHAUSTION}
