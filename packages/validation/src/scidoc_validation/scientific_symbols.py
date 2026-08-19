from __future__ import annotations

AMBIGUITIES: dict[str, tuple[str, ...]] = {
    "-": ("−", "–", "—"),
    "1": ("l", "I"),
    "0": ("O", "o"),
    "a": ("α",),
    "u": ("μ",),
    "x": ("×",),
    ".": ("·",),
    "->": ("→", "⇒"),
}


def diagnose_ambiguous_symbols(value: str) -> list[str]:
    warnings: list[str] = []
    if " u" in value and any(char.isdigit() for char in value):
        warnings.append("Latin u may represent micro sign μ; source review advised")
    if "--" in value:
        warnings.append("consecutive hyphens may represent a scientific minus or dash")
    return warnings
