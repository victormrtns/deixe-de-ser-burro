from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.public_read import queries
from app.public_read.schemas import (
    PublicArticleDetail,
    PublicArticleSummary,
    PublicBookDetail,
    PublicBookSummary,
    PublicLanding,
)

router = APIRouter(prefix="/api/public", tags=["public"])

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def _not_found(message: str) -> AppError:
    return AppError("resource_not_found", message, 404)


@router.get("/landing", response_model=PublicLanding)
async def get_landing(session: SessionDependency) -> PublicLanding:
    return await queries.get_landing(session)


@router.get("/articles", response_model=list[PublicArticleSummary])
async def list_articles(session: SessionDependency) -> list[PublicArticleSummary]:
    return await queries.list_articles(session)


@router.get("/articles/{slug}", response_model=PublicArticleDetail)
async def get_article(slug: str, session: SessionDependency) -> PublicArticleDetail:
    article = await queries.find_article_detail(session, slug)
    if article is None:
        raise _not_found("Artigo não encontrado.")
    return article


@router.get("/books", response_model=list[PublicBookSummary])
async def list_books(session: SessionDependency) -> list[PublicBookSummary]:
    return await queries.list_books(session)


@router.get("/books/{slug}", response_model=PublicBookDetail)
async def get_book(slug: str, session: SessionDependency) -> PublicBookDetail:
    book = await queries.find_book_detail(session, slug)
    if book is None:
        raise _not_found("Livro não encontrado.")
    return book
