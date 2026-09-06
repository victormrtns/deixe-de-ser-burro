from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BUSINESS_TABLES = {
    "ai_usage_entries",
    "author_accounts",
    "author_sessions",
    "books",
    "conversation_messages",
    "conversations",
    "generation_attempts",
    "editorial_settings",
    "idempotency_keys",
    "publication_topics",
    "publications",
    "writing_memory_items",
    "writing_versions",
    "writings",
}


async def _insert_writing_version(session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    book_id = uuid4()
    writing_id = uuid4()
    version_id = uuid4()
    await session.execute(
        text("INSERT INTO books (id, title, author) VALUES (:book_id, 'Duna', 'Frank Herbert')"),
        {"book_id": book_id},
    )
    await session.execute(
        text(
            "INSERT INTO writings "
            "(id, book_id, title, source_range, markdown, version_number, status) "
            "VALUES (:writing_id, :book_id, 'Ecologia de Duna', '', '# Duna', 1, 'draft')"
        ),
        {"writing_id": writing_id, "book_id": book_id},
    )
    await session.execute(
        text(
            "INSERT INTO writing_versions "
            "(id, writing_id, version_number, markdown, title, source_range, reason) "
            "VALUES (:version_id, :writing_id, 1, '# Duna', 'Ecologia de Duna', '', 'created')"
        ),
        {"version_id": version_id, "writing_id": writing_id},
    )
    await session.commit()
    return book_id, writing_id, version_id


async def _insert_publication(
    session: AsyncSession,
    *,
    writing_id: UUID,
    version_id: UUID,
    slug: str = "ecologia-de-duna",
    book_slug: str = "duna",
    state: str = "published",
) -> UUID:
    publication_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO publications "
            "(id, writing_id, writing_version_id, slug, title, markdown, excerpt, "
            "reading_minutes, published_at, book_slug, book_title, book_author, "
            "public_cover_path, state, cleanup_due_at) "
            "VALUES (:publication_id, :writing_id, :version_id, :slug, 'Ecologia de Duna', "
            "'# Duna', 'Ecologia', 1, now(), :book_slug, 'Duna', 'Frank Herbert', "
            "'public/covers/duna.webp', :state, now() + interval '3 days')"
        ),
        {
            "publication_id": publication_id,
            "writing_id": writing_id,
            "version_id": version_id,
            "slug": slug,
            "book_slug": book_slug,
            "state": state,
        },
    )
    return publication_id


async def test_deleting_a_writing_removes_its_withdrawn_snapshot_dependencies(
    session: AsyncSession,
) -> None:
    _, writing_id, version_id = await _insert_writing_version(session)
    publication_id = await _insert_publication(
        session,
        writing_id=writing_id,
        version_id=version_id,
        state="withdrawn",
    )
    await session.execute(
        text(
            "INSERT INTO publication_topics (id, publication_id, topic, position) "
            "VALUES (:id, :publication_id, 'ecologia', 0)"
        ),
        {"id": uuid4(), "publication_id": publication_id},
    )
    await session.execute(
        text(
            "INSERT INTO editorial_settings (id, featured_publication_id) "
            "VALUES (:id, :publication_id)"
        ),
        {"id": uuid4(), "publication_id": publication_id},
    )
    await session.commit()

    await session.execute(text("DELETE FROM writings WHERE id = :id"), {"id": writing_id})
    await session.commit()

    assert (
        await session.scalar(
            text("SELECT count(*) FROM writing_versions WHERE writing_id = :id"),
            {"id": writing_id},
        )
        == 0
    )
    assert (
        await session.scalar(
            text("SELECT count(*) FROM publications WHERE writing_id = :id"), {"id": writing_id}
        )
        == 0
    )
    assert (
        await session.scalar(
            text("SELECT count(*) FROM publication_topics WHERE publication_id = :id"),
            {"id": publication_id},
        )
        == 0
    )
    assert (
        await session.scalar(
            text("SELECT count(*) FROM editorial_settings WHERE featured_publication_id IS NULL")
        )
        == 1
    )


async def test_publication_rejects_a_version_owned_by_another_writing(
    session: AsyncSession,
) -> None:
    _, writing_a, _ = await _insert_writing_version(session)
    _, _, version_b = await _insert_writing_version(session)

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await _insert_publication(
                session,
                writing_id=writing_a,
                version_id=version_b,
                slug="par-cruzado",
            )


async def test_publication_accepts_a_version_owned_by_the_same_writing(
    session: AsyncSession,
) -> None:
    _, writing_id, version_id = await _insert_writing_version(session)
    publication_id = await _insert_publication(
        session,
        writing_id=writing_id,
        version_id=version_id,
    )
    await session.commit()

    assert (
        await session.scalar(
            text("SELECT writing_version_id FROM publications WHERE id = :id"),
            {"id": publication_id},
        )
        == version_id
    )


@pytest.mark.parametrize(
    ("slug", "book_slug"),
    [
        ("", "duna"),
        ("Duna", "duna"),
        (" duna", "duna"),
        ("duna--ecologia", "duna"),
        ("ecologia", "Duna"),
        ("ecologia", "duna/privado"),
    ],
)
async def test_publication_rejects_non_canonical_public_slugs(
    session: AsyncSession, slug: str, book_slug: str
) -> None:
    _, writing_id, version_id = await _insert_writing_version(session)

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await _insert_publication(
                session,
                writing_id=writing_id,
                version_id=version_id,
                slug=slug,
                book_slug=book_slug,
            )


async def test_cleanup_query_uses_the_pending_cleanup_index(session: AsyncSession) -> None:
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        await session.scalars(
            text(
                "EXPLAIN SELECT id FROM publications "
                "WHERE state = 'published' "
                "AND cleanup_due_at <= now() "
                "AND cleanup_cancelled_at IS NULL "
                "AND cleanup_completed_at IS NULL "
                "ORDER BY cleanup_due_at, id LIMIT 100"
            )
        )
    )

    assert "ix_publications_pending_cleanup" in plan


async def test_schema_catalog_covers_core_types_constraints_and_indexes(
    session: AsyncSession,
) -> None:
    uuid_id_tables = set(
        await session.scalars(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND column_name = 'id' "
                "AND data_type = 'uuid'"
            )
        )
    )
    assert uuid_id_tables == BUSINESS_TABLES

    invalid_timestamp_columns = list(
        await session.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND column_name LIKE '%\\_at' "
                "AND data_type <> 'timestamp with time zone'"
            )
        )
    )
    assert invalid_timestamp_columns == []

    selected_columns = {
        (row.table_name, row.column_name): (row.is_nullable, row.column_default)
        for row in await session.execute(
            text(
                "SELECT table_name, column_name, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = current_schema() "
                "AND (table_name, column_name) IN "
                "(('author_accounts', 'is_active'), ('writings', 'version_number'), "
                "('writings', 'status'), ('publications', 'slug'), "
                "('publications', 'public_cover_path'), ('idempotency_keys', 'response_body'))"
            )
        )
    }
    assert selected_columns == {
        ("author_accounts", "is_active"): ("NO", "true"),
        ("writings", "version_number"): ("NO", "1"),
        ("writings", "status"): ("NO", "'draft'::character varying"),
        ("publications", "slug"): ("NO", None),
        ("publications", "public_cover_path"): ("YES", None),
        ("idempotency_keys", "response_body"): ("YES", None),
    }

    constraints = set(
        await session.scalars(
            text(
                "SELECT conname FROM pg_catalog.pg_constraint "
                "WHERE connamespace = current_schema()::regnamespace"
            )
        )
    )
    assert {
        "fk_publications_writing_version_pair",
        "ck_publications_slug_canonical",
        "ck_publications_book_slug_canonical",
        "uq_writing_versions_writing_id_id",
    } <= constraints

    indexes = set(
        await session.scalars(
            text("SELECT indexname FROM pg_catalog.pg_indexes WHERE schemaname = current_schema()")
        )
    )
    assert {
        "ix_publications_pending_cleanup",
        "ix_publications_writing_version_pair",
        "ix_publications_writing_version_id",
        "uq_publications_active_slug",
        "uq_publications_active_writing",
    } <= indexes

    foreign_key_rows = await session.execute(
        text(
            "SELECT relation.relname AS table_name, constraint_row.conname, "
            "array_agg(attribute.attname ORDER BY key_column.ordinality) AS columns "
            "FROM pg_catalog.pg_constraint AS constraint_row "
            "JOIN pg_catalog.pg_class AS relation "
            "ON relation.oid = constraint_row.conrelid "
            "CROSS JOIN LATERAL unnest(constraint_row.conkey) "
            "WITH ORDINALITY AS key_column(attnum, ordinality) "
            "JOIN pg_catalog.pg_attribute AS attribute "
            "ON attribute.attrelid = constraint_row.conrelid "
            "AND attribute.attnum = key_column.attnum "
            "WHERE constraint_row.connamespace = current_schema()::regnamespace "
            "AND constraint_row.contype = 'f' "
            "GROUP BY relation.relname, constraint_row.conname"
        )
    )
    index_rows = await session.execute(
        text(
            "SELECT relation.relname AS table_name, index_relation.relname AS index_name, "
            "array_agg(attribute.attname ORDER BY index_column.ordinality) AS columns "
            "FROM pg_catalog.pg_index AS index_row "
            "JOIN pg_catalog.pg_class AS relation ON relation.oid = index_row.indrelid "
            "JOIN pg_catalog.pg_class AS index_relation ON index_relation.oid = index_row.indexrelid "
            "CROSS JOIN LATERAL unnest(index_row.indkey) "
            "WITH ORDINALITY AS index_column(attnum, ordinality) "
            "JOIN pg_catalog.pg_attribute AS attribute "
            "ON attribute.attrelid = index_row.indrelid "
            "AND attribute.attnum = index_column.attnum "
            "WHERE relation.relnamespace = current_schema()::regnamespace "
            "AND index_row.indisvalid "
            "GROUP BY relation.relname, index_relation.relname"
        )
    )
    indexed_columns = [(row.table_name, tuple(row.columns)) for row in index_rows]
    uncovered_foreign_keys = [
        row.conname
        for row in foreign_key_rows
        if not any(
            table_name == row.table_name and columns[: len(row.columns)] == tuple(row.columns)
            for table_name, columns in indexed_columns
        )
    ]
    assert uncovered_foreign_keys == []

    delete_action_rows = await session.execute(
        text(
            "SELECT conname, confdeltype FROM pg_catalog.pg_constraint "
            "WHERE connamespace = current_schema()::regnamespace AND contype = 'f' "
            "AND conname IN ('fk_publications_writing_id', "
            "'fk_publications_writing_version_pair')"
        )
    )
    delete_actions = dict(delete_action_rows.tuples().all())
    assert delete_actions == {
        "fk_publications_writing_id": "c",
        "fk_publications_writing_version_pair": "c",
    }


async def test_initial_migration_downgrades_to_no_business_tables_and_reupgrades(
    migrated_database_url: str,
) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = migrated_database_url

    await asyncio.to_thread(command.downgrade, config, "base")
    engine = create_async_engine(migrated_database_url)
    try:
        async with engine.connect() as connection:
            tables_after_downgrade = set(
                await connection.scalars(
                    text(
                        "SELECT tablename FROM pg_catalog.pg_tables "
                        "WHERE schemaname = current_schema()"
                    )
                )
            )
        assert tables_after_downgrade.isdisjoint(BUSINESS_TABLES)
    finally:
        await engine.dispose()
        await asyncio.to_thread(command.upgrade, config, "head")

    verification_engine = create_async_engine(migrated_database_url)
    try:
        async with verification_engine.connect() as connection:
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0002_contextual_ai_conversation"
            )
    finally:
        await verification_engine.dispose()


async def test_zz_committed_test_state_is_written_for_isolation_probe(
    session: AsyncSession,
) -> None:
    await session.execute(text("TRUNCATE author_accounts CASCADE"))
    await session.execute(
        text(
            "INSERT INTO author_accounts (id, email, password_hash, is_active) "
            "VALUES (:id, 'isolation@example.com', 'hash', true)"
        ),
        {"id": uuid4()},
    )
    await session.commit()
    assert await session.scalar(text("SELECT count(*) FROM author_accounts")) == 1


async def test_zzz_each_test_starts_with_an_empty_business_schema(
    session: AsyncSession,
) -> None:
    assert await session.scalar(text("SELECT count(*) FROM author_accounts")) == 0
