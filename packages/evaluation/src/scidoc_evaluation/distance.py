from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def edit_distance[T](reference: Sequence[T], hypothesis: Sequence[T]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_item in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hypothesis_index] + 1,
                    previous[hypothesis_index - 1] + (reference_item != hypothesis_item),
                )
            )
        previous = current
    return previous[-1]
