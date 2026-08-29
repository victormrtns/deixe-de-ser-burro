from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.writings.models import Writing, WritingVersion


async def insert_writing(
    session: AsyncSession, book_id: UUID, *, title: str, source_range: str, markdown: str
) -> Writing:
    writing = Writing(book_id=book_id, title=title, source_range=source_range, markdown=markdown)
    session.add(writing)
    await session.flush()
    return writing


async def insert_version(session: AsyncSession, writing: Writing, *, reason: str) -> WritingVersion:
    version = WritingVersion(
        writing_id=writing.id,
        version_number=writing.version_number,
        markdown=writing.markdown,
        title=writing.title,
        source_range=writing.source_range,
        reason=reason,
    )
    session.add(version)
    await session.flush()
    return version


async def list_writings(session: AsyncSession, book_id: UUID) -> Sequence[Writing]:
    result = await session.scalars(
        select(Writing).where(Writing.book_id == book_id).order_by(Writing.created_at, Writing.id)
    )
    return result.all()


async def find_writing(session: AsyncSession, writing_id: UUID) -> Writing | None:
    return cast(Writing | None, await session.get(Writing, writing_id))


async def compare_and_swap(
    session: AsyncSession,
    writing_id: UUID,
    expected_version: int,
    changes: dict[str, Any],
) -> Writing | None:
    statement = (
        update(Writing)
        .where(Writing.id == writing_id, Writing.version_number == expected_version)
        .values(**changes, version_number=Writing.version_number + 1, updated_at=func.now())
        .returning(Writing)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def current_version(session: AsyncSession, writing_id: UUID) -> int | None:
    return cast(
        int | None,
        await session.scalar(select(Writing.version_number).where(Writing.id == writing_id)),
    )


async def list_versions(
    session: AsyncSession, writing_id: UUID, *, limit: int, before_version: int | None
) -> Sequence[WritingVersion]:
    query = (
        select(WritingVersion)
        .where(WritingVersion.writing_id == writing_id)
        .order_by(WritingVersion.version_number.desc())
        .limit(limit)
    )
    if before_version is not None:
        query = query.where(WritingVersion.version_number < before_version)
    return (await session.scalars(query)).all()


async def find_version(
    session: AsyncSession, writing_id: UUID, version_number: int
) -> WritingVersion | None:
    return cast(
        WritingVersion | None,
        await session.scalar(
            select(WritingVersion).where(
                WritingVersion.writing_id == writing_id,
                WritingVersion.version_number == version_number,
            )
        ),
    )


async def has_active_publication(session: AsyncSession, writing_id: UUID) -> bool:
    # Raw projection on purpose: the publishing module owns the ORM model later.
    found = await session.scalar(
        text("SELECT 1 FROM publications WHERE writing_id = :writing_id AND state = 'published'"),
        {"writing_id": writing_id},
    )
    return found is not None


async def delete_writing(session: AsyncSession, writing: Writing) -> None:
    await session.delete(writing)
    await session.flush()
