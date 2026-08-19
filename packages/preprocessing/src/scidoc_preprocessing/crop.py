import numpy as np
from scidoc_core.bbox import BBox


def crop(image: np.ndarray, bbox: BBox) -> np.ndarray:
    height, width = image.shape[:2]
    x0, y0 = max(0, round(bbox.x0)), max(0, round(bbox.y0))
    x1, y1 = min(width, round(bbox.x1)), min(height, round(bbox.y1))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("crop is empty")
    return image[y0:y1, x0:x1].copy()
