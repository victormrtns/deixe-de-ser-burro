from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (
        CheckConstraint("reading_minutes >= 1", name="reading_minutes"),
        CheckConstraint("state IN ('published', 'withdrawn')", name="state"),
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_canonical"),
        CheckConstraint("book_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="book_slug_canonical"),
        CheckConstraint("cleanup_due_at >= published_at", name="cleanup_after_publish"),
        ForeignKeyConstraint(
            ["writing_id", "writing_version_id"],
            ["writing_versions.writing_id", "writing_versions.id"],
            name="fk_publications_writing_version_pair",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    writing_id: Mapped[UUID] = mapped_column(
        ForeignKey("writings.id", name="fk_publications_writing_id", ondelete="CASCADE")
    )
    writing_version_id: Mapped[UUID] = mapped_column(index=True)
    slug: Mapped[str] = mapped_column(String(250))
    title: Mapped[str] = mapped_column(String(500))
    markdown: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text)
    reading_minutes: Mapped[int] = mapped_column(Integer)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    book_slug: Mapped[str] = mapped_column(String(250))
    book_title: Mapped[str] = mapped_column(String(500))
    book_author: Mapped[str] = mapped_column(String(500))
    public_cover_path: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32), default="published", server_default="published")
    cleanup_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cleanup_cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleanup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicationTopic(Base):
    __tablename__ = "publication_topics"
    __table_args__ = (
        CheckConstraint("char_length(btrim(topic)) > 0", name="not_blank"),
        CheckConstraint("position >= 0", name="position"),
        UniqueConstraint("publication_id", "topic", name="uq_publication_topics_publication_topic"),
        UniqueConstraint(
            "publication_id", "position", name="uq_publication_topics_publication_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    publication_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "publications.id",
            name="fk_publication_topics_publication_id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)


class EditorialSettings(Base):
    __tablename__ = "editorial_settings"
    __table_args__ = (
        CheckConstraint("singleton_key", name="singleton_key"),
        UniqueConstraint("singleton_key", name="uq_editorial_settings_singleton_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    singleton_key: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    featured_publication_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "publications.id",
            name="fk_editorial_settings_featured_publication_id",
            ondelete="SET NULL",
        ),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
