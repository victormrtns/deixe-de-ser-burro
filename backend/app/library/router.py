from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import CurrentAuthor
from app.auth.service import require_allowed_origin, require_author
from app.config import Settings, get_settings
from app.db import get_session
from app.files.local import get_file_store
from app.files.service import FileStore
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


FileStoreDependency = Annotated[FileStore, Depends(get_file_store)]


@router.put("/{book_id}/cover", response_model=BookSummary)
async def upload_book_cover(
    book_id: UUID,
    file: UploadFile,
    session: SessionDependency,
    store: FileStoreDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> BookSummary:
    content = await file.read(settings.max_cover_bytes + 1)
    return await service.upload_cover(session, store, book_id, content)


@router.delete("/{book_id}/cover", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_cover(
    book_id: UUID, session: SessionDependency, store: FileStoreDependency
) -> None:
    await service.remove_cover(session, store, book_id)


@router.get("/{book_id}/cover")
async def read_book_cover(
    book_id: UUID, session: SessionDependency, store: FileStoreDependency
) -> Response:
    content, media_type = await service.open_cover(session, store, book_id)
    return Response(content=content, media_type=media_type)
