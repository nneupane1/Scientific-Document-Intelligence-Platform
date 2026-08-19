from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, cast

from scidoc_core.errors import StorageSecurityError

from scidoc_storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, key: str) -> Path:
        if Path(key).is_absolute():
            raise StorageSecurityError("storage keys must be relative")
        target = (self.root / key).resolve()
        if target != self.root and self.root not in target.parents:
            raise StorageSecurityError("storage key escapes configured root")
        return target

    def put(self, key: str, source: str | Path | bytes) -> Path:
        destination = self.resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, bytes):
            destination.write_bytes(source)
        else:
            source_path = Path(source).resolve()
            if source_path != destination:
                shutil.copyfile(source_path, destination)
        return destination

    def get(self, key: str) -> bytes:
        return self.resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self.resolve(key).exists()

    def delete(self, key: str) -> bool:
        target = self.resolve(key)
        if not target.exists():
            return False
        if target.is_dir():
            raise StorageSecurityError("directory deletion is not supported")
        target.unlink()
        return True

    def open(self, key: str, mode: str = "rb") -> BinaryIO:
        if mode not in {"rb", "wb", "ab", "xb"}:
            raise ValueError("LocalStorage only exposes binary modes")
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        return cast(BinaryIO, target.open(mode))
