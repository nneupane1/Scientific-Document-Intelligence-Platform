from __future__ import annotations

from collections import defaultdict
from typing import TypedDict

from scidoc_engines.base import EngineContext, RecognitionEngine
from scidoc_engines.capabilities import Capability


class EngineStatus(TypedDict):
    name: str
    version: str
    capabilities: list[str]
    devices: list[str]
    available: bool
    reason: str | None


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, RecognitionEngine] = {}
        self._capabilities: dict[Capability, list[str]] = defaultdict(list)

    def register(self, engine: RecognitionEngine) -> None:
        self._engines[engine.name] = engine
        for capability in engine.capabilities:
            if engine.name not in self._capabilities[capability]:
                self._capabilities[capability].append(engine.name)

    def get(self, name: str) -> RecognitionEngine:
        return self._engines[name]

    def candidates(
        self, capability: Capability, region: object, context: EngineContext
    ) -> list[RecognitionEngine]:
        engines = [self._engines[name] for name in self._capabilities.get(capability, [])]
        supported = [engine for engine in engines if engine.supports(region, context)]  # type: ignore[arg-type]
        return sorted(supported, key=lambda engine: engine.estimate_cost(region, context))  # type: ignore[arg-type]

    def versions(self) -> dict[str, str]:
        return {
            name: engine.version for name, engine in self._engines.items() if engine.available()[0]
        }

    def statuses(self) -> list[EngineStatus]:
        """Describe every registered engine, including intentionally unavailable specialists."""
        result: list[EngineStatus] = []
        for name, engine in self._engines.items():
            try:
                available, reason = engine.available()
            except Exception as error:  # pragma: no cover - defensive adapter boundary
                available, reason = False, f"availability check failed: {type(error).__name__}"
            result.append(
                {
                    "name": name,
                    "version": engine.version,
                    "capabilities": sorted(capability.value for capability in engine.capabilities),
                    "devices": sorted(engine.supported_devices),
                    "available": available,
                    "reason": reason,
                }
            )
        return result


def default_registry() -> EngineRegistry:
    from scidoc_engines.math.formula_large import FormulaLargeEngine
    from scidoc_engines.math.formula_ocr import FormulaOcrFallbackEngine
    from scidoc_engines.math.formula_small import FormulaSmallEngine
    from scidoc_engines.ocr.lightweight import LightweightOcrEngine
    from scidoc_engines.ocr.paddle import PaddleOcrEngine

    registry = EngineRegistry()
    registry.register(LightweightOcrEngine())
    registry.register(PaddleOcrEngine())
    registry.register(FormulaSmallEngine())
    registry.register(FormulaOcrFallbackEngine())
    registry.register(FormulaLargeEngine())
    return registry
