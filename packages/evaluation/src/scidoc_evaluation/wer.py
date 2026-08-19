from scidoc_evaluation.distance import edit_distance


def word_error_rate(reference: str, hypothesis: str) -> float:
    words = reference.split()
    if not words:
        return 0.0 if not hypothesis.split() else 1.0
    return edit_distance(words, hypothesis.split()) / len(words)
