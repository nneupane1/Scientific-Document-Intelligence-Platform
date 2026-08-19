from scidoc_engines.math.normalization import normalize_latex


def normalize_math_query(value: str) -> str:
    return normalize_latex(value).replace(" ", "")
