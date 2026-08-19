from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scidoc_database.models.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from scidoc_database.models.page import Page


class Element(TimestampMixin, Base):
    __tablename__ = "elements"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    page_id: Mapped[str] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    element_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    bbox: Mapped[list[float]] = mapped_column(JSONType, nullable=False)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSONType, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    confidence_source: Mapped[str] = mapped_column(
        String(80), default="unavailable", nullable=False
    )
    provenance: Mapped[dict[str, object]] = mapped_column(JSONType, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(30), default="uncertain", nullable=False, index=True
    )
    warnings: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    page: Mapped[Page] = relationship(back_populates="elements")
