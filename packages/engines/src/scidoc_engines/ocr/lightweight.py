from __future__ import annotations

import importlib.util
from statistics import mean

from PIL import Image
from scidoc_core.confidence import Confidence, decide_confidence
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_schema.models import ElementContent

from scidoc_engines.base import EngineContext, EngineResult, RecognitionEngine, require_image
from scidoc_engines.capabilities import Capability


class LightweightOcrEngine(RecognitionEngine):
    """Local OCR using RapidOCR first and Tesseract as an installed fallback."""

    name = "lightweight_ocr"
    version = "rapidocr-or-tesseract"
    capabilities = frozenset({Capability.OCR_TEXT})
    _rapid: object | None = None

    def _backend(self) -> str | None:
        if importlib.util.find_spec("rapidocr_onnxruntime"):
            return "rapidocr"
        if importlib.util.find_spec("pytesseract"):
            import pytesseract

            try:
                pytesseract.get_tesseract_version()
                return "tesseract"
            except (OSError, RuntimeError):
                pass
        return None

    def available(self) -> tuple[bool, str | None]:
        backend = self._backend()
        if backend:
            return True, None
        return False, "install `pip install -e '.[ocr]'`; Tesseract also needs a system package"

    def supports(self, region: Region, context: EngineContext) -> bool:
        return region.region_type in {
            RegionType.TEXT,
            RegionType.CAPTION,
            RegionType.FIGURE,
            RegionType.TABLE,
            RegionType.UNKNOWN,
        }

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 1.0

    def _rapidocr(self, path: str) -> tuple[str, list[float], list[dict[str, object]]]:
        if self._rapid is None:
            from rapidocr_onnxruntime import RapidOCR

            self._rapid = RapidOCR()
        output, _ = self._rapid(path)  # type: ignore[operator]
        if not output:
            return "", [], []
        words = []
        confidences: list[float] = []
        for box, text, score in output:
            xs, ys = [point[0] for point in box], [point[1] for point in box]
            words.append(
                {
                    "text": str(text),
                    "bbox": [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
                    "confidence": float(score),
                }
            )
            confidences.append(float(score))
        return (
            "\n".join(str(word["text"]) for word in words),
            confidences,
            words,
        )

    @staticmethod
    def _tesseract(path: str) -> tuple[str, list[float], list[dict[str, object]]]:
        import pytesseract
        from pytesseract import Output

        data = pytesseract.image_to_data(Image.open(path), output_type=Output.DICT)
        words: list[dict[str, object]] = []
        confidences: list[float] = []
        for index, text in enumerate(data["text"]):
            if not str(text).strip():
                continue
            raw = float(data["conf"][index])
            score = max(0.0, min(1.0, raw / 100)) if raw >= 0 else None
            left, top = float(data["left"][index]), float(data["top"][index])
            width, height = float(data["width"][index]), float(data["height"][index])
            words.append(
                {"text": text, "bbox": [left, top, left + width, top + height], "confidence": score}
            )
            if score is not None:
                confidences.append(score)
        return " ".join(str(word["text"]) for word in words), confidences, words

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        path = require_image(region)
        backend = self._backend()
        if backend is None:
            raise RuntimeError(self.available()[1])
        text, confidences, words = (
            self._rapidocr(str(path)) if backend == "rapidocr" else self._tesseract(str(path))
        )
        score = mean(confidences) if confidences else None
        threshold = float(context.options.get("ocr_acceptance", 0.97))
        warnings = [] if text.strip() else ["OCR returned no text"]
        return EngineResult(
            content=ElementContent(text=text, words=words),
            confidence=Confidence(
                score=score,
                raw_score=score,
                source=f"{backend}_mean_word_confidence" if score is not None else "unavailable",
                state=decide_confidence(score, threshold),
                threshold=threshold,
            ),
            provenance=Provenance(
                method="ocr",
                engine=backend,
                engine_version=self.version,
                pipeline_version=context.pipeline_version,
                source_page=context.page_number,
            ),
            metrics={"words": words, "backend": backend},
            warnings=warnings,
        )
