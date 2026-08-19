from __future__ import annotations

from pathlib import Path

from scidoc_schema.models import SdrDocument


def export_json(sdr: SdrDocument, destination: str | Path) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(sdr.model_dump_json(indent=2), encoding="utf-8")
    return output
