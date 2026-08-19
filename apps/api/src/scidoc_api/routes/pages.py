from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from scidoc_core.config import Settings
from scidoc_database.models import Job, Page
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from scidoc_api.dependencies.database import get_db
from scidoc_api.dependencies.settings import app_settings
from scidoc_api.schemas import PageDetail, PageResponse, ProcessResponse
from scidoc_api.services import dispatch_processing

router = APIRouter(tags=["pages"])


@router.get("/api/documents/{document_id}/pages", response_model=list[PageResponse])
def list_pages(document_id: str, session: Session = Depends(get_db)) -> list[PageResponse]:
    pages = list(
        session.scalars(
            select(Page).where(Page.document_id == document_id).order_by(Page.page_number)
        )
    )
    return [PageResponse.model_validate(page) for page in pages]


@router.get("/api/documents/{document_id}/pages/{page_number}", response_model=PageDetail)
def get_page(document_id: str, page_number: int, session: Session = Depends(get_db)) -> PageDetail:
    page = session.scalar(
        select(Page)
        .options(selectinload(Page.elements))
        .where(Page.document_id == document_id, Page.page_number == page_number)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="page not found or not processed yet")
    return PageDetail.model_validate(page)


@router.post("/api/pages/{page_id}/reprocess", response_model=ProcessResponse, status_code=202)
def reprocess_page(
    page_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> ProcessResponse:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="page not found")
    job = Job(
        id=f"job_{uuid.uuid4().hex[:16]}",
        document_id=page.document_id,
        job_type="page_reprocess",
        pages_total=page.document.page_count,
        details={"page_number": page.page_number},
    )
    session.add(job)
    session.commit()
    dispatch_processing(page.document_id, job.id, settings, background_tasks, {page.page_number})
    return ProcessResponse(document_id=page.document_id, job_id=job.id)
