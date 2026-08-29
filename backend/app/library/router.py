from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import CurrentAuthor
from app.auth.service import require_allowed_origin, require_author
from app.db import get_session
from app.library import service
from app.library.schemas import BookCreateRequest, BookSummary, BookUpdateRequest

router = APIRouter(
    prefix="/api/books",
    tags=["library"],
    dependencies=[Depends(require_allowed_origin), Depends(require_author)],
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.get("", response_model=list[BookSummary])
async def list_books(session: SessionDependency) -> list[BookSummary]:
    return await service.list_books(session)


@router.post("", response_model=BookSummary, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreateRequest,
    session: SessionDependency,
    author: Annotated[CurrentAuthor, Depends(require_author)],
    idempotency_key: IdempotencyKeyHeader = None,
) -> JSONResponse:
    stored = await service.create_book(session, author.id, payload, idempotency_key=idempotency_key)
    return JSONResponse(status_code=stored.status_code, content=stored.body)


@router.get("/{book_id}", response_model=BookSummary)
async def get_book(book_id: UUID, session: SessionDependency) -> BookSummary:
    return await service.get_book(session, book_id)


@router.patch("/{book_id}", response_model=BookSummary)
async def update_book(
    book_id: UUID, payload: BookUpdateRequest, session: SessionDependency
) -> BookSummary:
    return await service.update_book(session, book_id, payload)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: UUID, session: SessionDependency) -> None:
    await service.delete_book(session, book_id)
