from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from scidoc_core.config import Settings
from scidoc_database.models import Document
from scidoc_exporters.narration import NarrationTargetError, build_narration_script
from scidoc_schema.models import SdrDocument
from scidoc_storage.local import LocalStorage
from scidoc_storage.paths import DocumentPaths
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.dependencies.settings import app_settings
from scidoc_api.neural_voice import (
    NeuralVoiceError,
    active_narration_provider,
    provider_default_voice,
    provider_model,
    provider_voices,
    synthesize_narration_wav,
)
from scidoc_api.schemas import (
    NarrationCapabilities,
    NarrationRequest,
    NarrationVoiceOption,
)

router = APIRouter(tags=["narration"])

_REMOTE_PRIVACY_NOTICE = (
    "Only the recovered narration text is sent to OpenAI after you press Listen; the source PDF, "
    "page image, coordinates, and evidence metadata stay local."
)
_LOCAL_PRIVACY_NOTICE = (
    "Speech is generated locally on this Mac. No PDF content or narration text leaves the device."
)
_CACHE_VERSION = "natural-narration-v2"


@router.get("/api/narration/capabilities", response_model=NarrationCapabilities)
def narration_capabilities(settings: Settings = Depends(app_settings)) -> NarrationCapabilities:
    provider = active_narration_provider(settings)
    if provider is None:
        default_voice = (
            settings.narration_default_voice
            if settings.narration_provider == "openai"
            else settings.narration_local_default_voice
        )
        return NarrationCapabilities(
            configured=False,
            provider="unavailable",
            model="No narration engine available",
            default_voice=default_voice,
            voices=[],
            ai_generated=False,
            remote_processing=False,
            privacy_notice=(
                "Install the local Kokoro model, use macOS Speech, or configure OpenAI."
            ),
        )
    voices = [
        NarrationVoiceOption(
            id=voice,
            label=label,
            recommended=index < 2,
        )
        for index, (voice, label) in enumerate(provider_voices(provider).items())
    ]
    return NarrationCapabilities(
        configured=True,
        provider=provider,
        model=provider_model(provider, settings),
        default_voice=provider_default_voice(provider, settings),
        voices=voices,
        ai_generated=provider != "macos",
        remote_processing=provider == "openai",
        privacy_notice=_REMOTE_PRIVACY_NOTICE if provider == "openai" else _LOCAL_PRIVACY_NOTICE,
    )


def _load_sdr(document: Document) -> SdrDocument:
    if not document.sdr_path or not Path(document.sdr_path).exists():
        raise HTTPException(
            status_code=409, detail="document must finish processing before narration"
        )
    return SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".wav", delete=False) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.post("/api/documents/{document_id}/narration", response_class=FileResponse)
async def create_narration(
    document_id: str,
    request: NarrationRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> FileResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    provider = active_narration_provider(settings)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Natural narration needs the local Kokoro model, macOS Speech, or an OpenAI key."
            ),
        )

    sdr = _load_sdr(document)
    try:
        script = build_narration_script(
            sdr, page_number=request.page_number, element_id=request.element_id
        )
    except NarrationTargetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    voice = request.voice or provider_default_voice(provider, settings)
    if voice not in provider_voices(provider):
        raise HTTPException(status_code=422, detail="voice is unavailable for the active provider")
    model = provider_model(provider, settings)
    digest_source = "\x00".join((_CACHE_VERSION, provider, model, voice, script))
    digest = hashlib.sha256(digest_source.encode()).hexdigest()
    target = request.element_id or f"page-{request.page_number:04d}"
    try:
        destination = LocalStorage(settings.storage_root).resolve(
            DocumentPaths(document_id).narration(target, voice, digest)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="invalid narration target") from exc

    cache_status = "hit"
    if not destination.exists():
        cache_status = "miss"
        try:
            audio = await synthesize_narration_wav(script, voice=voice, settings=settings)
        except NeuralVoiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        _atomic_write(destination, audio)

    filename = f"{Path(document.filename).stem}-page-{request.page_number}-{voice}.wav"
    return FileResponse(
        destination,
        media_type="audio/wav",
        filename=filename,
        content_disposition_type="inline",
        headers={
            "X-SciDoc-AI-Generated": "true" if provider != "macos" else "false",
            "X-SciDoc-Narration-Cache": cache_status,
            "X-SciDoc-Narration-Provider": provider,
        },
    )
