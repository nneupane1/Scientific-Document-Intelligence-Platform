def classify_diagram(*, enabled: bool) -> dict[str, object]:
    if not enabled:
        return {"status": "disabled"}
    raise NotImplementedError("diagram semantics are reserved for V4")
