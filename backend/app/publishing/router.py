from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import CurrentAuthor
from app.auth.service import require_allowed_origin, require_author
from app.db import get_session
from app.files.local import get_file_store
from app.files.service import FileStore
from app.publishing import service
from app.publishing.schemas import FeaturedSelectionRequest, PublicationStatusDto, PublishResult

router = APIRouter(
    prefix="/api",
    tags=["publishing"],
    dependencies=[Depends(require_allowed_origin), Depends(require_author)],
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.post(
    "/writings/{writing_id}/publication",
    response_model=PublishResult,
    status_code=status.HTTP_201_CREATED,
)
async def publish_writing(
    writing_id: UUID,
    session: SessionDependency,
    store: Annotated[FileStore, Depends(get_file_store)],
    author: Annotated[CurrentAuthor, Depends(require_author)],
    idempotency_key: IdempotencyKeyHeader = None,
) -> JSONResponse:
    stored = await service.publish_writing(
        session, store, author.id, writing_id, idempotency_key=idempotency_key
    )
    return JSONResponse(status_code=stored.status_code, content=stored.body)


@router.get("/writings/{writing_id}/publication", response_model=PublicationStatusDto)
async def get_publication_status(
    writing_id: UUID, session: SessionDependency
) -> PublicationStatusDto:
    return await service.get_publication_status(session, writing_id)


@router.post(
    "/writings/{writing_id}/publication/cancel-cleanup", response_model=PublicationStatusDto
)
async def cancel_cleanup(writing_id: UUID, session: SessionDependency) -> PublicationStatusDto:
    return await service.cancel_cleanup(session, writing_id)


@router.delete("/writings/{writing_id}/publication", response_model=PublicationStatusDto)
async def withdraw_publication(
    writing_id: UUID, session: SessionDependency
) -> PublicationStatusDto:
    return await service.withdraw_publication(session, writing_id)


@router.put("/editorial/featured-publication", status_code=status.HTTP_204_NO_CONTENT)
async def set_featured_publication(
    payload: FeaturedSelectionRequest, session: SessionDependency
) -> None:
    await service.set_featured_publication(session, payload.slug)


@router.delete("/editorial/featured-publication", status_code=status.HTTP_204_NO_CONTENT)
async def clear_featured_publication(session: SessionDependency) -> None:
    await service.clear_featured_publication(session)
