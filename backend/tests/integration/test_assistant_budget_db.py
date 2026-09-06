from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import budget, persistence
from app.assistant.models import AiUsageEntry
from app.clock import utc_now
from app.db import Database
from app.errors import AppError
from app.library.models import Book
from app.writings.models import Writing

LIMIT = 1_000_000


async def _attempt(session: AsyncSession) -> tuple[UUID, UUID]:
    """Create a writing plus one generation attempt, and return their ids."""
    book = Book(title="Duna", author="Frank Herbert")
    session.add(book)
    await session.flush()
    writing = Writing(
        book_id=book.id, title="O deserto", source_range="1–2", markdown="# O deserto"
    )
    session.add(writing)
    await session.flush()
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    attempt = await persistence.create_author_message_and_attempt(
        session,
        conversation.id,
        content="Pergunta",
        model="fake-model",
        instruction_version="parte-1-v1",
    )
    await session.commit()
    return writing.id, attempt.id


async def _entry_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(AiUsageEntry)) or 0)


async def test_reservation_blocks_before_the_external_call(session: AsyncSession) -> None:
    writing_id, attempt_id = await _attempt(session)
    await budget.reserve(
        session, writing_id=writing_id, attempt_id=attempt_id, worst_case=LIMIT, limit=LIMIT
    )
    await budget.settle(session, attempt_id, actual_micros=LIMIT)
    await session.commit()

    _, second_attempt_id = await _attempt(session)
    with pytest.raises(AppError) as raised:
        await budget.reserve(
            session,
            writing_id=writing_id,
            attempt_id=second_attempt_id,
            worst_case=1,
            limit=LIMIT,
        )
    await session.rollback()

    assert raised.value.code == "ai_budget_exceeded"
    assert raised.value.status_code == 429
    assert await _entry_count(session) == 1


async def test_settlement_replaces_the_reservation_only_once(session: AsyncSession) -> None:
    writing_id, attempt_id = await _attempt(session)
    await budget.reserve(
        session, writing_id=writing_id, attempt_id=attempt_id, worst_case=1_000, limit=LIMIT
    )
    assert await budget.totals(session) == (0, 1_000)

    await budget.settle(session, attempt_id, actual_micros=80)
    await budget.settle(session, attempt_id, actual_micros=80)
    await session.commit()

    assert await budget.totals(session) == (80, 0)


async def test_release_frees_the_reservation_and_repeats_are_ignored(
    session: AsyncSession,
) -> None:
    writing_id, attempt_id = await _attempt(session)
    await budget.reserve(
        session, writing_id=writing_id, attempt_id=attempt_id, worst_case=1_000, limit=LIMIT
    )

    await budget.release(session, attempt_id)
    await budget.release(session, attempt_id)
    await session.commit()

    assert await budget.totals(session) == (0, 0)
    assert await _entry_count(session) == 1


async def test_settling_a_released_reservation_does_not_resurrect_it(
    session: AsyncSession,
) -> None:
    writing_id, attempt_id = await _attempt(session)
    await budget.reserve(
        session, writing_id=writing_id, attempt_id=attempt_id, worst_case=1_000, limit=LIMIT
    )
    await budget.release(session, attempt_id)

    await budget.settle(session, attempt_id, actual_micros=900)
    await session.commit()

    entry = await persistence.find_usage_entry(session, attempt_id)
    assert entry is not None
    assert entry.state == "released"
    assert await budget.totals(session) == (0, 0)


async def test_only_one_of_two_simultaneous_reservations_fits(
    session: AsyncSession, migrated_database_url: str
) -> None:
    writing_id, first_attempt_id = await _attempt(session)
    _, second_attempt_id = await _attempt(session)
    barrier = asyncio.Barrier(2)
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)

    async def contend(database: Database, attempt_id: UUID) -> object:
        async with database.session() as current_session:
            await barrier.wait()
            entry = await budget.reserve(
                current_session,
                writing_id=writing_id,
                attempt_id=attempt_id,
                worst_case=600_000,
                limit=LIMIT,
            )
            await current_session.commit()
            return entry

    try:
        results = await asyncio.gather(
            contend(first_database, first_attempt_id),
            contend(second_database, second_attempt_id),
            return_exceptions=True,
        )
    finally:
        await first_database.dispose()
        await second_database.dispose()

    refusals = [result for result in results if isinstance(result, AppError)]
    assert len(refusals) == 1
    assert refusals[0].code == "ai_budget_exceeded"
    assert await _entry_count(session) == 1
    assert await budget.totals(session) == (0, 600_000)


async def test_summary_reports_the_period_totals_and_state(session: AsyncSession) -> None:
    writing_id, attempt_id = await _attempt(session)
    _, other_attempt_id = await _attempt(session)
    await budget.reserve(
        session, writing_id=writing_id, attempt_id=attempt_id, worst_case=500_000, limit=LIMIT
    )
    await budget.settle(session, attempt_id, actual_micros=500_000)
    await budget.reserve(
        session,
        writing_id=writing_id,
        attempt_id=other_attempt_id,
        worst_case=300_000,
        limit=LIMIT,
    )
    await session.commit()

    report = await budget.summary(session, limit=LIMIT)

    assert report.period == utc_now().strftime("%Y-%m")
    assert report.spent_usd_micros == 500_000
    assert report.reserved_usd_micros == 300_000
    assert report.limit_usd_micros == LIMIT
    assert report.limit_state == "near_limit"
