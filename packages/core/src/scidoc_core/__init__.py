"""Shared primitives for the scientific document pipeline."""

from scidoc_core.bbox import BBox
from scidoc_core.confidence import ConfidenceState
from scidoc_core.config import Settings, get_settings
from scidoc_core.provenance import Provenance, ProvenanceEvent

__all__ = ["BBox", "ConfidenceState", "Provenance", "ProvenanceEvent", "Settings", "get_settings"]
