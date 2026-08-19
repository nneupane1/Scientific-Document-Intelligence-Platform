from __future__ import annotations

from scidoc_core.region import Region

from scidoc_engines.base import EngineContext, EngineResult
from scidoc_engines.capabilities import Capability
from scidoc_engines.math.base import FormulaEngine


class FormulaLargeEngine(FormulaEngine):
    name = "formula_large"
    version = "disabled"
    capabilities = frozenset({Capability.FORMULA})

    def available(self) -> tuple[bool, str | None]:
        return False, "no large formula model is configured"

    def supports(self, region: Region, context: EngineContext) -> bool:
        return bool(context.options.get("enable_large_formula_engine", False))

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 8.0

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        raise RuntimeError("formula_large is disabled; configure a local model adapter")
