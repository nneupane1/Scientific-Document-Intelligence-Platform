from enum import StrEnum


class Capability(StrEnum):
    NATIVE_TEXT = "native_text"
    OCR_TEXT = "ocr_text"
    FORMULA = "formula"
    TABLE = "table"
    CHEMISTRY = "chemistry"
    DIAGRAM = "diagram"
    VLM = "vlm"
