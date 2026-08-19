from scidoc_core.confidence import ConfidenceState


def accepted(score: float | None, threshold: float) -> ConfidenceState:
    if score is None:
        return ConfidenceState.NEEDS_REVIEW
    return ConfidenceState.ACCEPTED if score >= threshold else ConfidenceState.UNCERTAIN
