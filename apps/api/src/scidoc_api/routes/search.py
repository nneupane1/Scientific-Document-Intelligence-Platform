from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from scidoc_database.models import Document
from scidoc_schema.models import SdrDocument
from scidoc_search.text import search_document
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.schemas import SearchResponse

router = APIRouter(tags=["search"])


@router.get("/api/documents/{document_id}/search", response_model=SearchResponse)
def search(
    document_id: str,
    q: str = Query(min_length=1, max_length=200),
    session: Session = Depends(get_db),
) -> SearchResponse:
    document = session.get(Document, document_id)
    if document is None or not document.sdr_path or not Path(document.sdr_path).exists():
        raise HTTPException(status_code=404, detail="processed SDR not found")
    hits = search_document(SdrDocument.model_validate_json(Path(document.sdr_path).read_bytes()), q)
    return SearchResponse(
        query=q, count=len(hits), hits=[hit.model_dump(mode="json") for hit in hits]
    )
