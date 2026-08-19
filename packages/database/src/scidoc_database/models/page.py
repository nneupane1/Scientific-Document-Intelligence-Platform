from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scidoc_database.models.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from scidoc_database.models.document import Document
    from scidoc_database.models.element import Element


class Page(TimestampMixin, Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_pages_document_page"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    rendered_path: Mapped[str | None] = mapped_column(String(1024))
    result_path: Mapped[str | None] = mapped_column(String(1024))
    inspection: Mapped[dict[str, object]] = mapped_column(JSONType, default=dict, nullable=False)

    document: Mapped[Document] = relationship(back_populates="pages")
    elements: Mapped[list[Element]] = relationship(
        back_populates="page", cascade="all, delete-orphan", order_by="Element.reading_order"
    )
