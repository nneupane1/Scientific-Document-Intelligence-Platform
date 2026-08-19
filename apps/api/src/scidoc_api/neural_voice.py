from __future__ import annotations

import asyncio
import importlib.util
import io
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from functools import lru_cache
from pathlib import Path
from typing import Literal

import httpx
from scidoc_core.config import Settings

_MAX_INPUT_CHARACTERS = 3_600
_SAMPLE_RATE = 24_000
_SAMPLE_WIDTH_BYTES = 2
_CHANNELS = 1
_KOKORO_CHUNK_CHARACTERS = 900
_NARRATION_INSTRUCTIONS = (
    "Speak like an expert human audiobook narrator: warm, calm, natural, and easy to follow. "
    "Use measured pacing and brief pauses around headings, equations, table rows, and review "
    "warnings. Read the supplied words exactly. Do not paraphrase, correct, omit, or add content."
)

NarrationProvider = Literal["kokoro", "macos", "openai"]

KOKORO_VOICES = {
    "af_heart": "Heart — warm, natural American",
    "af_bella": "Bella — expressive American",
    "af_nicole": "Nicole — calm audiobook",
    "bf_emma": "Emma — polished British",
}
MACOS_VOICES = {
    "samantha": "Samantha — clear American",
    "daniel": "Daniel — clear British",
    "karen": "Karen — clear Australian",
    "moira": "Moira — clear Irish",
    "rishi": "Rishi — clear Indian English",
    "tessa": "Tessa — clear South African",
}
OPENAI_VOICES = {
    "marin": "Marin — warm and natural",
    "cedar": "Cedar — clear and grounded",
    "coral": "Coral — bright and conversational",
    "sage": "Sage — composed and precise",
    "ballad": "Ballad — expressive and measured",
    "alloy": "Alloy — balanced",
    "ash": "Ash — steady",
    "echo": "Echo — direct",
    "fable": "Fable — narrative",
    "nova": "Nova — energetic",
    "onyx": "Onyx — deep",
    "shimmer": "Shimmer — light",
    "verse": "Verse — versatile",
}

_KOKORO_LOCK = threading.Lock()


class NeuralVoiceError(RuntimeError):
    """A safe, user-facing failure from a narration provider."""


def kokoro_available(settings: Settings) -> bool:
    return (
        importlib.util.find_spec("kokoro_onnx") is not None
        and importlib.util.find_spec("soundfile") is not None
        and settings.narration_local_model.is_file()
        and settings.narration_local_voices.is_file()
    )


def macos_voice_available() -> bool:
    return shutil.which("say") is not None and shutil.which("afconvert") is not None


def active_narration_provider(settings: Settings) -> NarrationProvider | None:
    requested = settings.narration_provider
    if requested == "kokoro":
        return "kokoro" if kokoro_available(settings) else None
    if requested == "macos":
        return "macos" if macos_voice_available() else None
    if requested == "openai":
        return "openai" if settings.narration_api_key is not None else None
    if kokoro_available(settings):
        return "kokoro"
    if settings.narration_api_key is not None:
        return "openai"
    if macos_voice_available():
        return "macos"
    return None


def provider_voices(provider: NarrationProvider) -> dict[str, str]:
    if provider == "kokoro":
        return KOKORO_VOICES
    if provider == "macos":
        return MACOS_VOICES
    return OPENAI_VOICES


def provider_default_voice(provider: NarrationProvider, settings: Settings) -> str:
    if provider == "kokoro":
        return settings.narration_local_default_voice
    if provider == "macos":
        return settings.narration_macos_default_voice
    return settings.narration_default_voice


def provider_model(provider: NarrationProvider, settings: Settings) -> str:
    if provider == "kokoro":
        return "Kokoro-82M v1.0 (local ONNX)"
    if provider == "macos":
        return "macOS Speech Synthesis (local)"
    return settings.narration_model


def split_narration_script(script: str, limit: int = _MAX_INPUT_CHARACTERS) -> list[str]:
    """Split a long narration without cutting words or exceeding the provider request limit."""

    normalized = script.strip()
    if not normalized:
        return []
    units = [unit.strip() for unit in re.split(r"(?<=[.!?])\s+|\n+", normalized) if unit.strip()]
    chunks: list[str] = []
    current = ""

    def append_piece(piece: str) -> None:
        nonlocal current
        candidate = f"{current} {piece}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = piece
        else:
            current = candidate

    for unit in units:
        if len(unit) <= limit:
            append_piece(unit)
            continue
        words = unit.split()
        piece = ""
        for word in words:
            if len(word) > limit:
                raise NeuralVoiceError(
                    "Narration contains a token that is too long to speak safely."
                )
            candidate = f"{piece} {word}".strip()
            if piece and len(candidate) > limit:
                append_piece(piece)
                piece = word
            else:
                piece = candidate
        if piece:
            append_piece(piece)
    if current:
        chunks.append(current)
    return chunks


def pcm_to_wav(pcm: bytes) -> bytes:
    if not pcm or len(pcm) % _SAMPLE_WIDTH_BYTES:
        raise NeuralVoiceError("The voice service returned invalid audio.")
    destination = io.BytesIO()
    with wave.open(destination, "wb") as output:
        output.setnchannels(_CHANNELS)
        output.setsampwidth(_SAMPLE_WIDTH_BYTES)
        output.setframerate(_SAMPLE_RATE)
        output.writeframes(pcm)
    return destination.getvalue()


def _provider_error(response: httpx.Response) -> NeuralVoiceError:
    if response.status_code in {401, 403}:
        return NeuralVoiceError("The neural voice service rejected the server API key.")
    if response.status_code == 429:
        return NeuralVoiceError(
            "The neural voice service is rate-limited; please try again shortly."
        )
    if response.status_code >= 500:
        return NeuralVoiceError("The neural voice service is temporarily unavailable.")
    return NeuralVoiceError("The neural voice service could not generate this narration.")


async def synthesize_narration_wav(script: str, *, voice: str, settings: Settings) -> bytes:
    """Generate exact speech with the best configured local-first provider."""

    provider = active_narration_provider(settings)
    if provider is None:
        raise NeuralVoiceError("Natural narration is not configured on this server.")
    if voice not in provider_voices(provider):
        raise NeuralVoiceError(f"Voice {voice!r} is not available for the active provider.")
    if provider == "kokoro":
        return await asyncio.to_thread(_synthesize_kokoro_wav, script, voice, settings)
    if provider == "macos":
        return await asyncio.to_thread(_synthesize_macos_wav, script, voice, settings)
    return await _synthesize_openai_wav(script, voice, settings)


@lru_cache(maxsize=2)
def _load_kokoro(model_path: str, voices_path: str) -> object:
    from kokoro_onnx import Kokoro

    return Kokoro(model_path, voices_path)


def _synthesize_kokoro_wav(script: str, voice: str, settings: Settings) -> bytes:
    chunks = split_narration_script(script, limit=_KOKORO_CHUNK_CHARACTERS)
    if not chunks:
        raise NeuralVoiceError("There is no recovered text to narrate.")
    try:
        import numpy as np
        import soundfile as sf

        with _KOKORO_LOCK:
            engine = _load_kokoro(
                str(settings.narration_local_model.resolve()),
                str(settings.narration_local_voices.resolve()),
            )
            audio_parts = []
            sample_rate = _SAMPLE_RATE
            for chunk in chunks:
                samples, sample_rate = engine.create(  # type: ignore[attr-defined]
                    chunk,
                    voice=voice,
                    speed=settings.narration_local_speed,
                    lang="en-us" if not voice.startswith("b") else "en-gb",
                )
                audio_parts.append(np.asarray(samples, dtype=np.float32).reshape(-1))
        if not audio_parts or sample_rate != _SAMPLE_RATE:
            raise NeuralVoiceError("The local neural voice returned invalid audio.")
        pause = np.zeros(int(sample_rate * 0.14), dtype=np.float32)
        combined_parts = []
        for index, part in enumerate(audio_parts):
            if index:
                combined_parts.append(pause)
            combined_parts.append(part)
        destination = io.BytesIO()
        sf.write(
            destination,
            np.concatenate(combined_parts),
            sample_rate,
            format="WAV",
            subtype="PCM_16",
        )
        return destination.getvalue()
    except NeuralVoiceError:
        raise
    except Exception as exc:
        raise NeuralVoiceError("The local Kokoro voice could not generate narration.") from exc


def _synthesize_macos_wav(script: str, voice: str, settings: Settings) -> bytes:
    if not script.strip():
        raise NeuralVoiceError("There is no recovered text to narrate.")
    system_voice = MACOS_VOICES.get(voice)
    if system_voice is None:
        raise NeuralVoiceError("The selected macOS voice is unavailable.")
    say_voice = system_voice.split(" —", maxsplit=1)[0]
    try:
        with tempfile.TemporaryDirectory(prefix="scidoc-narration-") as directory:
            aiff_path = Path(directory) / "narration.aiff"
            wav_path = Path(directory) / "narration.wav"
            spoken = subprocess.run(
                [
                    "say",
                    "-v",
                    say_voice,
                    "-r",
                    str(settings.narration_macos_rate),
                    "-o",
                    str(aiff_path),
                ],
                input=script,
                capture_output=True,
                check=False,
                text=True,
                timeout=settings.narration_timeout_seconds,
            )
            if spoken.returncode != 0 or not aiff_path.is_file():
                raise NeuralVoiceError("The local macOS voice could not generate narration.")
            converted = subprocess.run(
                [
                    "afconvert",
                    "-f",
                    "WAVE",
                    "-d",
                    "LEI16@24000",
                    str(aiff_path),
                    str(wav_path),
                ],
                capture_output=True,
                check=False,
                timeout=settings.narration_timeout_seconds,
            )
            if converted.returncode != 0 or not wav_path.is_file():
                raise NeuralVoiceError("The local macOS voice returned invalid audio.")
            return wav_path.read_bytes()
    except NeuralVoiceError:
        raise
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NeuralVoiceError("The local macOS voice is temporarily unavailable.") from exc


async def _synthesize_openai_wav(script: str, voice: str, settings: Settings) -> bytes:
    if settings.narration_api_key is None:
        raise NeuralVoiceError("The OpenAI narration provider has no server API key.")
    chunks = split_narration_script(script)
    if not chunks:
        raise NeuralVoiceError("There is no recovered text to narrate.")

    headers = {
        "Authorization": f"Bearer {settings.narration_api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }
    pcm_parts: list[bytes] = []
    timeout = httpx.Timeout(settings.narration_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for chunk in chunks:
                response = await client.post(
                    f"{settings.narration_api_base.rstrip('/')}/audio/speech",
                    headers=headers,
                    json={
                        "model": settings.narration_model,
                        "voice": voice,
                        "input": chunk,
                        "instructions": _NARRATION_INSTRUCTIONS,
                        "response_format": "pcm",
                    },
                )
                if not response.is_success:
                    raise _provider_error(response)
                pcm_parts.append(response.content)
    except NeuralVoiceError:
        raise
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise NeuralVoiceError("The server could not reach the neural voice service.") from exc

    return pcm_to_wav(b"".join(pcm_parts))
