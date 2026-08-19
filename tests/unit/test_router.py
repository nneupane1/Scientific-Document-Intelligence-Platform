from __future__ import annotations

from scidoc_core.bbox import BBox
from scidoc_core.confidence import Confidence, ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region, RegionType
from scidoc_engines.base import EngineContext, EngineResult, RecognitionEngine
from scidoc_engines.capabilities import Capability
from scidoc_engines.registry import EngineRegistry
from scidoc_routing.policy import RoutingPolicy
from scidoc_routing.router import Router
from scidoc_schema.models import ElementContent


class CountingOcr(RecognitionEngine):
    name = "counting_ocr"
    version = "test"
    capabilities = frozenset({Capability.OCR_TEXT})

    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def supports(self, region: Region, context: EngineContext) -> bool:
        return True

    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        return 1

    def process(self, region: Region, context: EngineContext) -> EngineResult:
        self.calls += 1
        return EngineResult(
            content=ElementContent(text="OCR"),
            confidence=Confidence(
                score=0.99, raw_score=99, source="test", state=ConfidenceState.ACCEPTED
            ),
            provenance=Provenance(
                method="ocr", engine=self.name, pipeline_version="test", source_page=1
            ),
        )


def test_reliable_native_content_never_invokes_ocr() -> None:
    engine = CountingOcr()
    registry = EngineRegistry()
    registry.register(engine)
    region = Region(
        id="r1",
        page_number=1,
        bbox=BBox.from_list([0, 0, 10, 10]),
        region_type=RegionType.TEXT,
        native_content={"text": "Direct source text"},
        native_confidence=1.0,
    )
    result = Router(registry, RoutingPolicy()).route(region, EngineContext("doc", 1, "test"))
    assert result.state is ConfidenceState.ACCEPTED
    assert result.result is not None and result.result.content.text == "Direct source text"
    assert engine.calls == 0


def test_visual_text_uses_registered_ocr() -> None:
    engine = CountingOcr()
    registry = EngineRegistry()
    registry.register(engine)
    region = Region(
        id="r1", page_number=1, bbox=BBox.from_list([0, 0, 10, 10]), region_type=RegionType.TEXT
    )
    result = Router(registry, RoutingPolicy()).route(region, EngineContext("doc", 1, "test"))
    assert result.state is ConfidenceState.ACCEPTED
    assert engine.calls == 1
