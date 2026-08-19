from scidoc_engines.vlm.base import LocalVlm


class DisabledLocalVlm(LocalVlm):
    def analyze(self, image_path: str, prompt: str) -> dict[str, object]:
        return {"status": "engine_unavailable", "reason": "local VLM feature flag is disabled"}
