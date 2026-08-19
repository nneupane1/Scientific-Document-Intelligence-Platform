from __future__ import annotations

from collections import Counter
from pathlib import Path

import pymupdf as fitz
from pydantic import BaseModel, ConfigDict, Field
from scidoc_core.page import PageClassification

from scidoc_pdf.classifier import classify_page


class PageInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int
    width: float
    height: float
    rotation: int
    text_blocks: int
    text_coverage: float = Field(ge=0, le=1)
    embedded_images: int
    image_coverage: float = Field(ge=0, le=1)
    vector_objects: int
    fonts: list[str]
    native_text: str
    classification: PageClassification


class DocumentInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    page_count: int
    metadata: dict[str, str]
    pages: list[PageInspection]
    classifications: dict[str, int]
    fonts: list[str]
    embedded_images: int


def _bounded_coverage(rectangles: list[fitz.Rect], page_rect: fitz.Rect) -> float:
    if page_rect.get_area() <= 0:
        return 0.0
    clipped_area = sum((rect & page_rect).get_area() for rect in rectangles)
    return float(min(1.0, max(0.0, clipped_area / page_rect.get_area())))


def inspect_page(page: fitz.Page, *, include_text: bool = True) -> PageInspection:
    raw = page.get_text("dict", sort=True)
    text_rects: list[fitz.Rect] = []
    fonts: set[str] = set()
    text_parts: list[str] = []
    text_blocks = 0
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        text_blocks += 1
        text_rects.append(fitz.Rect(block["bbox"]))
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("font"):
                    fonts.add(str(span["font"]))
                if include_text and span.get("text"):
                    text_parts.append(str(span["text"]))

    image_rects: list[fitz.Rect] = []
    for image in page.get_images(full=True):
        try:
            image_rects.extend(page.get_image_rects(image[0]))
        except (RuntimeError, ValueError):
            continue
    drawings = page.get_drawings()
    text_coverage = _bounded_coverage(text_rects, page.rect)
    image_coverage = _bounded_coverage(image_rects, page.rect)
    classification = classify_page(
        text_coverage=text_coverage,
        image_coverage=image_coverage,
        text_blocks=text_blocks,
        vector_objects=len(drawings),
    )
    return PageInspection(
        number=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        rotation=page.rotation,
        text_blocks=text_blocks,
        text_coverage=text_coverage,
        embedded_images=len(page.get_images(full=True)),
        image_coverage=image_coverage,
        vector_objects=len(drawings),
        fonts=sorted(fonts),
        native_text="\n".join(text_parts),
        classification=classification,
    )


def inspect_document(path: str | Path, *, include_text: bool = True) -> DocumentInspection:
    target = Path(path)
    with fitz.open(target) as document:
        pages = [inspect_page(page, include_text=include_text) for page in document]
        counts = Counter(page.classification.value for page in pages)
        metadata = {str(key): str(value or "") for key, value in document.metadata.items()}
    return DocumentInspection(
        filename=target.name,
        page_count=len(pages),
        metadata=metadata,
        pages=pages,
        classifications={
            classification.value: counts[classification.value]
            for classification in PageClassification
        },
        fonts=sorted({font for page in pages for font in page.fonts}),
        embedded_images=sum(page.embedded_images for page in pages),
    )
