from __future__ import annotations

from dataclasses import dataclass

from scidoc_engines.math.normalization import normalize_latex


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    agreement: float
    unanimous: bool
    candidates: list[str]


def compare_outputs(candidates: list[str], *, mathematical: bool = False) -> ConsensusResult:
    normalizer = normalize_latex if mathematical else lambda value: " ".join(value.split())
    normalized = [normalizer(candidate) for candidate in candidates]
    if not normalized:
        return ConsensusResult(agreement=0.0, unanimous=False, candidates=[])
    largest = max(normalized.count(candidate) for candidate in set(normalized))
    return ConsensusResult(
        agreement=largest / len(normalized),
        unanimous=largest == len(normalized),
        candidates=candidates,
    )
