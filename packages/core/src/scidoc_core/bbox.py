from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

Coordinate = Annotated[float, Field(ge=0)]


class BBox(BaseModel):
    """Top-left-origin bounding box in source page coordinates."""

    x0: Coordinate
    y0: Coordinate
    x1: Coordinate
    y1: Coordinate

    @model_validator(mode="after")
    def ordered(self) -> BBox:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("bbox maximum coordinates must follow minimum coordinates")
        return self

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, float, float, float]) -> BBox:
        if len(values) != 4:
            raise ValueError("bbox requires exactly four coordinates")
        return cls(x0=values[0], y0=values[1], x1=values[2], y1=values[3])

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    def normalized(self, page_width: float, page_height: float) -> BBox:
        if page_width <= 0 or page_height <= 0:
            raise ValueError("page dimensions must be positive")
        return BBox(
            x0=self.x0 / page_width,
            y0=self.y0 / page_height,
            x1=self.x1 / page_width,
            y1=self.y1 / page_height,
        )

    def scale(self, scale_x: float, scale_y: float | None = None) -> BBox:
        sy = scale_x if scale_y is None else scale_y
        return BBox(
            x0=self.x0 * scale_x,
            y0=self.y0 * sy,
            x1=self.x1 * scale_x,
            y1=self.y1 * sy,
        )

    def iou(self, other: BBox) -> float:
        ix0, iy0 = max(self.x0, other.x0), max(self.y0, other.y0)
        ix1, iy1 = min(self.x1, other.x1), min(self.y1, other.y1)
        intersection = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        union = self.area + other.area - intersection
        return intersection / union if union else 0.0
