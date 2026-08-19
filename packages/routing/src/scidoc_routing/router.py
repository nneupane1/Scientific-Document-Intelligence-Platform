from __future__ import annotations

from dataclasses import dataclass, field

from scidoc_core.confidence import ConfidenceState
from scidoc_core.region import Region, RegionType
from scidoc_engines.base import EngineContext, EngineResult
from scidoc_engines.capabilities import Capability
from scidoc_engines.registry import EngineRegistry

from scidoc_routing.policy import RoutingPolicy


@dataclass(slots=True)
class RouteAttempt:
    engine: str
    available: bool
    accepted: bool
    reason: str | None = None
    score: float | None = None


@dataclass(slots=True)
class RouteOutcome:
    result: EngineResult | None
    state: ConfidenceState
    attempts: list[RouteAttempt] = field(default_factory=list)
    escalated: bool = False


class Router:
    """Cheapest-reliable-method-first routing cascade."""

    def __init__(self, registry: EngineRegistry, policy: RoutingPolicy) -> None:
        self.registry = registry
        self.policy = policy

    def route(self, region: Region, context: EngineContext) -> RouteOutcome:
        # This short-circuit is the central invariant: reliable native content never invokes OCR.
        if (
            region.native_content
            and (region.native_confidence or 0) >= self.policy.native_acceptance
        ):
            from scidoc_engines.native.text import NativeTextEngine

            result = NativeTextEngine().process(region, context)
            return RouteOutcome(
                result=result,
                state=ConfidenceState.ACCEPTED,
                attempts=[
                    RouteAttempt(engine="native_pdf", available=True, accepted=True, score=1.0)
                ],
            )

        capability = (
            Capability.FORMULA if region.region_type is RegionType.EQUATION else Capability.OCR_TEXT
        )
        threshold = (
            self.policy.formula_acceptance
            if capability is Capability.FORMULA
            else self.policy.ocr_acceptance
        )
        context.options.update(
            {
                "ocr_acceptance": self.policy.ocr_acceptance,
                "formula_acceptance": self.policy.formula_acceptance,
                "enable_large_formula_engine": self.policy.enable_large_formula_engine,
            }
        )
        attempts: list[RouteAttempt] = []
        last_result: EngineResult | None = None
        candidates = self.registry.candidates(capability, region, context)
        if not candidates:
            return RouteOutcome(
                result=None,
                state=ConfidenceState.ENGINE_UNAVAILABLE,
                attempts=[
                    RouteAttempt(
                        engine=capability.value,
                        available=False,
                        accepted=False,
                        reason="no engine supports the region",
                    )
                ],
            )
        for index, engine in enumerate(candidates):
            available, reason = engine.available()
            if not available:
                attempts.append(
                    RouteAttempt(engine=engine.name, available=False, accepted=False, reason=reason)
                )
                continue
            try:
                result = engine.process(region, context)
            except (RuntimeError, ValueError) as exc:
                attempts.append(
                    RouteAttempt(
                        engine=engine.name, available=True, accepted=False, reason=str(exc)
                    )
                )
                continue
            last_result = result
            accepted = result.confidence.score is not None and result.confidence.score >= threshold
            # Native results were handled above. Missing model scores require review.
            attempts.append(
                RouteAttempt(
                    engine=engine.name,
                    available=True,
                    accepted=accepted,
                    score=result.confidence.score,
                )
            )
            if accepted:
                return RouteOutcome(
                    result=result,
                    state=ConfidenceState.ACCEPTED,
                    attempts=attempts,
                    escalated=index > 0,
                )
        if last_result:
            return RouteOutcome(
                result=last_result,
                state=ConfidenceState.NEEDS_REVIEW,
                attempts=attempts,
                escalated=len(attempts) > 1,
            )
        return RouteOutcome(
            result=None,
            state=ConfidenceState.ENGINE_UNAVAILABLE,
            attempts=attempts,
            escalated=len(attempts) > 1,
        )
