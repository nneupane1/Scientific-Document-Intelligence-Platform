from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scidoc_database.models import Job


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_id(self, job_id: str) -> Job | None:
        return self.session.get(Job, job_id)

    def latest_for_document(self, document_id: str) -> Job | None:
        statement = (
            select(Job)
            .where(Job.document_id == document_id)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def add(self, job: Job) -> Job:
        self.session.add(job)
        self.session.flush()
        return job
