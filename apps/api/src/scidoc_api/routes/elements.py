from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from scidoc_core.config import Settings
from scidoc_database.models import Element, Page
from sqlalchemy import select
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.dependencies.settings import app_settings
from scidoc_api.routes.pages import reprocess_page
from scidoc_api.schemas import ElementResponse, ProcessResponse

router = APIRouter(tags=["elements"])


@router.get("/api/documents/{document_id}/elements", response_model=list[ElementResponse])
def list_elements(
    document_id: str,
    element_type: str | None = Query(None),
    review_status: str | None = Query(None),
    session: Session = Depends(get_db),
) -> list[ElementResponse]:
    statement = select(Element).join(Page).where(Page.document_id == document_id)
    if element_type:
        statement = statement.where(Element.element_type == element_type)
    if review_status:
        statement = statement.where(Element.review_status == review_status)
    statement = statement.order_by(Page.page_number, Element.reading_order)
    return [ElementResponse.model_validate(element) for element in session.scalars(statement)]


@router.get("/api/elements/{element_id}", response_model=ElementResponse)
def get_element(element_id: str, session: Session = Depends(get_db)) -> ElementResponse:
    element = session.get(Element, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="element not found")
    return ElementResponse.model_validate(element)


@router.post(
    "/api/elements/{element_id}/reprocess", response_model=ProcessResponse, status_code=202
)
def reprocess_element(
    element_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    settings: Settings = Depends(app_settings),
) -> ProcessResponse:
    element = session.get(Element, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="element not found")
    return reprocess_page(element.page_id, background_tasks, session, settings)
