from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(
    content: bytes,
    *,
    engine_name: str,
    model_version: str,
    preprocessing: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    digest = hashlib.sha256()
    digest.update(content)
    metadata = {
        "engine": engine_name,
        "model_version": model_version,
        "preprocessing": preprocessing or {},
        "options": options or {},
    }
    digest.update(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode())
    return digest.hexdigest()


class FileCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
            raise ValueError("cache key must be a SHA-256 hexadecimal digest")
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> bytes | None:
        path = self.path(key)
        return path.read_bytes() if path.exists() else None

    def put(self, key: str, value: bytes) -> Path:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path
