from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.library.models import Book
from app.publishing.cleanup import CleanupRunner
from app.publishing.models import Publication
from app.writings.models import Writing, WritingVersion


class RecordingPurger:
    def __init__(self) -> None:
        self.purged_writing_ids: list[UUID] = []

    async def purge(self, session: AsyncSession, writing_id: UUID) -> None:
        self.purged_writing_ids.append(writing_id)


class FailingPurger:
    async def purge(self, session: AsyncSession, writing_id: UUID) -> None:
        raise RuntimeError("purge failed")


async def seed_publication(
    session: AsyncSession,
    *,
    due_in: timedelta,
    cancelled: bool = False,
    slug: str | None = None,
) -> Publication:
    book = Book(title="Duna", author="Frank Herbert")
    session.add(book)
    await session.flush()
    writing = Writing(
        book_id=book.id,
        title="O deserto",
        source_range="Cap. 1",
        markdown="# O deserto",
        status="cleanup_scheduled",
    )
    session.add(writing)
    await session.flush()
    version = WritingVersion(
        writing_id=writing.id,
        version_number=1,
        markdown=writing.markdown,
        title=writing.title,
        source_range=writing.source_range,
        reason="created",
    )
    session.add(version)
    await session.flush()
    now = await session.scalar(text("SELECT now()"))
    assert now is not None
    publication = Publication(
        writing_id=writing.id,
        writing_version_id=version.id,
        slug=slug or f"o-deserto-{uuid4().hex[:8]}",
        title=writing.title,
        markdown=writing.markdown,
        excerpt="Um resumo.",
        reading_minutes=1,
        published_at=now - timedelta(days=4),
        book_slug="duna",
        book_title="Duna",
        book_author="Frank Herbert",
        cleanup_due_at=now + due_in,
        cleanup_cancelled_at=now if cancelled else None,
    )
    session.add(publication)
    await session.commit()
    return publication


async def test_cleanup_completes_due_publications_and_is_repeatable(
    session: AsyncSession, migrated_database_url: str
) -> None:
    due = await seed_publication(session, due_in=timedelta(hours=-1))
    await seed_publication(session, due_in=timedelta(hours=-1), cancelled=True)
    await seed_publication(session, due_in=timedelta(days=1))
    purger = RecordingPurger()
    database = Database(migrated_database_url)
    runner = CleanupRunner(database, purgers=[purger])

    try:
        first = await runner.run_batch(limit=10)
        second = await runner.run_batch(limit=10)
    finally:
        await database.dispose()

    completed_at = await session.scalar(
        text("SELECT cleanup_completed_at FROM publications WHERE id = :id"), {"id": due.id}
    )
    writing_status = await session.scalar(
        text("SELECT status FROM writings WHERE id = :id"), {"id": due.writing_id}
    )
    assert first.completed_ids == [due.id]
    assert first.failed_ids == []
    assert second.completed_ids == []
    assert purger.purged_writing_ids == [due.writing_id]
    assert completed_at is not None
    assert writing_status == "published"


async def test_a_failed_purger_leaves_the_publication_retryable(
    session: AsyncSession, migrated_database_url: str
) -> None:
    due = await seed_publication(session, due_in=timedelta(hours=-1))
    database = Database(migrated_database_url)

    try:
        failed = await CleanupRunner(database, purgers=[FailingPurger()]).run_batch(limit=10)
        recovered = await CleanupRunner(database, purgers=[RecordingPurger()]).run_batch(limit=10)
    finally:
        await database.dispose()

    assert failed.completed_ids == []
    assert failed.failed_ids == [due.id]
    assert recovered.completed_ids == [due.id]


async def test_competing_runners_never_purge_the_same_publication(
    session: AsyncSession, migrated_database_url: str
) -> None:
    first_due = await seed_publication(session, due_in=timedelta(hours=-2))
    second_due = await seed_publication(session, due_in=timedelta(hours=-1))
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)
    first_purger, second_purger = RecordingPurger(), RecordingPurger()

    try:
        first_result, second_result = await asyncio.gather(
            CleanupRunner(first_database, purgers=[first_purger]).run_batch(limit=10),
            CleanupRunner(second_database, purgers=[second_purger]).run_batch(limit=10),
        )
    finally:
        await first_database.dispose()
        await second_database.dispose()

    all_completed = sorted(first_result.completed_ids + second_result.completed_ids)
    all_purged = first_purger.purged_writing_ids + second_purger.purged_writing_ids
    assert all_completed == sorted([first_due.id, second_due.id])
    assert sorted(all_purged) == sorted([first_due.writing_id, second_due.writing_id])


async def test_cli_reports_counts_only_and_uses_safe_exit_codes(
    session: AsyncSession, migrated_database_url: str
) -> None:
    await seed_publication(session, due_in=timedelta(hours=-1))
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": migrated_database_url,
            "PUBLIC_ORIGIN": "http://localhost:5173",
            "FILES_ROOT": "./data/test-files",
        }
    )
    backend_root = Path(__file__).parents[2]

    run = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.cli", "cleanup-due-publications", "--limit", "10"],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert run.returncode == 0, run.stderr + run.stdout
    assert "1" in run.stdout
    assert "O deserto" not in run.stdout + run.stderr
