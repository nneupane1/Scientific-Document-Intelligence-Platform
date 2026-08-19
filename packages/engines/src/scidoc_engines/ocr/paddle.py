from __future__ import annotations

import importlib.util
from statistics import mean

from scidoc_core.confidence import Confidence, decide_confidence
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_schema.models import ElementContent

from scidoc_engines.base import EngineContext, EngineResult, RecognitionEngine, require_image
from scidoc_engines.capabilities import Capability


class PaddleOcrEngine(RecognitionEngine):
    name = "paddleocr"
    version = "optional"
    capabilities = frozenset({Capability.OCR_TEXT})
    supported_devices = frozenset({"cpu", "cuda"})
    _model: object | None = None

    def available(self) -> tuple[bool, str | None]:
        available = importlib.util.find_spec("paddleocr") is not None
        return (True, None) if available else (False, "install `pip install -e '.[paddle]'`")

    def supports(self, region: Region, context: EngineContext) -> bool:
        return region.region_type in {
            RegionType.TEXT,
            RegionType.CAPTION,
            RegionType.FIGURE,
            RegionType.TABLE,
            RegionType.UNKNOWN,
        }

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 2.0

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        path = require_image(region)
        if not self.available()[0]:
            raise RuntimeError(self.available()[1])
        if self._model is None:
            from paddleocr import PaddleOCR

            self._model = PaddleOCR(
                use_angle_cls=True, lang="en", use_gpu=context.device == "cuda", show_log=False
            )
        raw = self._model.ocr(str(path), cls=True)  # type: ignore[attr-defined]
        words: list[dict[str, object]] = []
        confidences: list[float] = []
        for line in raw[0] if raw else []:
            box, (text, score) = line
            xs, ys = [point[0] for point in box], [point[1] for point in box]
            words.append(
                {"text": text, "bbox": [min(xs), min(ys), max(xs), max(ys)], "confidence": score}
            )
            confidences.append(float(score))
        score = mean(confidences) if confidences else None
        threshold = float(context.options.get("ocr_acceptance", 0.97))
        return EngineResult(
            content=ElementContent(
                text="\n".join(str(word["text"]) for word in words), words=words
            ),
            confidence=Confidence(
                score=score,
                raw_score=score,
                source="paddle_mean_line_confidence",
                state=decide_confidence(score, threshold),
                threshold=threshold,
            ),
            provenance=Provenance(
                method="ocr",
                engine=self.name,
                engine_version=self.version,
                pipeline_version=context.pipeline_version,
                source_page=context.page_number,
            ),
            metrics={"words": words},
            warnings=[] if words else ["PaddleOCR returned no text"],
        )
