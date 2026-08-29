from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthorAccount, AuthorSession


async def find_active_author(session: AsyncSession, email: str) -> AuthorAccount | None:
    return cast(
        AuthorAccount | None,
        await session.scalar(
            select(AuthorAccount).where(
                AuthorAccount.email == email,
                AuthorAccount.is_active.is_(True),
            )
        ),
    )


async def insert_author(session: AsyncSession, email: str, password_hash: str) -> AuthorAccount:
    author = AuthorAccount(email=email, password_hash=password_hash, is_active=True)
    session.add(author)
    await session.flush()
    return author


async def insert_session(
    session: AsyncSession,
    author_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> AuthorSession:
    author_session = AuthorSession(
        author_id=author_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(author_session)
    await session.flush()
    return author_session


async def find_valid_session(
    session: AsyncSession, token_hash: str, now: datetime
) -> tuple[AuthorSession, AuthorAccount] | None:
    result = await session.execute(
        select(AuthorSession, AuthorAccount)
        .join(AuthorAccount, AuthorAccount.id == AuthorSession.author_id)
        .where(
            AuthorSession.token_hash == token_hash,
            AuthorSession.revoked_at.is_(None),
            AuthorSession.expires_at > now,
            AuthorAccount.is_active.is_(True),
        )
    )
    row = result.one_or_none()
    return None if row is None else (row[0], row[1])


async def touch_session_if_stale(
    session: AsyncSession,
    session_id: UUID,
    now: datetime,
    stale_before: datetime,
) -> None:
    await session.execute(
        update(AuthorSession)
        .where(
            AuthorSession.id == session_id,
            AuthorSession.last_seen_at <= stale_before,
        )
        .values(last_seen_at=now)
    )


async def revoke_session(session: AsyncSession, token_hash: str, now: datetime) -> None:
    await session.execute(
        update(AuthorSession)
        .where(
            AuthorSession.token_hash == token_hash,
            AuthorSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
