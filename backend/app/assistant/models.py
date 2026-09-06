from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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

# FK targets must be registered in the shared metadata before use.
import app.writings.models  # noqa: F401
from app.models import Base

MESSAGE_ROLES = ("author", "assistant")
MESSAGE_STATES = ("streaming", "completed", "interrupted", "failed")
ATTEMPT_STATES = ("pending", "streaming", "completed", "interrupted", "failed")
MEMORY_KINDS = ("preference", "decision", "open_question")
USAGE_STATES = ("reserved", "settled", "released")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Conversation(Base):
    """The single primary conversation of a writing."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    writing_id: Mapped[UUID] = mapped_column(
        ForeignKey("writings.id", name="fk_conversations_writing_id", ondelete="CASCADE"),
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversationMessage(Base):
    """Visible content of the conversation, from the author or the assistant."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint(_in_list("role", MESSAGE_ROLES), name="role"),
        CheckConstraint(_in_list("state", MESSAGE_STATES), name="state"),
        # An assistant message starts empty and fills in while streaming; an
        # author message is only ever persisted with its final content.
        CheckConstraint(
            "role <> 'author' OR char_length(btrim(content)) > 0", name="author_content_not_blank"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conversations.id", name="fk_conversation_messages_conversation_id", ondelete="CASCADE"
        ),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, default="", server_default="")
    state: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GenerationAttempt(Base):
    """One potentially billable model call, auditable on its own."""

    __tablename__ = "generation_attempts"
    __table_args__ = (
        CheckConstraint(_in_list("state", ATTEMPT_STATES), name="state"),
        CheckConstraint("attempt_number >= 1", name="attempt_number_positive"),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0",
            name="tokens_nonnegative",
        ),
        CheckConstraint(
            "estimated_cost_usd_micros >= 0 AND (latency_ms IS NULL OR latency_ms >= 0)",
            name="cost_and_latency_nonnegative",
        ),
        UniqueConstraint(
            "author_message_id",
            "attempt_number",
            name="uq_generation_attempts_author_message_id_attempt_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_message_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conversation_messages.id",
            name="fk_generation_attempts_author_message_id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    assistant_message_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conversation_messages.id",
            name="fk_generation_attempts_assistant_message_id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    model: Mapped[str] = mapped_column(String(100))
    instruction_version: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    provider_response_id: Mapped[str | None] = mapped_column(String(200))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_cost_usd_micros: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    safe_error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WritingMemoryItem(Base):
    """Structured memory local to one writing, never shared across writings."""

    __tablename__ = "writing_memory_items"
    __table_args__ = (
        CheckConstraint(_in_list("kind", MEMORY_KINDS), name="kind"),
        CheckConstraint("char_length(btrim(content)) > 0", name="content_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    writing_id: Mapped[UUID] = mapped_column(
        ForeignKey("writings.id", name="fk_writing_memory_items_writing_id", ondelete="CASCADE"),
        index=True,
    )
    source_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conversation_messages.id",
            name="fk_writing_memory_items_source_message_id",
            ondelete="SET NULL",
        ),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiUsageEntry(Base):
    """Reserved and settled cost of one attempt, in integer USD micro-units."""

    __tablename__ = "ai_usage_entries"
    __table_args__ = (
        CheckConstraint(_in_list("state", USAGE_STATES), name="state"),
        CheckConstraint(
            "reserved_usd_micros >= 0 AND (actual_usd_micros IS NULL OR actual_usd_micros >= 0)",
            name="micros_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    writing_id: Mapped[UUID] = mapped_column(
        ForeignKey("writings.id", name="fk_ai_usage_entries_writing_id", ondelete="CASCADE"),
        index=True,
    )
    generation_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "generation_attempts.id",
            name="fk_ai_usage_entries_generation_attempt_id",
            ondelete="CASCADE",
        ),
        unique=True,
    )
    state: Mapped[str] = mapped_column(String(16), default="reserved", server_default="reserved")
    reserved_usd_micros: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    actual_usd_micros: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
