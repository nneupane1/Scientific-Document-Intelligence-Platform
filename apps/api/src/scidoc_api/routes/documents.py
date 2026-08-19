from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from scidoc_core.config import Settings
from scidoc_core.document import sanitize_filename
from scidoc_core.errors import InvalidPdfError
from scidoc_database.models import Document, Job
from scidoc_database.repositories import DocumentRepository, JobRepository
from scidoc_pipeline.document_pipeline import DocumentPipeline
from scidoc_schema.models import SdrDocument
from sqlalchemy import select
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.dependencies.settings import app_settings
from scidoc_api.schemas import DocumentSummary, JobResponse, ProcessResponse, UploadResponse
from scidoc_api.services import dispatch_processing

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _job_response(job: Job | None) -> JobResponse | None:
    return JobResponse.model_validate(job) if job else None


def _summary(document: Document, job: Job | None = None) -> DocumentSummary:
    processing: dict[str, object] | None = None
    if document.sdr_path and Path(document.sdr_path).exists():
        sdr = SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())
        processing = sdr.processing.model_dump(mode="json")
    return DocumentSummary.model_validate(
        {
            **{
                key: getattr(document, key)
                for key in (
                    "id",
                    "filename",
                    "sha256",
                    "page_count",
                    "status",
                    "created_at",
                    "updated_at",
                )
            },
            "latest_job": _job_response(job),
            "summary": processing,
        }
    )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> UploadResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="only PDF uploads are accepted")
    safe_name = sanitize_filename(file.filename or "document.pdf")
    temp_dir = settings.storage_root / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="upload_", suffix=".pdf", dir=temp_dir, delete=False
        ) as handle:
            temp_path = Path(handle.name)
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413, detail=f"PDF exceeds {settings.max_upload_mb} MB limit"
                    )
                handle.write(chunk)
        pipeline = DocumentPipeline(session, settings)
        result = pipeline.ingest(temp_path, original_filename=safe_name)
        job = session.get(Job, result.job_id)
        if not result.duplicate or (job and job.status not in {"completed", "running"}):
            dispatch_processing(result.document_id, result.job_id, settings, background_tasks)
        return UploadResponse(
            document_id=result.document_id,
            job_id=result.job_id,
            duplicate=result.duplicate,
            status=job.status if job else "queued",
        )
    except InvalidPdfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
) -> list[DocumentSummary]:
    documents = DocumentRepository(session).list(limit=limit, offset=offset)
    jobs = JobRepository(session)
    return [_summary(document, jobs.latest_for_document(document.id)) for document in documents]


@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, session: Session = Depends(get_db)) -> DocumentSummary:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return _summary(document, JobRepository(session).latest_for_document(document.id))


@router.get("/{document_id}/file", response_class=FileResponse)
def document_file(document_id: str, session: Session = Depends(get_db)) -> FileResponse:
    document = session.get(Document, document_id)
    if document is None or not Path(document.source_path).exists():
        raise HTTPException(status_code=404, detail="source PDF not found")
    return FileResponse(
        document.source_path, media_type="application/pdf", filename=document.filename
    )


@router.get("/{document_id}/sdr", response_model=SdrDocument)
def document_sdr(document_id: str, session: Session = Depends(get_db)) -> SdrDocument:
    document = session.get(Document, document_id)
    if document is None or not document.sdr_path or not Path(document.sdr_path).exists():
        raise HTTPException(status_code=404, detail="SDR is not available yet")
    return SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes())


@router.post("/{document_id}/process", response_model=ProcessResponse, status_code=202)
def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> ProcessResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    active = session.scalar(
        select(Job)
        .where(Job.document_id == document_id, Job.status.in_(["queued", "running"]))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    if active:
        return ProcessResponse(document_id=document_id, job_id=active.id, status=active.status)
    job = Job(
        id=f"job_{uuid.uuid4().hex[:16]}",
        document_id=document_id,
        job_type="document_process",
        pages_total=document.page_count,
    )
    session.add(job)
    session.commit()
    dispatch_processing(document_id, job.id, settings, background_tasks)
    return ProcessResponse(document_id=document_id, job_id=job.id)
