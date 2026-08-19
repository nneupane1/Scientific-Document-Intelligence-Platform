from __future__ import annotations

import cv2
import numpy as np


def deskew(image: np.ndarray, angle_degrees: float) -> np.ndarray:
    if abs(angle_degrees) < 0.05:
        return image.copy()
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle_degrees, 1.0)
    return cv2.warpAffine(
        image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
