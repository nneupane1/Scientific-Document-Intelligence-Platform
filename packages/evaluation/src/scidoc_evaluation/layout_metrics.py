from __future__ import annotations

from scidoc_core.bbox import BBox


def layout_metrics(
    predicted: list[BBox], reference: list[BBox], threshold: float = 0.5
) -> dict[str, float]:
    matched_reference: set[int] = set()
    true_positive = 0
    for prediction in predicted:
        candidates = [
            (prediction.iou(target), index)
            for index, target in enumerate(reference)
            if index not in matched_reference
        ]
        if candidates:
            score, index = max(candidates)
            if score >= threshold:
                true_positive += 1
                matched_reference.add(index)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(reference) if reference else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }
