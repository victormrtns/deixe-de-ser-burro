"""Persist the contextual AI conversation: messages, attempts, memory, and usage.

Revision ID: 0002_contextual_ai_conversation
Revises: 0001_initial
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_contextual_ai_conversation"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("writing_id", UUID, nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["writing_id"],
            ["writings.id"],
            name="fk_conversations_writing_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.UniqueConstraint("writing_id", name="uq_conversations_writing_id"),
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", UUID, nullable=False),
        sa.Column("conversation_id", UUID, nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('author', 'assistant')", name="role"),
        sa.CheckConstraint(
            "state IN ('streaming', 'completed', 'interrupted', 'failed')", name="state"
        ),
        sa.CheckConstraint(
            "role <> 'author' OR char_length(btrim(content)) > 0", name="author_content_not_blank"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_messages_conversation_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversation_messages"),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"]
    )
    op.create_index(
        "ix_conversation_messages_history",
        "conversation_messages",
        ["conversation_id", "created_at", "id"],
    )

    op.create_table(
        "generation_attempts",
        sa.Column("id", UUID, nullable=False),
        sa.Column("author_message_id", UUID, nullable=False),
        sa.Column("assistant_message_id", UUID, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("instruction_version", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd_micros", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("safe_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("finished_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "state IN ('pending', 'streaming', 'completed', 'interrupted', 'failed')", name="state"
        ),
        sa.CheckConstraint("attempt_number >= 1", name="attempt_number_positive"),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0",
            name="tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "estimated_cost_usd_micros >= 0 AND (latency_ms IS NULL OR latency_ms >= 0)",
            name="cost_and_latency_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["author_message_id"],
            ["conversation_messages.id"],
            name="fk_generation_attempts_author_message_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["conversation_messages.id"],
            name="fk_generation_attempts_assistant_message_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generation_attempts"),
        sa.UniqueConstraint(
            "author_message_id",
            "attempt_number",
            name="uq_generation_attempts_author_message_id_attempt_number",
        ),
    )
    op.create_index(
        "ix_generation_attempts_author_message_id", "generation_attempts", ["author_message_id"]
    )
    op.create_index(
        "ix_generation_attempts_assistant_message_id",
        "generation_attempts",
        ["assistant_message_id"],
    )

    op.create_table(
        "writing_memory_items",
        sa.Column("id", UUID, nullable=False),
        sa.Column("writing_id", UUID, nullable=False),
        sa.Column("source_message_id", UUID, nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("superseded_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint("kind IN ('preference', 'decision', 'open_question')", name="kind"),
        sa.CheckConstraint("char_length(btrim(content)) > 0", name="content_not_blank"),
        sa.ForeignKeyConstraint(
            ["writing_id"],
            ["writings.id"],
            name="fk_writing_memory_items_writing_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["conversation_messages.id"],
            name="fk_writing_memory_items_source_message_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_writing_memory_items"),
    )
    op.create_index("ix_writing_memory_items_writing_id", "writing_memory_items", ["writing_id"])
    op.create_index(
        "ix_writing_memory_items_source_message_id", "writing_memory_items", ["source_message_id"]
    )
    op.create_index(
        "ix_writing_memory_items_active",
        "writing_memory_items",
        ["writing_id", "created_at"],
        postgresql_where=sa.text("active"),
    )

    op.create_table(
        "ai_usage_entries",
        sa.Column("id", UUID, nullable=False),
        sa.Column("writing_id", UUID, nullable=False),
        sa.Column("generation_attempt_id", UUID, nullable=False),
        sa.Column("state", sa.String(length=16), server_default="reserved", nullable=False),
        sa.Column("reserved_usd_micros", sa.Integer(), server_default="0", nullable=False),
        sa.Column("actual_usd_micros", sa.Integer(), nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("settled_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint("state IN ('reserved', 'settled', 'released')", name="state"),
        sa.CheckConstraint(
            "reserved_usd_micros >= 0 AND (actual_usd_micros IS NULL OR actual_usd_micros >= 0)",
            name="micros_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["writing_id"],
            ["writings.id"],
            name="fk_ai_usage_entries_writing_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generation_attempt_id"],
            ["generation_attempts.id"],
            name="fk_ai_usage_entries_generation_attempt_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_usage_entries"),
        sa.UniqueConstraint(
            "generation_attempt_id", name="uq_ai_usage_entries_generation_attempt_id"
        ),
    )
    op.create_index("ix_ai_usage_entries_writing_id", "ai_usage_entries", ["writing_id"])
    op.create_index("ix_ai_usage_entries_created_at", "ai_usage_entries", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_usage_entries")
    op.drop_table("writing_memory_items")
    op.drop_table("generation_attempts")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
