from scidoc_storage.cache import cache_key


def test_cache_key_is_deterministic_and_version_sensitive() -> None:
    first = cache_key(b"pixels", engine_name="ocr", model_version="1", options={"dpi": 300})
    second = cache_key(b"pixels", engine_name="ocr", model_version="1", options={"dpi": 300})
    changed = cache_key(b"pixels", engine_name="ocr", model_version="2", options={"dpi": 300})
    assert first == second
    assert first != changed
    assert len(first) == 64
