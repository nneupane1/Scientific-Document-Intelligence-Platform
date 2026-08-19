from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scidoc_database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from scidoc_database.models.job import Job
    from scidoc_database.models.page import Page
    from scidoc_database.models.run import ProcessingRun


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_sha256", "sha256", unique=True),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sdr_path: Mapped[str | None] = mapped_column(String(1024))

    pages: Mapped[list[Page]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Page.page_number"
    )
    jobs: Mapped[list[Job]] = relationship(back_populates="document", cascade="all, delete-orphan")
    runs: Mapped[list[ProcessingRun]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
