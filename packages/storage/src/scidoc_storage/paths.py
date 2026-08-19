from __future__ import annotations

import re
from dataclasses import dataclass

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class DocumentPaths:
    document_id: str

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.document_id):
            raise ValueError("invalid document identifier")

    @property
    def root(self) -> str:
        return f"documents/{self.document_id}"

    @property
    def original(self) -> str:
        return f"{self.root}/original/document.pdf"

    def rendered_page(self, page_number: int, dpi: int = 300) -> str:
        return f"{self.root}/rendered/page_{page_number:04d}_{dpi}dpi.png"

    def region(self, page_number: int, region_id: str, dpi: int = 300) -> str:
        safe = "".join(
            character for character in region_id if character.isalnum() or character in "-_"
        )
        return f"{self.root}/regions/page_{page_number:04d}/region_{safe}_{dpi}dpi.png"

    def page_result(self, page_number: int) -> str:
        return f"{self.root}/results/pages/page_{page_number:04d}.json"

    @property
    def sdr(self) -> str:
        return f"{self.root}/results/document.sdr.json"

    def export(self, extension: str) -> str:
        safe = extension.lower().lstrip(".")
        if safe not in {"json", "html", "md", "tex", "pdf"}:
            raise ValueError("unsupported export extension")
        return f"{self.root}/exports/document.{safe}"

    def narration(self, target: str, voice: str, digest: str) -> str:
        safe_target = "".join(
            character for character in target if character.isalnum() or character in "-_"
        )
        safe_voice = "".join(
            character for character in voice if character.isalnum() or character in "-_"
        )
        safe_digest = "".join(character for character in digest if character in "0123456789abcdef")
        if not safe_target or not safe_voice or len(safe_digest) < 12:
            raise ValueError("invalid narration path component")
        return f"{self.root}/exports/narration/{safe_target}-{safe_voice}-{safe_digest[:16]}.wav"
