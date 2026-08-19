from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from scidoc_database.models import Job
from scidoc_database.session import new_session
from sqlalchemy.orm import Session

from scidoc_api.dependencies.database import get_db
from scidoc_api.schemas import JobResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_db)) -> JobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse.model_validate(job)


@router.get("/{job_id}/events")
def job_events(job_id: str) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        previous = ""
        while True:
            with new_session() as session:
                job = session.get(Job, job_id)
                if job is None:
                    yield 'event: error\ndata: {"detail":"job not found"}\n\n'
                    return
                payload = JobResponse.model_validate(job).model_dump(mode="json")
            encoded = json.dumps(payload, separators=(",", ":"))
            if encoded != previous:
                yield f"event: progress\ndata: {encoded}\n\n"
                previous = encoded
            if payload["status"] in {"completed", "failed", "cancelled"}:
                return
            await asyncio.sleep(0.75)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
