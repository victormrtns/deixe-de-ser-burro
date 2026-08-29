from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599",
            name="response_status",
        ),
        UniqueConstraint(
            "author_id", "operation", "key", name="uq_idempotency_keys_author_operation_key"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "author_accounts.id",
            name="fk_idempotency_keys_author_id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(250))
    request_hash: Mapped[str] = mapped_column(String(128))
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    resource_id: Mapped[UUID | None] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
