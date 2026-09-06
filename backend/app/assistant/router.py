from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import service
from app.assistant.dependencies import get_model_gateway
from app.assistant.gateway import ModelGateway
from app.assistant.schemas import (
    ConversationDto,
    MemoryCreateRequest,
    MemoryItemDto,
    SendMessageRequest,
    UsageSummaryDto,
)
from app.auth.schemas import CurrentAuthor
from app.auth.service import require_allowed_origin, require_author
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError

router = APIRouter(
    prefix="/api/writings/{writing_id}",
    tags=["assistant"],
    dependencies=[Depends(require_allowed_origin), Depends(require_author)],
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
AuthorDependency = Annotated[CurrentAuthor, Depends(require_author)]
GatewayDependency = Annotated[ModelGateway, Depends(get_model_gateway)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]

SSE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


@router.get("/conversation", response_model=ConversationDto)
async def get_conversation(writing_id: UUID, session: SessionDependency) -> ConversationDto:
    return await service.get_conversation(session, writing_id)


@router.post("/conversation/messages")
async def send_message(
    writing_id: UUID,
    payload: SendMessageRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    author: AuthorDependency,
    gateway: GatewayDependency,
    idempotency_key: IdempotencyKeyHeader = None,
) -> StreamingResponse:
    prepared = await service.prepare_generation(
        session,
        settings=settings,
        writing_id=writing_id,
        author_id=author.id,
        content=payload.content,
        idempotency_key=_require_key(idempotency_key),
    )
    return _stream(session, gateway, prepared)


@router.post("/conversation/messages/{message_id}/retry")
async def retry_message(
    writing_id: UUID,
    message_id: UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    author: AuthorDependency,
    gateway: GatewayDependency,
    idempotency_key: IdempotencyKeyHeader = None,
) -> StreamingResponse:
    prepared = await service.prepare_generation(
        session,
        settings=settings,
        writing_id=writing_id,
        author_id=author.id,
        author_message_id=message_id,
        idempotency_key=_require_key(idempotency_key),
    )
    return _stream(session, gateway, prepared)


@router.post("/memory", response_model=MemoryItemDto, status_code=status.HTTP_201_CREATED)
async def remember(
    writing_id: UUID, payload: MemoryCreateRequest, session: SessionDependency
) -> MemoryItemDto:
    return await service.create_memory_item(session, writing_id, payload)


@router.get("/usage", response_model=UsageSummaryDto)
async def get_usage(
    writing_id: UUID, session: SessionDependency, settings: SettingsDependency
) -> UsageSummaryDto:
    return await service.get_usage(session, settings)


def _require_key(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise AppError("validation_error", "Idempotency-Key é obrigatório.", 400)
    return idempotency_key


def _stream(
    session: AsyncSession, gateway: ModelGateway, prepared: service.Prepared
) -> StreamingResponse:
    # Every pre-stream failure already raised above, so the response body can
    # only carry domain frames from here on.
    return StreamingResponse(
        _frames(session, gateway, prepared),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def _frames(
    session: AsyncSession, gateway: ModelGateway, prepared: service.Prepared
) -> AsyncIterator[str]:
    async for name, payload in service.run_generation(session, gateway, prepared):
        yield _sse_frame(name, payload)


def _sse_frame(name: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return f"event: {name}\ndata: {body}\n\n"
