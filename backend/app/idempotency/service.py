from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import utc_now
from app.errors import AppError
from app.idempotency.models import IdempotencyKey

REPLAY_WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class StoredResponse:
    status_code: int
    body: dict[str, Any]
    resource_id: UUID | None = None


def canonical_request_hash(payload: BaseModel) -> str:
    raw = payload.model_dump_json(by_alias=True, exclude_none=False)
    return sha256(raw.encode()).hexdigest()


async def execute_idempotent(
    session: AsyncSession,
    *,
    author_id: UUID,
    operation: str,
    key: str,
    request_hash: str,
    action: Callable[[], Awaitable[StoredResponse]],
) -> StoredResponse:
    """Run `action` at most once per (author, operation, key).

    The action must leave its writes uncommitted: the key record is committed in
    the same transaction, so a lost race rolls the duplicate work back and the
    caller receives the winner's stored response instead.
    """
    existing = await _find_key(session, author_id, operation, key, for_update=True)
    if existing is not None:
        return _replay(existing, request_hash)

    response = await action()
    session.add(
        IdempotencyKey(
            author_id=author_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            response_status=response.status_code,
            response_body=response.body,
            resource_id=response.resource_id,
            expires_at=utc_now() + REPLAY_WINDOW,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        winner = await _find_key(session, author_id, operation, key, for_update=False)
        if winner is None:
            raise
        return _replay(winner, request_hash)
    return response


async def _find_key(
    session: AsyncSession,
    author_id: UUID,
    operation: str,
    key: str,
    *,
    for_update: bool,
) -> IdempotencyKey | None:
    query = select(IdempotencyKey).where(
        IdempotencyKey.author_id == author_id,
        IdempotencyKey.operation == operation,
        IdempotencyKey.key == key,
    )
    if for_update:
        query = query.with_for_update()
    return cast(IdempotencyKey | None, await session.scalar(query))


def _replay(record: IdempotencyKey, request_hash: str) -> StoredResponse:
    if record.request_hash != request_hash:
        raise AppError(
            "idempotency_conflict",
            "A chave de idempotência já foi usada com outro conteúdo.",
            409,
        )
    if record.response_status is None or record.response_body is None:
        raise AppError(
            "idempotency_conflict",
            "A operação anterior com esta chave não registrou uma resposta.",
            409,
        )
    return StoredResponse(record.response_status, record.response_body, record.resource_id)
