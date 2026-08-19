from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MathValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)


def _balanced(value: str, opening: str, closing: str) -> bool:
    level = 0
    for character in value:
        if character == opening:
            level += 1
        elif character == closing:
            level -= 1
            if level < 0:
                return False
    return level == 0


def validate_latex(value: str) -> MathValidationResult:
    warnings: list[str] = []
    if not value.strip():
        warnings.append("empty LaTeX")
    for opening, closing, name in (
        ("{", "}", "braces"),
        ("(", ")", "parentheses"),
        ("[", "]", "brackets"),
    ):
        if not _balanced(value, opening, closing):
            warnings.append(f"unbalanced {name}")
    if value.count("\\begin") != value.count("\\end"):
        warnings.append("unbalanced LaTeX environments")
    if "\\frac" in value and "{" not in value:
        warnings.append("fraction command appears malformed")
    return MathValidationResult(valid=not warnings, warnings=warnings)
