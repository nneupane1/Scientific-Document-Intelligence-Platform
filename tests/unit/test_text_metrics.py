from scidoc_evaluation.cer import character_error_rate
from scidoc_evaluation.wer import word_error_rate


def test_error_rates() -> None:
    assert character_error_rate("abc", "axc") == 1 / 3
    assert word_error_rate("one two", "one three") == 0.5
