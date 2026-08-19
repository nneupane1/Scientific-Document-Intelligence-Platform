import cv2
import numpy as np


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 15
    )


def adjust_contrast(image: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8)).apply(gray)
