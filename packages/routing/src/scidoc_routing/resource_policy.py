from dataclasses import dataclass

from scidoc_engines.device import resolve_device


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    device: str = "auto"

    def resolved_device(self) -> str:
        return resolve_device(self.device)
