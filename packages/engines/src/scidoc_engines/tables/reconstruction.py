def reconstruct_table(*, enabled: bool) -> dict[str, object]:
    if not enabled:
        return {"status": "disabled"}
    raise NotImplementedError("table reconstruction is reserved for V2")
