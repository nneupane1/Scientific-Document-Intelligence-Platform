from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_REPEATED_GARBAGE = re.compile(r"([^\w\s])\1{5,}")


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)


def validate_text(value: str) -> ValidationResult:
    warnings: list[str] = []
    if not value.strip():
        warnings.append("empty text")
    if "\ufffd" in value:
        warnings.append("Unicode replacement characters detected")
    controls = sum(unicodedata.category(char) == "Cc" and char not in "\n\t\r" for char in value)
    if controls:
        warnings.append("unexpected control characters detected")
    if _REPEATED_GARBAGE.search(value):
        warnings.append("repeated punctuation suggests OCR garbage")
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) > 2 and len(set(lines)) / len(lines) < 0.6:
        warnings.append("duplicate lines detected")
    alphanumeric = sum(char.isalnum() for char in value)
    if value and alphanumeric / len(value) < 0.2:
        warnings.append("suspiciously low alphanumeric ratio")
    return ValidationResult(valid=not warnings, warnings=warnings)
