from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from scidoc_database.models import Document


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_id(self, document_id: str, *, related: bool = False) -> Document | None:
        statement = select(Document).where(Document.id == document_id)
        if related:
            statement = statement.options(selectinload(Document.pages), selectinload(Document.jobs))
        return self.session.scalar(statement)

    def by_hash(self, sha256: str) -> Document | None:
        return self.session.scalar(select(Document).where(Document.sha256 == sha256))

    def list(self, *, limit: int = 100, offset: int = 0) -> list[Document]:
        statement = (
            select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
        )
        return list(self.session.scalars(statement))

    def add(self, document: Document) -> Document:
        self.session.add(document)
        self.session.flush()
        return document
