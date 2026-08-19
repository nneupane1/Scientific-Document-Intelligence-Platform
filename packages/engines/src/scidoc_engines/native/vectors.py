from __future__ import annotations

from scidoc_core.region import Region


def vector_payload(region: Region) -> dict[str, object]:
    return {"bbox": region.bbox.as_list(), "metadata": region.metadata}
