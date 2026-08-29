from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Writing(Base):
    __tablename__ = "writings"
    __table_args__ = (
        CheckConstraint("char_length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint("version_number >= 1", name="version_positive"),
        CheckConstraint(
            "status IN ('draft', 'cleanup_scheduled', 'published')",
            name="status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", name="fk_writings_book_id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500))
    source_range: Mapped[str] = mapped_column(Text)
    markdown: Mapped[str] = mapped_column(Text)
    version_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WritingVersion(Base):
    __tablename__ = "writing_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="version_positive"),
        CheckConstraint(
            "reason IN ('created', 'manual_save', 'restored', 'published')",
            name="reason",
        ),
        UniqueConstraint(
            "writing_id", "version_number", name="uq_writing_versions_writing_version"
        ),
        UniqueConstraint("writing_id", "id", name="uq_writing_versions_writing_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    writing_id: Mapped[UUID] = mapped_column(
        ForeignKey("writings.id", name="fk_writing_versions_writing_id", ondelete="CASCADE"),
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer)
    markdown: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500))
    source_range: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
