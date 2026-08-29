from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import utc_now
from app.errors import AppError
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
