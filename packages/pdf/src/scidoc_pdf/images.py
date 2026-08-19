from __future__ import annotations

import pymupdf as fitz


def embedded_image_metadata(page: fitz.Page) -> list[dict[str, int | str]]:
    return [
        {
            "xref": int(image[0]),
            "width": int(image[2]),
            "height": int(image[3]),
            "bits": int(image[4]),
            "colorspace": str(image[5]),
        }
        for image in page.get_images(full=True)
    ]
