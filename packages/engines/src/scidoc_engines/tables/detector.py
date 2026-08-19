def detect_tables(*, enabled: bool) -> list[object]:
    if not enabled:
        return []
    raise NotImplementedError("table detection is reserved for V2")
