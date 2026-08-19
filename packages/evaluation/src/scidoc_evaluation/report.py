from __future__ import annotations

import json
from pathlib import Path


def write_report(payload: dict[str, object], destination: str | Path) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output
