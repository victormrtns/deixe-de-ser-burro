from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import utc_now
from app.errors import AppError
from app.files.service import (
    FileStore,
    FileTooLarge,
    StoredFile,
    UnsupportedImage,
    media_type_for_key,
)
from app.idempotency.service import StoredResponse, canonical_request_hash, execute_idempotent
from app.library import persistence
from app.library.models import Book
from app.library.schemas import BookCreateRequest, BookSummary, BookUpdateRequest

CREATE_BOOK_OPERATION = "create_book"


async def list_books(session: AsyncSession) -> list[BookSummary]:
    books = await persistence.list_books_with_writing_counts(session)
    return [_summarize(book, writing_count) for book, writing_count in books]


async def create_book(
    session: AsyncSession,
    author_id: UUID,
    request: BookCreateRequest,
    *,
    idempotency_key: str | None = None,
) -> StoredResponse:
    async def perform_create() -> StoredResponse:
        book = await persistence.insert_book(session, title=request.title, author=request.author)
        summary = _summarize(book, writing_count=0)
        return StoredResponse(201, summary.model_dump(mode="json", by_alias=True), book.id)

    if idempotency_key is None:
        response = await perform_create()
        await session.commit()
        return response

    return await execute_idempotent(
        session,
        author_id=author_id,
        operation=CREATE_BOOK_OPERATION,
        key=idempotency_key,
        request_hash=canonical_request_hash(request),
        action=perform_create,
    )


async def get_book(session: AsyncSession, book_id: UUID) -> BookSummary:
    book = await _require_book(session, book_id)
    return _summarize(book, await persistence.count_writings(session, book.id))


async def update_book(
    session: AsyncSession, book_id: UUID, request: BookUpdateRequest
) -> BookSummary:
    book = await _require_book(session, book_id)
    changes = request.model_dump(exclude_none=True)
    if changes:
        for field_name, value in changes.items():
            setattr(book, field_name, value)
        book.updated_at = utc_now()
        await session.commit()
    return _summarize(book, await persistence.count_writings(session, book.id))


async def delete_book(session: AsyncSession, book_id: UUID) -> None:
    book = await _require_book(session, book_id)
    if await persistence.count_writings(session, book.id):
        raise _book_not_empty()
    try:
        await persistence.delete_book(session, book)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise _book_not_empty() from error


async def upload_cover(
    session: AsyncSession, store: FileStore, book_id: UUID, content: bytes
) -> BookSummary:
    book = await _require_book(session, book_id)
    stored = await _validated_cover(store, content)

    previous_cover = book.private_cover_path
    book.private_cover_path = stored.key
    book.updated_at = utc_now()
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await store.delete(stored.key)
        raise
    if previous_cover:
        await store.delete(previous_cover)
    return _summarize(book, await persistence.count_writings(session, book.id))


async def remove_cover(session: AsyncSession, store: FileStore, book_id: UUID) -> None:
    book = await _require_book(session, book_id)
    previous_cover = book.private_cover_path
    if previous_cover is None:
        return
    book.private_cover_path = None
    book.updated_at = utc_now()
    await session.commit()
    await store.delete(previous_cover)


async def open_cover(session: AsyncSession, store: FileStore, book_id: UUID) -> tuple[bytes, str]:
    book = await _require_book(session, book_id)
    if book.private_cover_path is None:
        raise AppError("resource_not_found", "O livro não possui capa.", 404)
    content = await store.open(book.private_cover_path)
    return content, _cover_media_type(book.private_cover_path)


async def _validated_cover(store: FileStore, content: bytes) -> StoredFile:
    try:
        return await store.put_private_cover(content)
    except FileTooLarge as error:
        raise AppError(
            "upload_too_large", "A imagem excede o tamanho máximo permitido.", 413
        ) from error
    except UnsupportedImage as error:
        raise AppError(
            "unsupported_media_type", "Envie uma imagem PNG ou JPEG válida.", 415
        ) from error


def _cover_media_type(cover_path: str) -> str:
    media_type = media_type_for_key(cover_path)
    if media_type is None:
        raise AppError("resource_not_found", "O livro não possui capa.", 404)
    return media_type


async def _require_book(session: AsyncSession, book_id: UUID) -> Book:
    book = await persistence.find_book(session, book_id)
    if book is None:
        raise AppError("resource_not_found", "Livro não encontrado.", 404)
    return book


def _book_not_empty() -> AppError:
    return AppError(
        "book_not_empty",
        "Exclua as escritas do livro antes de removê-lo.",
        409,
    )


def _summarize(book: Book, writing_count: int) -> BookSummary:
    cover_url = f"/api/books/{book.id}/cover" if book.private_cover_path else None
    return BookSummary(
        id=book.id,
        title=book.title,
        author=book.author,
        cover_url=cover_url,
        writing_count=writing_count,
    )
