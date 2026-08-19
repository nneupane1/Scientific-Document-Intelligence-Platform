from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolutionEscalation:
    current_dpi: int
    next_dpi: int | None
    reason: str


def next_resolution(
    current: int, escalation: int = 450, maximum: int = 600
) -> ResolutionEscalation:
    if current < escalation:
        return ResolutionEscalation(
            current, escalation, "first visual recognition was insufficient"
        )
    if current < maximum:
        return ResolutionEscalation(current, maximum, "escalated recognition remained insufficient")
    return ResolutionEscalation(current, None, "maximum configured resolution reached")
