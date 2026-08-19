from __future__ import annotations

from dataclasses import dataclass

from scidoc_core.config import Settings


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    native_acceptance: float = 0.99
    ocr_acceptance: float = 0.97
    formula_acceptance: float = 0.97
    enable_high_dpi_retry: bool = True
    enable_large_formula_engine: bool = False
    enable_vlm: bool = True

    @classmethod
    def from_settings(cls, settings: Settings) -> RoutingPolicy:
        return cls(
            native_acceptance=settings.native_acceptance,
            ocr_acceptance=settings.ocr_acceptance,
            formula_acceptance=settings.formula_acceptance,
            enable_high_dpi_retry=settings.enable_high_dpi_retry,
            enable_large_formula_engine=settings.enable_large_formula_engine,
            enable_vlm=settings.enable_vlm,
        )
