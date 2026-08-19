import cv2
import numpy as np


def rotate_right_angle(image: np.ndarray, degrees: int) -> np.ndarray:
    normalized = degrees % 360
    codes = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return image.copy() if normalized == 0 else cv2.rotate(image, codes[normalized])
