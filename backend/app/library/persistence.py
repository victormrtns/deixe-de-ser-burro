from __future__ import annotations

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.models import Book
from app.writings.models import Writing


async def insert_book(session: AsyncSession, *, title: str, author: str) -> Book:
    book = Book(title=title, author=author)
    session.add(book)
    await session.flush()
    return book


async def find_book(session: AsyncSession, book_id: UUID) -> Book | None:
    return cast(Book | None, await session.get(Book, book_id))


async def list_books_with_writing_counts(session: AsyncSession) -> Sequence[tuple[Book, int]]:
    writing_counts = (
        select(Writing.book_id, func.count().label("writing_count"))
        .group_by(Writing.book_id)
        .subquery()
    )
    rows = await session.execute(
        select(Book, func.coalesce(writing_counts.c.writing_count, 0))
        .outerjoin(writing_counts, writing_counts.c.book_id == Book.id)
        .order_by(Book.created_at, Book.id)
    )
    return [(row[0], row[1]) for row in rows.all()]


async def count_writings(session: AsyncSession, book_id: UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Writing).where(Writing.book_id == book_id)
    )
    return count or 0


async def delete_book(session: AsyncSession, book: Book) -> None:
    await session.delete(book)
    await session.flush()
