from pathlib import Path

import pytest
from scidoc_core.errors import StorageSecurityError
from scidoc_storage.local import LocalStorage
from scidoc_storage.paths import DocumentPaths


def test_storage_paths_are_deterministic(tmp_path: Path) -> None:
    paths = DocumentPaths("doc_123")
    assert paths.original == "documents/doc_123/original/document.pdf"
    assert paths.page_result(7).endswith("page_0007.json")
    storage = LocalStorage(tmp_path)
    target = storage.put(paths.original, b"%PDF-test")
    assert target.read_bytes() == b"%PDF-test"


def test_storage_blocks_traversal(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    with pytest.raises(StorageSecurityError):
        storage.resolve("../outside")
