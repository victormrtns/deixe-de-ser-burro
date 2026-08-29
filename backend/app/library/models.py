from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("char_length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint("char_length(btrim(author)) > 0", name="author_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(500))
    private_cover_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
