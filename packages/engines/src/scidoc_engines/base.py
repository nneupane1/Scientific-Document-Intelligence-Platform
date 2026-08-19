from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scidoc_core.confidence import Confidence
from scidoc_core.provenance import Provenance
from scidoc_core.region import Region
from scidoc_schema.models import ElementContent

from scidoc_engines.capabilities import Capability


@dataclass(slots=True)
class EngineContext:
    document_id: str
    page_number: int
    pipeline_version: str
    device: str = "cpu"
    dpi: int = 300
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineResult:
    content: ElementContent
    confidence: Confidence
    provenance: Provenance
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class RecognitionEngine(ABC):
    name: str
    version: str
    capabilities: frozenset[Capability]
    supported_devices: frozenset[str] = frozenset({"cpu"})

    @abstractmethod
    def available(self) -> tuple[bool, str | None]:
        """Return availability and an actionable reason when unavailable."""

    @abstractmethod
    def supports(self, region: Region, context: EngineContext) -> bool:
        pass

    @abstractmethod
    def estimate_cost(self, region: Region, context: EngineContext) -> float:
        pass

    @abstractmethod
    def process(self, region: Region, context: EngineContext) -> EngineResult:
        pass


def require_image(region: Region) -> Path:
    if region.image_path is None or not region.image_path.exists():
        raise ValueError(f"region {region.id} has no readable image crop")
    return region.image_path
