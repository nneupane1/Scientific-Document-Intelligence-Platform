from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scidoc_database.models.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from scidoc_database.models.document import Document


class ProcessingRun(TimestampMixin, Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    git_commit: Mapped[str | None] = mapped_column(String(64))
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_versions: Mapped[dict[str, str]] = mapped_column(JSONType, default=dict, nullable=False)
    statistics: Mapped[dict[str, object]] = mapped_column(JSONType, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="runs")
