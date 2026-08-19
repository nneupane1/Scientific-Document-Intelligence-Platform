from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from latex2mathml.converter import convert as latex_to_mathml
from scidoc_schema.models import ElementContent

_OPERATOR_SPEECH = {
    "!": "factorial",
    "(": "open parenthesis",
    ")": "close parenthesis",
    "+": "plus",
    ",": "comma",
    "-": "minus",
    "/": "divided by",
    "<": "less than",
    "=": "equals",
    ">": "greater than",
    "[": "open bracket",
    "]": "close bracket",
    "±": "plus or minus",
    "·": "times",
    "×": "times",
    "÷": "divided by",
    "−": "minus",
    "∂": "partial derivative",
    "∈": "is an element of",
    "∑": "sum",
    "√": "square root",
    "∞": "infinity",
    "∫": "integral",
    "≈": "approximately equals",
    "≠": "does not equal",
    "≤": "less than or equal to",
    "≥": "greater than or equal to",
    "→": "approaches",
    "↔": "if and only if",
    "⇌": "is in equilibrium with",
}
_GREEK_SPEECH = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "ε": "epsilon",
    "θ": "theta",
    "λ": "lambda",
    "μ": "mu",
    "π": "pi",
    "ρ": "rho",
    "σ": "sigma",
    "τ": "tau",
    "φ": "phi",
    "ψ": "psi",
    "ω": "omega",
    "Δ": "capital delta",
    "Σ": "capital sigma",
    "Ω": "capital omega",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _speech_join(*parts: str) -> str:
    return " ".join(" ".join(parts).split())


def _speak_token(value: str | None) -> str:
    token = " ".join((value or "").split())
    if not token:
        return ""
    if token in _OPERATOR_SPEECH:
        return _OPERATOR_SPEECH[token]
    if token in _GREEK_SPEECH:
        return _GREEK_SPEECH[token]
    return token


def mathml_element_to_speech(node: ET.Element) -> str:
    """Turn a parsed MathML tree into deterministic, screen-reader-friendly speech."""

    name = _local_name(node.tag)
    children = list(node)
    spoken_children = [mathml_element_to_speech(child) for child in children]

    if name == "annotation":
        return ""
    if name in {"mi", "mn", "mo", "ms", "mtext"}:
        return _speak_token(node.text)
    if name == "mfrac" and len(spoken_children) >= 2:
        return _speech_join(
            "fraction", spoken_children[0], "over", spoken_children[1], "end fraction"
        )
    if name == "msqrt":
        return _speech_join("square root of", *spoken_children, "end root")
    if name == "mroot" and len(spoken_children) >= 2:
        return _speech_join(spoken_children[1], "root of", spoken_children[0], "end root")
    if name == "msup" and len(spoken_children) >= 2:
        exponent = spoken_children[1]
        if exponent == "2":
            return _speech_join(spoken_children[0], "squared")
        if exponent == "3":
            return _speech_join(spoken_children[0], "cubed")
        return _speech_join(spoken_children[0], "to the power of", exponent)
    if name == "msub" and len(spoken_children) >= 2:
        return _speech_join(spoken_children[0], "subscript", spoken_children[1])
    if name == "msubsup" and len(spoken_children) >= 3:
        return _speech_join(
            spoken_children[0],
            "subscript",
            spoken_children[1],
            "to the power of",
            spoken_children[2],
        )
    if name == "munder" and len(spoken_children) >= 2:
        return _speech_join(spoken_children[0], "with lower limit", spoken_children[1])
    if name == "mover" and len(spoken_children) >= 2:
        return _speech_join(spoken_children[0], "with upper value", spoken_children[1])
    if name == "munderover" and len(spoken_children) >= 3:
        return _speech_join(
            spoken_children[0], "from", spoken_children[1], "to", spoken_children[2]
        )
    if name == "mfenced":
        return _speech_join("open parenthesis", *spoken_children, "close parenthesis")
    if name == "mtr":
        return _speech_join("row", *spoken_children)
    if name == "mtd":
        return _speech_join("cell", *spoken_children)
    if name == "mtable":
        return _speech_join("matrix", *spoken_children, "end matrix")
    if name == "semantics":
        return next((value for value in spoken_children if value), "")
    return _speech_join(_speak_token(node.text), *spoken_children)


def mathml_to_speech(raw_mathml: str | None) -> str:
    if not raw_mathml:
        return ""
    try:
        root = ET.fromstring(raw_mathml)
    except ET.ParseError:
        return ""
    if _local_name(root.tag) != "math":
        return ""
    return mathml_element_to_speech(root)


def _plain_expression_to_speech(value: str | None) -> str:
    if not value:
        return ""
    spoken = " ".join(value.split())
    for token, replacement in sorted(
        {**_OPERATOR_SPEECH, **_GREEK_SPEECH}.items(), key=lambda item: len(item[0]), reverse=True
    ):
        spoken = spoken.replace(token, f" {replacement} ")
    return re.sub(r"\s+", " ", spoken).strip()


def equation_to_speech(content: ElementContent) -> str:
    """Return an exact spoken form, preferring MathML and deriving it from LaTeX when needed."""

    spoken = mathml_to_speech(content.mathml)
    if spoken:
        return spoken

    for latex in (content.normalized_latex, content.latex, content.raw_latex):
        if not latex:
            continue
        try:
            spoken = mathml_to_speech(latex_to_mathml(latex))
        except Exception:  # latex2mathml exposes multiple parser exception types
            spoken = ""
        if spoken:
            return spoken

    for fallback in (content.unicode, content.alt_text, content.text, content.label):
        spoken = _plain_expression_to_speech(fallback)
        if spoken:
            return spoken
    return "Mathematical expression"
