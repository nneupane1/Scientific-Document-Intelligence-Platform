from __future__ import annotations

import importlib.util

from PIL import Image
from scidoc_core.confidence import Confidence, ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_schema.models import ElementContent

from scidoc_engines.base import EngineContext, EngineResult, require_image
from scidoc_engines.capabilities import Capability
from scidoc_engines.math.base import FormulaEngine
from scidoc_engines.math.latex_mathml import latex_to_mathml, latex_to_unicode
from scidoc_engines.math.normalization import normalize_latex


class FormulaSmallEngine(FormulaEngine):
    """Optional, real local pix2tex model retained for the worker lifetime."""

    name = "formula_small"
    version = "pix2tex"
    capabilities = frozenset({Capability.FORMULA})
    supported_devices = frozenset({"cpu", "cuda", "mps"})
    _model: object | None = None

    def available(self) -> tuple[bool, str | None]:
        available = importlib.util.find_spec("pix2tex") is not None
        return (
            (True, None)
            if available
            else (False, "run `./scripts/download_models.sh formula` or install `.[math]`")
        )

    def supports(self, region: Region, context: EngineContext) -> bool:
        return region.region_type is RegionType.EQUATION

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 3.0

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        path = require_image(region)
        if not self.available()[0]:
            raise RuntimeError(self.available()[1])
        if self._model is None:
            from pix2tex.cli import LatexOCR

            self._model = LatexOCR()
        raw_latex = str(self._model(Image.open(path)))  # type: ignore[operator]
        normalized = normalize_latex(raw_latex)
        mathml, warning = latex_to_mathml(normalized)
        warnings = [warning] if warning else []
        # pix2tex exposes no calibrated recognition confidence; preserve that fact.
        return EngineResult(
            content=ElementContent(
                raw_latex=raw_latex,
                normalized_latex=normalized,
                latex=normalized,
                mathml=mathml,
                unicode=latex_to_unicode(normalized),
            ),
            confidence=Confidence(
                score=None,
                raw_score=None,
                source="unavailable",
                state=ConfidenceState.NEEDS_REVIEW,
                threshold=float(context.options.get("formula_acceptance", 0.97)),
            ),
            provenance=Provenance(
                method="formula_recognition",
                engine=self.name,
                engine_version=self.version,
                model="pix2tex",
                pipeline_version=context.pipeline_version,
                source_page=context.page_number,
            ),
            warnings=warnings + ["formula engine does not provide calibrated confidence"],
        )
