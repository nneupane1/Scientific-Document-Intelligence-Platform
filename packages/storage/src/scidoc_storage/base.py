from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, source: str | Path | bytes) -> Path:
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def open(self, key: str, mode: str = "rb") -> BinaryIO:
        pass
