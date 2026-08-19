from scidoc_engines.math.normalization import normalize_latex, unicode_math_to_latex
from scidoc_validation.math import validate_latex


def test_conservative_latex_normalization() -> None:
    assert normalize_latex(r"\[  E \, = mc^2  \]") == "E = mc^2"
    assert unicode_math_to_latex("E = mc²") == "E = mc^2"


def test_multidisciplinary_unicode_math_normalization() -> None:
    latex = unicode_math_to_latex("∇×E = −∂B/∂t, x ∈ Ω, ∑ᵢ pᵢ = 1")
    assert r"\nabla" in latex
    assert r"\partial" in latex
    assert r"\in" in latex
    assert r"\Omega" in latex
    assert r"\sum" in latex


def test_latex_validation() -> None:
    assert validate_latex(r"\frac{x}{2}").valid
    assert not validate_latex(r"\frac{x{2}").valid
