from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.publishing.models import Publication
from app.publishing.persistence import lock_writing


class PrivateDataPurger(Protocol):
    """Deletes one writing's private context; future private modules register one."""

    async def purge(self, session: AsyncSession, writing_id: UUID) -> None: ...


@dataclass
class CleanupResult:
    completed_ids: list[UUID] = field(default_factory=list)
    failed_ids: list[UUID] = field(default_factory=list)
    # Exception class names only: safe to print without leaking private content.
    failure_kinds: list[str] = field(default_factory=list)


def due_publications_query(*, limit: int) -> Select[tuple[Publication]]:
    return (
        select(Publication)
        .where(
            Publication.state == "published",
            Publication.cleanup_due_at <= func.now(),
            Publication.cleanup_cancelled_at.is_(None),
            Publication.cleanup_completed_at.is_(None),
        )
        .order_by(Publication.cleanup_due_at, Publication.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class CleanupRunner:
    """Processes overdue cleanups one transaction at a time.

    Each publication is claimed with SKIP LOCKED and finished (purgers, writing
    status, completion timestamp) inside its own transaction, so a crash or a
    failed purger leaves that publication due and retryable while competing
    runners keep making progress on the rest.
    """

    def __init__(self, database: Database, purgers: Sequence[PrivateDataPurger] = ()) -> None:
        self._database = database
        self._purgers = tuple(purgers)

    async def run_batch(self, limit: int) -> CleanupResult:
        result = CleanupResult()
        for _ in range(limit):
            processed = await self._process_next(skip_ids=result.failed_ids, into=result)
            if not processed:
                break
        return result

    async def _process_next(self, *, skip_ids: list[UUID], into: CleanupResult) -> bool:
        async with self._database.session() as session:
            publication = await self._claim_next_due(session, skip_ids)
            if publication is None:
                return False
            # Captured before rollback can expire the instance's attributes.
            publication_id = publication.id
            try:
                await self._complete(session, publication)
            # A purger failure must not stop the batch; the item stays due.
            except Exception as error:  # noqa: BLE001
                await session.rollback()
                into.failed_ids.append(publication_id)
                into.failure_kinds.append(type(error).__name__)
            else:
                into.completed_ids.append(publication_id)
        return True

    async def _claim_next_due(
        self, session: AsyncSession, skip_ids: list[UUID]
    ) -> Publication | None:
        query = due_publications_query(limit=1)
        if skip_ids:
            query = query.where(Publication.id.not_in(skip_ids))
        return cast(Publication | None, await session.scalar(query))

    async def _complete(self, session: AsyncSession, publication: Publication) -> None:
        for purger in self._purgers:
            await purger.purge(session, publication.writing_id)

        now = await session.scalar(select(func.now()))
        assert now is not None
        publication.cleanup_completed_at = now
        publication.updated_at = now
        writing = await lock_writing(session, publication.writing_id)
        if writing is not None:
            writing.status = "published"
        await session.commit()
