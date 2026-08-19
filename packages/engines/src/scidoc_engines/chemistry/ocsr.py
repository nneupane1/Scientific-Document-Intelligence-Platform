def recognize_molecule(*, enabled: bool) -> dict[str, object]:
    if not enabled:
        return {"status": "disabled"}
    raise NotImplementedError("OCSR is reserved for V3")
