from __future__ import annotations

from fastapi import APIRouter, Depends
from scidoc_core.config import Settings
from scidoc_engines.registry import default_registry

from scidoc_api.dependencies.settings import app_settings

router = APIRouter(tags=["capabilities"])


@router.get("/api/capabilities")
def runtime_capabilities(settings: Settings = Depends(app_settings)) -> dict[str, object]:
    """Return a truthful, read-only view of the intelligence available in this runtime."""
    engines = default_registry().statuses()
    vlm_adapter_configured = any(
        bool(engine["available"]) and "vlm" in engine["capabilities"] for engine in engines
    )
    return {
        "pipeline_version": settings.pipeline_version,
        "schema_version": settings.sdr_schema_version,
        "processing_mode": "local-first",
        "queue_mode": settings.queue_mode,
        "deterministic_core": True,
        "llm_in_evidence_path": False,
        "vlm_policy_enabled": settings.enable_vlm,
        "vlm_adapter_configured": vlm_adapter_configured,
        "feature_flags": {
            "tables": settings.enable_tables,
            "chemistry": settings.enable_chemistry,
            "diagrams": settings.enable_diagrams,
            "charts": settings.enable_charts,
            "vlm_escalation": settings.enable_vlm,
            "high_dpi_retry": settings.enable_high_dpi_retry,
        },
        "engines": engines,
    }
