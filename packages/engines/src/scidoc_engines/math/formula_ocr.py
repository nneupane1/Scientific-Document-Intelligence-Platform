from __future__ import annotations

from scidoc_core.confidence import Confidence, decide_confidence
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_schema.models import ElementContent

from scidoc_engines.base import EngineContext, EngineResult
from scidoc_engines.capabilities import Capability
from scidoc_engines.math.base import FormulaEngine
from scidoc_engines.math.latex_mathml import latex_to_mathml
from scidoc_engines.math.normalization import unicode_math_to_latex
from scidoc_engines.ocr.lightweight import LightweightOcrEngine


class FormulaOcrFallbackEngine(FormulaEngine):
    """Always-local formula fallback using OCR plus conservative notation normalization."""

    name = "formula_ocr_fallback"
    version = "rapidocr-or-tesseract+unicode-normalizer-v1"
    capabilities = frozenset({Capability.FORMULA})

    def __init__(self) -> None:
        self.ocr = LightweightOcrEngine()

    def available(self) -> tuple[bool, str | None]:
        return self.ocr.available()

    def supports(self, region: Region, context: EngineContext) -> bool:
        return region.region_type is RegionType.EQUATION

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 5.0

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        ocr_result = self.ocr.process(region, context)
        transcription = ocr_result.content.text or ""
        latex = unicode_math_to_latex(transcription)
        mathml, mathml_warning = latex_to_mathml(latex) if latex else (None, None)
        threshold = float(context.options.get("formula_acceptance", 0.97))
        score = ocr_result.confidence.score
        warnings = [
            *ocr_result.warnings,
            "formula used the local OCR fallback; review superscripts, subscripts, and operators",
        ]
        if mathml_warning:
            warnings.append(mathml_warning)
        return EngineResult(
            content=ElementContent(
                text=transcription,
                raw_latex=latex or None,
                normalized_latex=latex or None,
                latex=latex or None,
                mathml=mathml,
                unicode=transcription or None,
                words=ocr_result.content.words,
            ),
            confidence=Confidence(
                score=score,
                raw_score=ocr_result.confidence.raw_score,
                source="formula_ocr_mean_word_confidence" if score is not None else "unavailable",
                state=decide_confidence(score, threshold),
                threshold=threshold,
            ),
            provenance=Provenance(
                method="formula_ocr_fallback",
                engine=self.name,
                engine_version=self.version,
                pipeline_version=context.pipeline_version,
                source_page=context.page_number,
            ),
            metrics={"ocr": ocr_result.metrics},
            warnings=warnings,
        )
