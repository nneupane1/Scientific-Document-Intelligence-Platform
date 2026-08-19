def extract_relationships(*, enabled: bool) -> list[object]:
    if not enabled:
        return []
    raise NotImplementedError("diagram relationships are reserved for V4")
