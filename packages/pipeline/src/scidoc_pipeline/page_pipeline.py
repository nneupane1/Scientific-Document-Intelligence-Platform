from __future__ import annotations

import json
from pathlib import Path

import cv2
import pymupdf as fitz
from scidoc_core.bbox import BBox
from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance, ProvenanceEvent
from scidoc_core.region import Region, RegionType
from scidoc_engines.base import EngineContext
from scidoc_layout.detector import ClassicalLayoutDetector
from scidoc_layout.postprocess import remove_near_duplicates
from scidoc_layout.reading_order import sort_reading_order
from scidoc_pdf.braille import detect_braille_dot_geometry
from scidoc_pdf.classifier import has_reliable_native_text
from scidoc_pdf.inspector import inspect_page
from scidoc_pdf.native_text import extract_native_elements
from scidoc_pdf.renderer import PageRenderer
from scidoc_preprocessing.quality import analyze_quality
from scidoc_routing.router import Router
from scidoc_schema.models import ElementContent, ElementType, PageMetrics, SdrElement, SdrPage
from scidoc_storage.cache import FileCache, cache_key

from scidoc_pipeline.context import PipelineContext
from scidoc_pipeline.region_pipeline import RegionPipeline


class PagePipeline:
    def __init__(self, context: PipelineContext, document_dir: Path) -> None:
        self.context = context
        self.document_dir = document_dir
        self.renderer = PageRenderer(document_dir / "rendered")
        self.layout = ClassicalLayoutDetector()
        self.region_pipeline = RegionPipeline(Router(context.registry, context.routing_policy))
        self.cache = FileCache(context.settings.storage_root / "cache")

    def _recognize(
        self, region: Region, engine_context: EngineContext, reading_order: int
    ) -> SdrElement:
        if region.image_path is None:
            return self.region_pipeline.process(region, engine_context, reading_order)
        key = cache_key(
            region.image_path.read_bytes(),
            engine_name="cost_aware_router",
            model_version=json.dumps(self.context.registry.versions(), sort_keys=True),
            preprocessing={"dpi": engine_context.dpi},
            options={
                "config_hash": self.context.settings.config_hash(),
                "region_type": region.region_type.value,
            },
        )
        cached = self.cache.get(key)
        if cached is not None:
            element = SdrElement.model_validate_json(cached)
            element.id = region.id
            element.bbox = (
                region.bbox.x0,
                region.bbox.y0,
                region.bbox.x1,
                region.bbox.y1,
            )
            element.reading_order = reading_order
            element.provenance.source_page = region.page_number
            element.provenance.cache_hit = True
            element.provenance.cache_key = key
            return element
        element = self.region_pipeline.process(region, engine_context, reading_order)
        element.provenance.cache_hit = False
        element.provenance.cache_key = key
        self.cache.put(key, element.model_dump_json().encode())
        return element

    def _prefix_ids(self, elements: list[SdrElement], page_number: int) -> list[SdrElement]:
        for index, element in enumerate(elements, start=1):
            element.id = f"{self.context.document_id}-p{page_number}-e{index}"
            element.reading_order = index - 1
        return elements

    def _native_tables(self, page: fitz.Page) -> list[SdrElement]:
        """Recover native table cells as rows and columns without inventing missing values."""

        if not self.context.settings.enable_tables or not hasattr(page, "find_tables"):
            return []
        try:
            detected = page.find_tables().tables
        except (AttributeError, RuntimeError, ValueError):
            return []
        result: list[SdrElement] = []
        for table in detected:
            raw_rows = table.extract() or []
            rows = [
                [None if value is None else str(value).strip() for value in row] for row in raw_rows
            ]
            if not rows or not any(any(value for value in row) for row in rows):
                continue
            header = getattr(table, "header", None)
            names = [str(value or "").strip() for value in getattr(header, "names", [])]
            columns = (
                names if any(names) else [f"column_{index + 1}" for index in range(len(rows[0]))]
            )
            data_rows = rows
            if names and rows[0] == names:
                data_rows = rows[1:]
            raw_bbox = table.bbox
            bbox = BBox(
                x0=float(raw_bbox[0]),
                y0=float(raw_bbox[1]),
                x1=float(raw_bbox[2]),
                y1=float(raw_bbox[3]),
            )
            text_rows: list[list[str | None]] = [list(columns), *data_rows]
            result.append(
                SdrElement(
                    id="pending",
                    type=ElementType.TABLE,
                    bbox=tuple(bbox.as_list()),
                    reading_order=0,
                    content=ElementContent(
                        text="\n".join(
                            "\t".join("" if value is None else str(value) for value in row)
                            for row in text_rows
                        ),
                        columns=columns,
                        rows=data_rows,
                    ),
                    confidence=0.99,
                    confidence_source="deterministic_native_table_geometry",
                    provenance=Provenance(
                        method="native_pdf_table",
                        engine="pymupdf.find_tables",
                        engine_version=fitz.VersionBind,
                        pipeline_version=self.context.settings.pipeline_version,
                        source_page=page.number + 1,
                    ),
                    review_status=ConfidenceState.ACCEPTED,
                )
            )
        return result

    def _visual_element_type(self, context_text: str) -> ElementType:
        text = context_text.casefold()
        settings = self.context.settings
        if "braille" in text:
            return ElementType.BRAILLE
        if settings.enable_chemistry:
            if any(term in text for term in ("reaction", "chemical equation", "reaction scheme")):
                return ElementType.CHEMICAL_EQUATION
            if any(
                term in text for term in ("molecule", "molecular structure", "chemical structure")
            ):
                return ElementType.MOLECULE
        if settings.enable_charts and any(
            term in text for term in ("chart", "graph", "plot", "histogram", "spectrum")
        ):
            return ElementType.CHART
        if settings.enable_diagrams:
            if "circuit" in text:
                return ElementType.CIRCUIT
            if any(term in text for term in ("diagram", "schematic", "flowchart", "workflow")):
                return ElementType.DIAGRAM
        if settings.enable_tables and "table" in text:
            return ElementType.TABLE
        return ElementType.FIGURE

    @staticmethod
    def _inside_any_table(element: SdrElement, tables: list[SdrElement]) -> bool:
        x0, y0, x1, y1 = element.bbox
        center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
        return any(
            table.bbox[0] <= center_x <= table.bbox[2]
            and table.bbox[1] <= center_y <= table.bbox[3]
            for table in tables
        )

    def _specialize_visual(self, element: SdrElement, context_text: str) -> SdrElement:
        target = self._visual_element_type(f"{context_text}\n{element.content.text or ''}")
        element.type = target
        label = target.value.replace("_", " ")
        nearby = " ".join(context_text.split())
        element.content.alt_text = f"Detected {label} from the source PDF" + (
            f"; nearby text: {nearby[:240]}" if nearby else ""
        )
        if target is not ElementType.FIGURE:
            element.warnings = sorted(
                set([*element.warnings, "visual subtype is evidence-based and should be reviewed"])
            )
            if element.review_status is ConfidenceState.ACCEPTED:
                element.review_status = ConfidenceState.UNCERTAIN
        return element

    def _apply_visual_braille_fallback(self, element: SdrElement, region: Region) -> SdrElement:
        if region.image_path is None or (element.content.text or "").strip():
            return element
        dots = detect_braille_dot_geometry(region.image_path)
        if not dots:
            return element
        element.type = ElementType.BRAILLE
        element.content.alt_text = (
            f"Braille-like dot geometry detected ({len(dots)} dots); "
            "cell transcription requires review"
        )
        element.content.candidates.append(
            {"engine": "opencv_braille_geometry", "kind": "braille_dots", "dots": dots}
        )
        element.review_status = ConfidenceState.NEEDS_REVIEW
        element.warnings = sorted(
            set(
                [
                    *element.warnings,
                    "Braille-like dots were preserved geometrically; no characters were guessed",
                ]
            )
        )
        element.provenance.history.append(
            ProvenanceEvent(
                method="braille_dot_geometry",
                engine="opencv",
                engine_version=cv2.__version__,
                pipeline_version=self.context.settings.pipeline_version,
                source_page=region.page_number,
                details={"dot_count": len(dots)},
            )
        )
        return element

    @staticmethod
    def _nearby_text(page: fitz.Page, bbox: BBox) -> str:
        candidates = []
        for block in page.get_text("blocks", sort=True):
            if len(block) <= 4:
                continue
            if float(block[0]) >= bbox.x1 or float(block[2]) <= bbox.x0:
                continue
            distance = min(abs(float(block[3]) - bbox.y0), abs(float(block[1]) - bbox.y1))
            if distance <= page.rect.height * 0.16:
                candidates.append((distance, str(block[4])))
        candidates.sort(key=lambda item: item[0])
        return "\n".join(text for _, text in candidates[:2])

    def _vector_visuals(
        self, page: fitz.Page, start: int, excluded: list[SdrElement]
    ) -> list[SdrElement]:
        """Preserve substantial vector charts and diagrams as OCR-addressable SDR regions."""

        settings = self.context.settings
        if not (settings.enable_charts or settings.enable_diagrams or settings.enable_chemistry):
            return []
        try:
            clusters = page.cluster_drawings()
        except (AttributeError, RuntimeError, ValueError):
            return []
        result: list[SdrElement] = []
        page_area = page.rect.get_area()
        excluded_boxes = [BBox.from_list(element.bbox) for element in excluded]
        for rectangle in clusters:
            bbox = BBox.from_list(
                [float(rectangle.x0), float(rectangle.y0), float(rectangle.x1), float(rectangle.y1)]
            )
            area_ratio = bbox.area / page_area if page_area else 0
            if not 0.015 <= area_ratio <= 0.65:
                continue
            if bbox.width < page.rect.width * 0.12 or bbox.height < page.rect.height * 0.06:
                continue
            if any(bbox.iou(item) >= 0.45 for item in excluded_boxes):
                continue
            index = start + len(result)
            region_id = f"{self.context.document_id}-p{page.number + 1}-e{index + 1}"
            crop = self.renderer.render_region(page, bbox, region_id, settings.default_dpi)
            region = Region(
                id=region_id,
                page_number=page.number + 1,
                bbox=bbox,
                region_type=RegionType.FIGURE,
                image_path=crop,
                metadata={"detection": "native_vector_cluster"},
            )
            element = self._recognize(
                region,
                EngineContext(
                    document_id=self.context.document_id,
                    page_number=page.number + 1,
                    pipeline_version=settings.pipeline_version,
                    dpi=settings.default_dpi,
                ),
                index,
            )
            element.provenance.history.insert(
                0,
                ProvenanceEvent(
                    method="native_pdf_vector_geometry",
                    engine="pymupdf.cluster_drawings",
                    engine_version=fitz.VersionBind,
                    pipeline_version=settings.pipeline_version,
                    source_page=page.number + 1,
                    details={"area_ratio": round(area_ratio, 6)},
                ),
            )
            element = self._apply_visual_braille_fallback(element, region)
            result.append(
                element
                if element.type is ElementType.BRAILLE
                else self._specialize_visual(element, self._nearby_text(page, bbox))
            )
        return result

    def _embedded_visuals(self, page: fitz.Page, start: int) -> list[SdrElement]:
        result: list[SdrElement] = []
        seen: list[BBox] = []
        for image in page.get_images(full=True):
            try:
                rectangles = page.get_image_rects(image[0])
            except (RuntimeError, ValueError):
                continue
            for rectangle in rectangles:
                bbox = BBox.from_list([rectangle.x0, rectangle.y0, rectangle.x1, rectangle.y1])
                if bbox.area < page.rect.get_area() * 0.01 or any(
                    bbox.iou(item) > 0.95 for item in seen
                ):
                    continue
                seen.append(bbox)
                index = start + len(result)
                nearby_text = self._nearby_text(page, bbox)
                equation_candidate = "formula" in nearby_text.casefold()
                if equation_candidate:
                    region_id = f"{self.context.document_id}-p{page.number + 1}-e{index + 1}"
                    crop = self.renderer.render_region(
                        page, bbox, region_id, self.context.settings.default_dpi
                    )
                    region = Region(
                        id=region_id,
                        page_number=page.number + 1,
                        bbox=bbox,
                        region_type=RegionType.EQUATION,
                        image_path=crop,
                        metadata={"detection": "preceding_formula_label"},
                    )
                    result.append(
                        self._recognize(
                            region,
                            EngineContext(
                                document_id=self.context.document_id,
                                page_number=page.number + 1,
                                pipeline_version=self.context.settings.pipeline_version,
                                dpi=self.context.settings.default_dpi,
                            ),
                            index,
                        )
                    )
                    continue
                region_id = f"{self.context.document_id}-p{page.number + 1}-e{index + 1}"
                crop = self.renderer.render_region(
                    page, bbox, region_id, self.context.settings.default_dpi
                )
                region = Region(
                    id=region_id,
                    page_number=page.number + 1,
                    bbox=bbox,
                    region_type=RegionType.FIGURE,
                    image_path=crop,
                    metadata={"detection": "native_embedded_image"},
                )
                element = self._recognize(
                    region,
                    EngineContext(
                        document_id=self.context.document_id,
                        page_number=page.number + 1,
                        pipeline_version=self.context.settings.pipeline_version,
                        dpi=self.context.settings.default_dpi,
                    ),
                    index,
                )
                element.provenance.history.insert(
                    0,
                    ProvenanceEvent(
                        method="native_pdf_image_geometry",
                        engine="pymupdf",
                        engine_version=fitz.VersionBind,
                        pipeline_version=self.context.settings.pipeline_version,
                        source_page=page.number + 1,
                        details={"embedded_image": True},
                    ),
                )
                element = self._apply_visual_braille_fallback(element, region)
                result.append(
                    element
                    if element.type is ElementType.BRAILLE
                    else self._specialize_visual(element, nearby_text)
                )
        return result

    def _visual_elements(
        self, page: fitz.Page
    ) -> tuple[list[SdrElement], str, dict[str, float | int | str | bool | None]]:
        settings = self.context.settings
        rendered = self.renderer.render_page(page, settings.default_dpi)
        quality = analyze_quality(rendered).model_dump()
        quality["effective_dpi_x"] = quality["width"] / (page.rect.width / 72)
        quality["effective_dpi_y"] = quality["height"] / (page.rect.height / 72)
        detected = remove_near_duplicates(
            self.layout.detect(rendered, page_width=page.rect.width, page_height=page.rect.height)
        )
        ordered = sort_reading_order(detected, page.rect.width)
        elements: list[SdrElement] = []
        for index, layout_region in enumerate(ordered):
            region_id = f"{self.context.document_id}-p{page.number + 1}-e{index + 1}"
            crop = self.renderer.render_region(
                page, layout_region.bbox, region_id, settings.default_dpi
            )
            region = Region(
                id=region_id,
                page_number=page.number + 1,
                bbox=layout_region.bbox,
                region_type=layout_region.region_type,
                image_path=crop,
                metadata={"layout_engine": self.layout.name},
            )
            engine_context = EngineContext(
                document_id=self.context.document_id,
                page_number=page.number + 1,
                pipeline_version=settings.pipeline_version,
                dpi=settings.default_dpi,
            )
            element = self._recognize(region, engine_context, index)
            element = self._apply_visual_braille_fallback(element, region)
            if element.type is not ElementType.BRAILLE and region.region_type in {
                RegionType.FIGURE,
                RegionType.TABLE,
            }:
                element = self._specialize_visual(element, "")
            if (
                settings.enable_high_dpi_retry
                and element.confidence is not None
                and element.review_status
                in {ConfidenceState.UNCERTAIN, ConfidenceState.NEEDS_REVIEW}
            ):
                high_res_crop = self.renderer.render_region(
                    page, region.bbox, region_id, settings.escalation_dpi
                )
                region.image_path = high_res_crop
                engine_context.dpi = settings.escalation_dpi
                retry = self._recognize(region, engine_context, index)
                previous_event = ProvenanceEvent(
                    method=element.provenance.method,
                    engine=element.provenance.engine,
                    engine_version=element.provenance.engine_version,
                    model=element.provenance.model,
                    model_version=element.provenance.model_version,
                    pipeline_version=element.provenance.pipeline_version,
                    source_page=element.provenance.source_page,
                    details={"reason": "higher-DPI retry", "dpi": settings.default_dpi},
                )
                if (retry.confidence or 0) > (element.confidence or 0):
                    retry.provenance.history.extend(element.provenance.history)
                    retry.provenance.history.append(previous_event)
                    element = retry
                else:
                    element.provenance.history.append(
                        ProvenanceEvent(
                            method=retry.provenance.method,
                            engine=retry.provenance.engine,
                            engine_version=retry.provenance.engine_version,
                            model=retry.provenance.model,
                            model_version=retry.provenance.model_version,
                            pipeline_version=retry.provenance.pipeline_version,
                            source_page=retry.provenance.source_page,
                            details={
                                "reason": "higher-DPI retry did not improve confidence",
                                "dpi": settings.escalation_dpi,
                            },
                        )
                    )
            elements.append(element)
        return elements, str(rendered), quality

    def process(self, page: fitz.Page) -> SdrPage:
        inspection = inspect_page(page)
        settings = self.context.settings
        reliable_native = has_reliable_native_text(
            text=inspection.native_text,
            text_coverage=inspection.text_coverage,
            min_characters=settings.native_min_characters,
        )
        rendered_path: str | None = None
        quality: dict[str, float | int | str | bool | None] = {}
        if reliable_native:
            elements = extract_native_elements(page, pipeline_version=settings.pipeline_version)
            tables = self._native_tables(page)
            if tables:
                elements = [
                    element for element in elements if not self._inside_any_table(element, tables)
                ]
                elements.extend(tables)
            elements.sort(key=lambda item: (item.bbox[1], item.bbox[0]))
            embedded = self._embedded_visuals(page, len(elements))
            elements.extend(embedded)
            elements.extend(self._vector_visuals(page, len(elements), [*tables, *embedded]))
            elements.sort(key=lambda item: (item.bbox[1], item.bbox[0]))
            elements = self._prefix_ids(elements, page.number + 1)
        else:
            elements, rendered_path, quality = self._visual_elements(page)
        elements.sort(key=lambda item: item.reading_order)
        metrics = PageMetrics(
            rotation=inspection.rotation,
            text_blocks=inspection.text_blocks,
            text_coverage=inspection.text_coverage,
            embedded_images=inspection.embedded_images,
            image_coverage=inspection.image_coverage,
            vector_objects=inspection.vector_objects,
            fonts=inspection.fonts,
            render_dpi=settings.default_dpi if rendered_path else None,
            quality=quality,
        )
        return SdrPage(
            number=page.number + 1,
            width=page.rect.width,
            height=page.rect.height,
            classification=inspection.classification.value,
            elements=elements,
            metrics=metrics,
        )
