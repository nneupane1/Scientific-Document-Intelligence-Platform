from __future__ import annotations

import importlib.util
from typing import Literal

Device = Literal["cuda", "mps", "cpu"]


def resolve_device(requested: str = "auto") -> Device:
    if requested in {"cuda", "mps", "cpu"}:
        return requested  # type: ignore[return-value]
    if requested != "auto":
        raise ValueError("device must be auto, cuda, mps, or cpu")
    if importlib.util.find_spec("torch"):
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    return "cpu"
