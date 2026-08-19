from scidoc_core.confidence import ConfidenceState, decide_confidence


def test_confidence_decisions_preserve_unavailable_scores() -> None:
    assert decide_confidence(0.98, 0.97) is ConfidenceState.ACCEPTED
    assert decide_confidence(0.7, 0.97) is ConfidenceState.UNCERTAIN
    assert decide_confidence(None, 0.97) is ConfidenceState.NEEDS_REVIEW
