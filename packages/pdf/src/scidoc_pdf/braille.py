from __future__ import annotations

import math
from pathlib import Path
from statistics import median

import cv2

_LETTER_CELLS = {
    "⠁": "a",
    "⠃": "b",
    "⠉": "c",
    "⠙": "d",
    "⠑": "e",
    "⠋": "f",
    "⠛": "g",
    "⠓": "h",
    "⠊": "i",
    "⠚": "j",
    "⠅": "k",
    "⠇": "l",
    "⠍": "m",
    "⠝": "n",
    "⠕": "o",
    "⠏": "p",
    "⠟": "q",
    "⠗": "r",
    "⠎": "s",
    "⠞": "t",
    "⠥": "u",
    "⠧": "v",
    "⠺": "w",
    "⠭": "x",
    "⠽": "y",
    "⠵": "z",
}

_PUNCTUATION_CELLS = {
    "⠀": " ",
    "⠂": ",",
    "⠆": ";",
    "⠒": ":",
    "⠲": ".",
    "⠖": "!",
    "⠦": "?",
    "⠤": "-",
    "⠶": '"',
    "⠄": "'",
    "⠌": "/",
}

_NUMBER_CELLS = {
    "⠁": "1",
    "⠃": "2",
    "⠉": "3",
    "⠙": "4",
    "⠑": "5",
    "⠋": "6",
    "⠛": "7",
    "⠓": "8",
    "⠊": "9",
    "⠚": "0",
}

CAPITAL_SIGN = "⠠"
NUMBER_SIGN = "⠼"


def contains_braille(value: str) -> bool:
    """Return whether text contains one or more Unicode Braille-pattern cells."""

    return any("\u2800" <= character <= "\u28ff" for character in value)


def translate_uncontracted_braille(value: str) -> str:
    """Translate deterministic Grade-1 English Braille while preserving unknown cells."""

    output: list[str] = []
    capitalize = False
    number_mode = False
    for character in value:
        if character == CAPITAL_SIGN:
            capitalize = True
            continue
        if character == NUMBER_SIGN:
            number_mode = True
            continue
        if character.isspace() or character == "⠀":
            output.append(" ")
            number_mode = False
            capitalize = False
            continue
        if number_mode and character in _NUMBER_CELLS:
            output.append(_NUMBER_CELLS[character])
            continue
        number_mode = False
        translated = _LETTER_CELLS.get(character, _PUNCTUATION_CELLS.get(character))
        if translated is None:
            output.append(character)
            capitalize = False
            continue
        output.append(translated.upper() if capitalize else translated)
        capitalize = False
    return "".join(output)


def detect_braille_dot_geometry(image_path: str | Path) -> list[dict[str, object]]:
    """Detect conservative Braille-like circular dot geometry without guessing cell text."""

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[int, int, int, int, float]] = []
    maximum_size = min(image.shape[:2]) * 0.14
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width < 2 or height < 2 or width > maximum_size or height > maximum_size:
            continue
        aspect = width / height
        if not 0.55 <= aspect <= 1.8:
            continue
        area = float(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))
        if area <= 2 or perimeter <= 0:
            continue
        circularity = 4 * math.pi * area / (perimeter * perimeter)
        fill_ratio = area / (width * height)
        if circularity < 0.48 or fill_ratio < 0.42:
            continue
        candidates.append((x, y, width, height, circularity))
    if len(candidates) < 4:
        return []

    characteristic = median((width + height) / 2 for _, _, width, height, _ in candidates)
    consistent = [
        item
        for item in candidates
        if characteristic * 0.55 <= (item[2] + item[3]) / 2 <= characteristic * 1.8
    ]
    if len(consistent) < 4:
        return []

    def cluster_count(values: list[float]) -> int:
        clusters: list[float] = []
        tolerance = max(2.0, characteristic * 0.7)
        for value in sorted(values):
            if not clusters or value - clusters[-1] > tolerance:
                clusters.append(value)
            else:
                clusters[-1] = (clusters[-1] + value) / 2
        return len(clusters)

    centers_x = [x + width / 2 for x, _, width, _, _ in consistent]
    centers_y = [y + height / 2 for _, y, _, height, _ in consistent]
    if cluster_count(centers_x) < 2 or cluster_count(centers_y) < 2:
        return []

    return [
        {
            "bbox": [x, y, x + width, y + height],
            "center": [round(x + width / 2, 2), round(y + height / 2, 2)],
            "circularity": round(circularity, 4),
        }
        for x, y, width, height, circularity in sorted(
            consistent, key=lambda item: (item[1], item[0])
        )
    ]
