from __future__ import annotations

from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_engines.base import EngineContext
from scidoc_routing.router import Router
from scidoc_schema.models import ElementContent, ElementType, SdrElement
from scidoc_validation.math import validate_latex
from scidoc_validation.scientific_symbols import diagnose_ambiguous_symbols
from scidoc_validation.text import validate_text

_ELEMENT_TYPES = {
    RegionType.TEXT: ElementType.PARAGRAPH,
    RegionType.EQUATION: ElementType.EQUATION,
    RegionType.FIGURE: ElementType.FIGURE,
    RegionType.TABLE: ElementType.TABLE,
    RegionType.CAPTION: ElementType.CAPTION,
    RegionType.UNKNOWN: ElementType.UNKNOWN,
}


class RegionPipeline:
    def __init__(self, router: Router) -> None:
        self.router = router

    def process(self, region: Region, context: EngineContext, reading_order: int) -> SdrElement:
        outcome = self.router.route(region, context)
        attempts = [
            {
                "engine": attempt.engine,
                "available": attempt.available,
                "accepted": attempt.accepted,
                "reason": attempt.reason,
                "score": attempt.score,
            }
            for attempt in outcome.attempts
        ]
        if outcome.result is None:
            return SdrElement(
                id=region.id,
                type=_ELEMENT_TYPES[region.region_type],
                bbox=tuple(region.bbox.as_list()),
                reading_order=reading_order,
                content=ElementContent(candidates=attempts),
                confidence=None,
                confidence_source="unavailable",
                provenance=Provenance(
                    method="recognition_unavailable",
                    engine=outcome.attempts[-1].engine if outcome.attempts else "none",
                    pipeline_version=context.pipeline_version,
                    source_page=context.page_number,
                ),
                review_status=ConfidenceState.ENGINE_UNAVAILABLE,
                warnings=[attempt.reason for attempt in outcome.attempts if attempt.reason],
            )

        result = outcome.result
        result.content.candidates = attempts
        warnings = list(result.warnings)
        if region.region_type is RegionType.EQUATION:
            latex = result.content.latex or ""
            warnings.extend(validate_latex(latex).warnings)
        else:
            text = result.content.text or ""
            warnings.extend(validate_text(text).warnings)
            warnings.extend(diagnose_ambiguous_symbols(text))
        state = outcome.state
        if warnings and state is ConfidenceState.ACCEPTED:
            state = ConfidenceState.UNCERTAIN
        return SdrElement(
            id=region.id,
            type=_ELEMENT_TYPES[region.region_type],
            bbox=tuple(region.bbox.as_list()),
            reading_order=reading_order,
            content=result.content,
            confidence=result.confidence.score,
            confidence_source=result.confidence.source,
            provenance=result.provenance,
            review_status=state,
            warnings=sorted(set(warnings)),
        )
