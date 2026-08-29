from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthorAccount
from app.auth.persistence import (
    find_active_author,
    find_valid_session,
    insert_author,
    insert_session,
    revoke_session,
    touch_session_if_stale,
)
from app.auth.schemas import CurrentAuthor
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_PASSWORD_HASH = PasswordHash.recommended()


@dataclass(frozen=True)
class IssuedSession:
    token: str = field(repr=False)
    expires_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_session_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def normalize_origin(value: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if (
        scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None

    effective_port = port if port is not None else (443 if scheme == "https" else 80)
    return scheme, parsed.hostname.lower(), effective_port


async def bootstrap_author(session: AsyncSession, email: str, password: str) -> AuthorAccount:
    normalized_email = normalize_email(email)
    if not normalized_email or not password:
        raise AppError("invalid_bootstrap_credentials", "Credenciais inválidas.", 400)

    existing = await session.scalar(
        select(AuthorAccount).where(AuthorAccount.is_active.is_(True)).limit(1)
    )
    if existing is not None:
        raise AppError("author_already_exists", "O autor já foi criado.", 409)

    encoded_password = _PASSWORD_HASH.hash(password)
    try:
        author = await insert_author(session, normalized_email, encoded_password)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AppError("author_already_exists", "O autor já foi criado.", 409) from error
    return author


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
    ttl: timedelta = timedelta(days=7),
) -> IssuedSession:
    author = await find_active_author(session, normalize_email(email))
    if author is None or not _PASSWORD_HASH.verify(password, author.password_hash):
        raise AppError("invalid_credentials", "Credenciais inválidas.", 401)

    token = secrets.token_urlsafe(32)
    expires_at = utc_now() + ttl
    await insert_session(session, author.id, hash_session_token(token), expires_at)
    await session.commit()
    return IssuedSession(token, expires_at)


async def resolve_author(
    session: AsyncSession,
    token: str | None,
    touch_interval: timedelta,
) -> CurrentAuthor | None:
    if not token:
        return None

    now = utc_now()
    resolved = await find_valid_session(session, hash_session_token(token), now)
    if resolved is None:
        return None

    author_session, author = resolved
    await touch_session_if_stale(
        session,
        author_session.id,
        now,
        now - touch_interval,
    )
    await session.commit()
    return CurrentAuthor(id=author.id, email=author.email)


async def revoke_author_session(session: AsyncSession, token: str | None) -> None:
    if token:
        await revoke_session(session, hash_session_token(token), utc_now())
        await session.commit()


async def optional_author(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentAuthor | None:
    return await resolve_author(
        session,
        request.cookies.get(settings.session_cookie_name),
        timedelta(seconds=settings.session_touch_interval_seconds),
    )


async def require_author(
    author: Annotated[CurrentAuthor | None, Depends(optional_author)],
) -> CurrentAuthor:
    if author is None:
        raise AppError("authentication_required", "Autenticação necessária.", 401)
    return author


async def require_allowed_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if request.method.upper() not in UNSAFE_METHODS:
        return
    if normalize_origin(request.headers.get("origin", "")) != normalize_origin(
        str(settings.public_origin)
    ):
        raise AppError("origin_not_allowed", "Origem não permitida.", 403)
