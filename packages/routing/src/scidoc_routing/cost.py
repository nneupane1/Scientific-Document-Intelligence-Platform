from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComputeCost:
    relative: float
    estimated_seconds: float | None = None
    device: str = "cpu"
