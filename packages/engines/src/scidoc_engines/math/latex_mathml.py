from __future__ import annotations


def latex_to_mathml(value: str) -> tuple[str | None, str | None]:
    try:
        from latex2mathml.converter import convert

        return convert(value), None
    except Exception as exc:
        return None, f"MathML conversion failed: {exc}"


def latex_to_unicode(value: str) -> str:
    replacements = {
        r"\hbar": "ℏ",
        r"\partial": "∂",
        r"\nabla": "∇",
        r"\infty": "∞",
        r"\times": "×",
        r"\pm": "±",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\theta": "θ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\pi": "π",
        r"\psi": "ψ",
    }
    result = value
    for latex, character in replacements.items():
        result = result.replace(latex, character)
    return result.replace("{", "").replace("}", "")
