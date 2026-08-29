from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import CurrentAuthor
from app.auth.service import require_allowed_origin, require_author
from app.db import get_session
from app.writings import service
from app.writings.schemas import (
    WorkspacePayload,
    WritingCreateRequest,
    WritingDto,
    WritingMetadataRequest,
    WritingRestoreRequest,
    WritingSaveRequest,
    WritingVersionDto,
    WritingVersionPage,
)

router = APIRouter(
    prefix="/api",
    tags=["writings"],
    dependencies=[Depends(require_allowed_origin), Depends(require_author)],
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.get("/books/{book_id}/writings", response_model=list[WritingDto])
async def list_book_writings(book_id: UUID, session: SessionDependency) -> list[WritingDto]:
    return await service.list_book_writings(session, book_id)


@router.post(
    "/books/{book_id}/writings", response_model=WritingDto, status_code=status.HTTP_201_CREATED
)
async def create_writing(
    book_id: UUID,
    payload: WritingCreateRequest,
    session: SessionDependency,
    author: Annotated[CurrentAuthor, Depends(require_author)],
    idempotency_key: IdempotencyKeyHeader = None,
) -> JSONResponse:
    stored = await service.create_writing(
        session, author.id, book_id, payload, idempotency_key=idempotency_key
    )
    return JSONResponse(status_code=stored.status_code, content=stored.body)


@router.get("/writings/{writing_id}", response_model=WritingDto)
async def get_writing(writing_id: UUID, session: SessionDependency) -> WritingDto:
    return await service.get_writing(session, writing_id)


@router.put("/writings/{writing_id}", response_model=WritingDto)
async def save_markdown(
    writing_id: UUID, payload: WritingSaveRequest, session: SessionDependency
) -> WritingDto:
    return await service.save_markdown(session, writing_id, payload)


@router.patch("/writings/{writing_id}", response_model=WritingDto)
async def update_metadata(
    writing_id: UUID, payload: WritingMetadataRequest, session: SessionDependency
) -> WritingDto:
    return await service.update_metadata(session, writing_id, payload)


@router.delete("/writings/{writing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_writing(writing_id: UUID, session: SessionDependency) -> None:
    await service.delete_writing(session, writing_id)


@router.get("/writings/{writing_id}/workspace", response_model=WorkspacePayload)
async def get_workspace(writing_id: UUID, session: SessionDependency) -> WorkspacePayload:
    return await service.get_workspace(session, writing_id)


@router.get("/writings/{writing_id}/versions", response_model=WritingVersionPage)
async def list_versions(
    writing_id: UUID,
    session: SessionDependency,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = service.DEFAULT_VERSION_PAGE_SIZE,
) -> WritingVersionPage:
    return await service.list_versions(session, writing_id, cursor=cursor, limit=limit)


@router.post("/writings/{writing_id}/versions/{version_number}/restore", response_model=WritingDto)
async def restore_version(
    writing_id: UUID,
    version_number: int,
    payload: WritingRestoreRequest,
    session: SessionDependency,
) -> WritingDto:
    return await service.restore_version(
        session, writing_id, version_number, payload.expected_version
    )


@router.get("/writings/{writing_id}/versions/{version_number}", response_model=WritingVersionDto)
async def get_version(
    writing_id: UUID, version_number: int, session: SessionDependency
) -> WritingVersionDto:
    return await service.get_version(session, writing_id, version_number)
