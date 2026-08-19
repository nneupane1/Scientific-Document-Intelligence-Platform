from __future__ import annotations

from dataclasses import dataclass

from scidoc_core.config import Settings
from scidoc_engines.registry import EngineRegistry
from scidoc_routing.policy import RoutingPolicy


@dataclass(slots=True)
class PipelineContext:
    document_id: str
    settings: Settings
    registry: EngineRegistry
    routing_policy: RoutingPolicy
