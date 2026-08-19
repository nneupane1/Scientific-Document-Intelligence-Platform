from __future__ import annotations

from scidoc_core.confidence import Confidence, ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region
from scidoc_schema.models import ElementContent

from scidoc_engines.base import EngineContext, EngineResult, RecognitionEngine
from scidoc_engines.capabilities import Capability


class NativeTextEngine(RecognitionEngine):
    name = "native_pdf"
    version = "pymupdf"
    capabilities = frozenset({Capability.NATIVE_TEXT})

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def supports(self, region: Region, context: EngineContext) -> bool:
        return bool(region.native_content and region.native_content.get("text"))

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 0.0

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        if not self.supports(region, context):
            raise ValueError("native text unavailable")
        return EngineResult(
            content=ElementContent.model_validate(region.native_content),
            confidence=Confidence(
                score=1.0,
                raw_score=1.0,
                source="deterministic_native_pdf",
                state=ConfidenceState.ACCEPTED,
                threshold=1.0,
            ),
            provenance=Provenance(
                method="native_pdf",
                engine=self.name,
                engine_version=self.version,
                pipeline_version=context.pipeline_version,
                source_page=context.page_number,
            ),
        )
