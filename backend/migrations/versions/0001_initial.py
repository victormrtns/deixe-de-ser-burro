"""Create the initial Entrelinhas schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "author_accounts",
        sa.Column("id", UUID, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "email = lower(btrim(email)) AND char_length(email) > 0",
            name="ck_author_accounts_email_normalized",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_author_accounts"),
        sa.UniqueConstraint("email", name="uq_author_accounts_email"),
    )
    op.create_index(
        "uq_author_accounts_single_active",
        "author_accounts",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "books",
        sa.Column("id", UUID, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=500), nullable=False),
        sa.Column("private_cover_path", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(btrim(title)) > 0", name="ck_books_title_not_blank"),
        sa.CheckConstraint("char_length(btrim(author)) > 0", name="ck_books_author_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_books"),
    )

    op.create_table(
        "author_sessions",
        sa.Column("id", UUID, nullable=False),
        sa.Column("author_id", UUID, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.Column("revoked_at", TIMESTAMP, nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["author_accounts.id"],
            name="fk_author_sessions_author_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_author_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_author_sessions_token_hash"),
    )
    op.create_index("ix_author_sessions_author_id", "author_sessions", ["author_id"])
    op.create_index("ix_author_sessions_expires_at", "author_sessions", ["expires_at"])

    op.create_table(
        "writings",
        sa.Column("id", UUID, nullable=False),
        sa.Column("book_id", UUID, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_range", sa.Text(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(btrim(title)) > 0", name="ck_writings_title_not_blank"),
        sa.CheckConstraint("version_number >= 1", name="ck_writings_version_positive"),
        sa.CheckConstraint(
            "status IN ('draft', 'cleanup_scheduled', 'published')",
            name="ck_writings_status",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name="fk_writings_book_id", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_writings"),
    )
    op.create_index("ix_writings_book_id", "writings", ["book_id"])

    op.create_table(
        "writing_versions",
        sa.Column("id", UUID, nullable=False),
        sa.Column("writing_id", UUID, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_range", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version_number >= 1", name="ck_writing_versions_version_positive"),
        sa.CheckConstraint(
            "reason IN ('created', 'manual_save', 'restored', 'published')",
            name="ck_writing_versions_reason",
        ),
        sa.ForeignKeyConstraint(
            ["writing_id"],
            ["writings.id"],
            name="fk_writing_versions_writing_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_writing_versions"),
        sa.UniqueConstraint(
            "writing_id", "version_number", name="uq_writing_versions_writing_version"
        ),
    )
    op.create_index("ix_writing_versions_writing_id", "writing_versions", ["writing_id"])

    op.create_table(
        "publications",
        sa.Column("id", UUID, nullable=False),
        sa.Column("writing_id", UUID, nullable=False),
        sa.Column("writing_version_id", UUID, nullable=False),
        sa.Column("slug", sa.String(length=250), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("reading_minutes", sa.Integer(), nullable=False),
        sa.Column("published_at", TIMESTAMP, nullable=False),
        sa.Column("book_slug", sa.String(length=250), nullable=False),
        sa.Column("book_title", sa.String(length=500), nullable=False),
        sa.Column("book_author", sa.String(length=500), nullable=False),
        sa.Column("public_cover_path", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=32), server_default="published", nullable=False),
        sa.Column("cleanup_due_at", TIMESTAMP, nullable=False),
        sa.Column("cleanup_cancelled_at", TIMESTAMP, nullable=True),
        sa.Column("cleanup_completed_at", TIMESTAMP, nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("reading_minutes >= 1", name="ck_publications_reading_minutes"),
        sa.CheckConstraint("state IN ('published', 'withdrawn')", name="ck_publications_state"),
        sa.CheckConstraint(
            "cleanup_due_at >= published_at", name="ck_publications_cleanup_after_publish"
        ),
        sa.ForeignKeyConstraint(
            ["writing_id"], ["writings.id"], name="fk_publications_writing_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["writing_version_id"],
            ["writing_versions.id"],
            name="fk_publications_writing_version_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publications"),
    )
    op.create_index("ix_publications_writing_id", "publications", ["writing_id"])
    op.create_index("ix_publications_writing_version_id", "publications", ["writing_version_id"])
    op.create_index("ix_publications_published_at", "publications", ["published_at"])
    op.create_index(
        "uq_publications_active_writing",
        "publications",
        ["writing_id"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
    )
    op.create_index(
        "uq_publications_active_slug",
        "publications",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
    )

    op.create_table(
        "publication_topics",
        sa.Column("id", UUID, nullable=False),
        sa.Column("publication_id", UUID, nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("char_length(btrim(topic)) > 0", name="ck_publication_topics_not_blank"),
        sa.CheckConstraint("position >= 0", name="ck_publication_topics_position"),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["publications.id"],
            name="fk_publication_topics_publication_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publication_topics"),
        sa.UniqueConstraint(
            "publication_id", "topic", name="uq_publication_topics_publication_topic"
        ),
        sa.UniqueConstraint(
            "publication_id", "position", name="uq_publication_topics_publication_position"
        ),
    )
    op.create_index(
        "ix_publication_topics_publication_id", "publication_topics", ["publication_id"]
    )

    op.create_table(
        "editorial_settings",
        sa.Column("id", UUID, nullable=False),
        sa.Column("singleton_key", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("featured_publication_id", UUID, nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("singleton_key", name="ck_editorial_settings_singleton_key"),
        sa.ForeignKeyConstraint(
            ["featured_publication_id"],
            ["publications.id"],
            name="fk_editorial_settings_featured_publication_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_editorial_settings"),
        sa.UniqueConstraint("singleton_key", name="uq_editorial_settings_singleton_key"),
    )
    op.create_index(
        "ix_editorial_settings_featured_publication_id",
        "editorial_settings",
        ["featured_publication_id"],
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", UUID, nullable=False),
        sa.Column("author_id", UUID, nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=250), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resource_id", UUID, nullable=True),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599",
            name="ck_idempotency_keys_response_status",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["author_accounts.id"],
            name="fk_idempotency_keys_author_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_keys"),
        sa.UniqueConstraint(
            "author_id", "operation", "key", name="uq_idempotency_keys_author_operation_key"
        ),
    )
    op.create_index("ix_idempotency_keys_author_id", "idempotency_keys", ["author_id"])
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("editorial_settings")
    op.drop_table("publication_topics")
    op.drop_table("publications")
    op.drop_table("writing_versions")
    op.drop_table("writings")
    op.drop_table("author_sessions")
    op.drop_table("books")
    op.drop_table("author_accounts")
