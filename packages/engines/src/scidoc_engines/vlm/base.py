from abc import ABC, abstractmethod


class LocalVlm(ABC):
    @abstractmethod
    def analyze(self, image_path: str, prompt: str) -> dict[str, object]:
        pass
