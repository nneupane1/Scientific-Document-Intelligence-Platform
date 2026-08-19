from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from scidoc_core.config import Settings
from scidoc_database.models import Document
from scidoc_exporters.service import export_sdr
from scidoc_schema.models import SdrDocument
from scidoc_storage.local import LocalStorage
from scidoc_storage.paths import DocumentPaths
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.dependencies.settings import app_settings
from scidoc_api.schemas import ExportRequest, ExportResponse

router = APIRouter(tags=["exports"])

_EXTENSIONS = {
    "json": "json",
    "html": "html",
    "markdown": "md",
    "latex": "tex",
    "searchable_pdf": "pdf",
}
_MEDIA = {
    "json": "application/json",
    "html": "text/html",
    "md": "text/markdown",
    "tex": "application/x-tex",
    "pdf": "application/pdf",
}


@router.post("/api/documents/{document_id}/export", response_model=ExportResponse)
def create_export(
    document_id: str,
    request: ExportRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> ExportResponse:
    document = session.get(Document, document_id)
    if document is None or not document.sdr_path or not Path(document.sdr_path).exists():
        raise HTTPException(status_code=409, detail="document must finish processing before export")
    sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
    extension = _EXTENSIONS[request.format]
    storage = LocalStorage(settings.storage_root)
    destination = storage.resolve(DocumentPaths(document_id).export(extension))
    export_sdr(sdr, destination, request.format, source_pdf=document.source_path)
    return ExportResponse(
        format=request.format, download_url=f"/api/documents/{document_id}/exports/{extension}"
    )


@router.get("/api/documents/{document_id}/exports/{extension}", response_class=FileResponse)
def download_export(
    document_id: str,
    extension: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> FileResponse:
    document = session.get(Document, document_id)
    if document is None or extension not in _MEDIA:
        raise HTTPException(status_code=404, detail="export not found")
    try:
        path = LocalStorage(settings.storage_root).resolve(
            DocumentPaths(document_id).export(extension)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="export not found") from exc
    if extension == "html" and document.sdr_path and Path(document.sdr_path).exists():
        sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
        export_sdr(sdr, path, "html", source_pdf=document.source_path)
    if extension == "pdf" and document.sdr_path and Path(document.sdr_path).exists():
        sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
        export_sdr(sdr, path, "searchable_pdf", source_pdf=document.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="export not found")
    filename = f"selectable-{Path(document.filename).stem}.pdf" if extension == "pdf" else path.name
    return FileResponse(
        path,
        media_type=_MEDIA[extension],
        filename=filename,
        content_disposition_type="inline" if extension in {"html", "pdf"} else "attachment",
    )
