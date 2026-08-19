from __future__ import annotations

from pathlib import Path

import cv2
from pydantic import BaseModel, ConfigDict
from scidoc_core.bbox import BBox
from scidoc_core.region import RegionType


class LayoutRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bbox: BBox
    region_type: RegionType
    score: float | None = None


class ClassicalLayoutDetector:
    """Connected-component layout fallback for raster pages."""

    name = "opencv_classical_layout"
    version = cv2.__version__

    def detect(
        self, image_path: str | Path, *, page_width: float, page_height: float
    ) -> list[LayoutRegion]:
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot load page image: {image_path}")
        inverted = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel_width = max(15, image.shape[1] // 45)
        merged = cv2.morphologyEx(
            inverted, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 5))
        )
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        scale_x, scale_y = page_width / image.shape[1], page_height / image.shape[0]
        regions: list[LayoutRegion] = []
        minimum_area = image.shape[0] * image.shape[1] * 0.00008
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if width * height < minimum_area or width < 12 or height < 8:
                continue
            density = cv2.countNonZero(inverted[y : y + height, x : x + width]) / (width * height)
            aspect = width / max(height, 1)
            centered = abs((x + width / 2) - image.shape[1] / 2) < image.shape[1] * 0.2
            region_type = RegionType.TEXT
            if density > 0.42 and height > image.shape[0] * 0.08:
                region_type = RegionType.FIGURE
            elif (
                centered and 1.2 < aspect < 14 and density < 0.32 and height < image.shape[0] * 0.12
            ):
                region_type = RegionType.EQUATION
            regions.append(
                LayoutRegion(
                    bbox=BBox(
                        x0=x * scale_x,
                        y0=y * scale_y,
                        x1=(x + width) * scale_x,
                        y1=(y + height) * scale_y,
                    ),
                    region_type=region_type,
                    score=None,
                )
            )
        if not regions:
            regions.append(
                LayoutRegion(
                    bbox=BBox(x0=0, y0=0, x1=page_width, y1=page_height),
                    region_type=RegionType.TEXT,
                )
            )
        return regions
