def recognize_reaction(*, enabled: bool) -> dict[str, object]:
    if not enabled:
        return {"status": "disabled"}
    raise NotImplementedError("chemical reaction recognition is reserved for V3")
