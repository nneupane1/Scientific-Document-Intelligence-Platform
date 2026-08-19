from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scidoc_database.models.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from scidoc_database.models.document import Document


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    pages_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(80), default="queued", nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONType, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="jobs")
