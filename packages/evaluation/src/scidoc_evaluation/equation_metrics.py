from __future__ import annotations

from difflib import SequenceMatcher

from scidoc_engines.math.normalization import normalize_latex


def equation_metrics(reference: str, hypothesis: str) -> dict[str, float | bool]:
    normalized_reference = normalize_latex(reference)
    normalized_hypothesis = normalize_latex(hypothesis)
    reference_tokens = normalized_reference.replace("{", " { ").replace("}", " } ").split()
    hypothesis_tokens = normalized_hypothesis.replace("{", " { ").replace("}", " } ").split()
    return {
        "exact_match": reference == hypothesis,
        "normalized_match": normalized_reference == normalized_hypothesis,
        "token_similarity": SequenceMatcher(None, reference_tokens, hypothesis_tokens).ratio(),
    }
