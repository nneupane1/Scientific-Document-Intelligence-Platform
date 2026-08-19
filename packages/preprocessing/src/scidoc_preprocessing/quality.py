from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict


class ImageQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int
    height: int
    contrast: float
    blur_variance: float
    skew_degrees: float
    noise_estimate: float
    mean_gray: float


def _estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, max(80, gray.shape[1] // 4))
    if lines is None:
        return 0.0
    angles = [float(theta * 180 / np.pi - 90) for _, theta in lines[:25, 0]]
    plausible = [angle for angle in angles if abs(angle) <= 15]
    return float(np.median(plausible)) if plausible else 0.0


def analyze_quality(image: str | Path | np.ndarray) -> ImageQuality:
    if isinstance(image, (str, Path)):
        source = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
        if source is None:
            raise ValueError(f"unable to read image: {image}")
    else:
        source = image
        if source.ndim == 3:
            source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(source, (3, 3), 0)
    noise = np.mean(np.abs(source.astype(np.float32) - blurred.astype(np.float32)))
    return ImageQuality(
        width=int(source.shape[1]),
        height=int(source.shape[0]),
        contrast=float(source.std() / 127.5),
        blur_variance=float(cv2.Laplacian(source, cv2.CV_64F).var()),
        skew_degrees=_estimate_skew(source),
        noise_estimate=float(noise),
        mean_gray=float(source.mean()),
    )
