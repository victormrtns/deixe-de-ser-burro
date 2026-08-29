from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.publishing.models import EditorialSettings, Publication
from app.writings.models import Writing


async def lock_writing(session: AsyncSession, writing_id: UUID) -> Writing | None:
    return cast(
        Writing | None,
        await session.scalar(select(Writing).where(Writing.id == writing_id).with_for_update()),
    )


async def active_publication(session: AsyncSession, writing_id: UUID) -> Publication | None:
    return cast(
        Publication | None,
        await session.scalar(
            select(Publication).where(
                Publication.writing_id == writing_id, Publication.state == "published"
            )
        ),
    )


async def lock_active_publication(session: AsyncSession, writing_id: UUID) -> Publication | None:
    return cast(
        Publication | None,
        await session.scalar(
            select(Publication)
            .where(Publication.writing_id == writing_id, Publication.state == "published")
            .with_for_update()
        ),
    )


async def latest_publication(session: AsyncSession, writing_id: UUID) -> Publication | None:
    return cast(
        Publication | None,
        await session.scalar(
            select(Publication)
            .where(Publication.writing_id == writing_id)
            .order_by(Publication.created_at.desc(), Publication.id.desc())
            .limit(1)
        ),
    )


async def find_active_by_slug(session: AsyncSession, slug: str) -> Publication | None:
    return cast(
        Publication | None,
        await session.scalar(
            select(Publication).where(Publication.slug == slug, Publication.state == "published")
        ),
    )


async def is_slug_taken(session: AsyncSession, slug: str) -> bool:
    return await find_active_by_slug(session, slug) is not None


async def database_now(session: AsyncSession) -> datetime:
    now = await session.scalar(select(func.now()))
    assert now is not None
    return now


async def insert_publication(session: AsyncSession, **fields: Any) -> Publication:
    publication = Publication(**fields)
    session.add(publication)
    await session.flush()
    return publication


async def lock_editorial_settings(session: AsyncSession) -> EditorialSettings:
    settings = cast(
        EditorialSettings | None,
        await session.scalar(select(EditorialSettings).with_for_update()),
    )
    if settings is not None:
        return settings

    settings = EditorialSettings()
    session.add(settings)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(EditorialSettings).with_for_update())
        assert existing is not None
        return existing
    return settings
