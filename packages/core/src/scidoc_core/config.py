from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with environment-variable overrides."""

    model_config = SettingsConfigDict(
        env_prefix="SCIDOC_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
        env_ignore_empty=True,
    )

    environment: str = "local"
    database_url: str = "sqlite:///./data/scidoc.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: Path = Path("./data")
    queue_mode: Literal["background", "dramatiq", "synchronous"] = "background"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    max_upload_mb: int = Field(default=250, ge=1, le=2048)
    log_level: str = "INFO"
    default_dpi: int = Field(default=300, ge=72, le=600)
    escalation_dpi: int = Field(default=450, ge=72, le=600)
    max_dpi: int = Field(default=600, ge=72, le=1200)
    native_acceptance: float = Field(default=0.99, ge=0, le=1)
    ocr_acceptance: float = Field(default=0.97, ge=0, le=1)
    formula_acceptance: float = Field(default=0.97, ge=0, le=1)
    native_min_characters: int = Field(default=8, ge=1)
    enable_high_dpi_retry: bool = True
    enable_large_formula_engine: bool = False
    enable_tables: bool = True
    enable_chemistry: bool = True
    enable_diagrams: bool = True
    enable_charts: bool = True
    enable_vlm: bool = True
    narration_provider: Literal["auto", "kokoro", "macos", "openai"] = "auto"
    narration_local_model: Path = Path("./data/models/narration/kokoro-v1.0.onnx")
    narration_local_voices: Path = Path("./data/models/narration/voices-v1.0.bin")
    narration_local_default_voice: Literal["af_heart", "af_bella", "af_nicole", "bf_emma"] = (
        "af_heart"
    )
    narration_local_speed: float = Field(default=0.95, ge=0.5, le=2.0)
    narration_macos_default_voice: Literal[
        "samantha", "daniel", "karen", "moira", "rishi", "tessa"
    ] = "samantha"
    narration_macos_rate: int = Field(default=185, ge=100, le=300)
    narration_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SCIDOC_NARRATION_API_KEY", "OPENAI_API_KEY"),
        exclude=True,
    )
    narration_api_base: str = Field(default="https://api.openai.com/v1", exclude=True)
    narration_model: str = Field(default="gpt-4o-mini-tts", exclude=True)
    narration_default_voice: Literal[
        "alloy",
        "ash",
        "ballad",
        "coral",
        "echo",
        "fable",
        "nova",
        "onyx",
        "sage",
        "shimmer",
        "verse",
        "marin",
        "cedar",
    ] = Field(default="marin", exclude=True)
    narration_timeout_seconds: float = Field(default=90, ge=10, le=300, exclude=True)
    pipeline_version: str = "0.2.0"
    sdr_schema_version: str = "0.1.0"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def config_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load YAML and expand ${VARIABLE} strings recursively."""

    def expand(value: Any) -> Any:
        if isinstance(value, str):
            return os.path.expandvars(value)
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            return {key: expand(item) for key, item in value.items()}
        return value

    with Path(path).open(encoding="utf-8") as handle:
        return cast(dict[str, Any], expand(yaml.safe_load(handle) or {}))
