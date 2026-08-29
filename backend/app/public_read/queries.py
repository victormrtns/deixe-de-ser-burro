from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.public_read.schemas import (
    PublicArticleDetail,
    PublicArticleSummary,
    PublicBookDetail,
    PublicBookSummary,
    PublicLanding,
    PublicLatestArticle,
    PublicSourceBook,
)
from app.publishing.models import EditorialSettings, Publication, PublicationTopic

RECENT_ARTICLES_LIMIT = 5
PUBLIC_TOPICS_LIMIT = 3

# The allowlist: only these snapshot columns ever reach a public response.
_SUMMARY_COLUMNS = (
    Publication.id,
    Publication.slug,
    Publication.title,
    Publication.excerpt,
    Publication.published_at,
    Publication.reading_minutes,
    Publication.public_cover_path,
    Publication.book_slug,
    Publication.book_title,
    Publication.book_author,
)
_ArticleRow = Row[Any]


def _active_articles_query() -> Select[Any]:
    return (
        select(*_SUMMARY_COLUMNS)
        .where(Publication.state == "published")
        .order_by(Publication.published_at.desc(), Publication.slug.asc())
    )


async def get_landing(session: AsyncSession) -> PublicLanding:
    rows = (await session.execute(_active_articles_query())).all()
    featured_row = await _featured_row(session, rows)
    topics = await _topics_by_book_slug(session)
    return PublicLanding(
        featured_article=_to_summary(featured_row) if featured_row is not None else None,
        recent_articles=[_to_summary(row) for row in rows[:RECENT_ARTICLES_LIMIT]],
        published_books=_group_books(rows, topics),
    )


async def list_articles(session: AsyncSession) -> list[PublicArticleSummary]:
    rows = (await session.execute(_active_articles_query())).all()
    return [_to_summary(row) for row in rows]


async def find_article_detail(session: AsyncSession, slug: str) -> PublicArticleDetail | None:
    row = (
        await session.execute(
            select(*_SUMMARY_COLUMNS, Publication.markdown).where(
                Publication.state == "published", Publication.slug == slug
            )
        )
    ).one_or_none()
    if row is None:
        return None
    summary = _to_summary(row)
    return PublicArticleDetail(**summary.model_dump(), markdown=row.markdown)


async def list_books(session: AsyncSession) -> list[PublicBookSummary]:
    rows = (await session.execute(_active_articles_query())).all()
    return _group_books(rows, await _topics_by_book_slug(session))


async def find_book_detail(session: AsyncSession, slug: str) -> PublicBookDetail | None:
    rows = (
        await session.execute(_active_articles_query().where(Publication.book_slug == slug))
    ).all()
    if not rows:
        return None
    topics = await _topics_by_book_slug(session)
    summary = _group_books(rows, topics)[0]
    return PublicBookDetail(
        **summary.model_dump(),
        articles=[_to_summary(row) for row in rows],
    )


async def _featured_row(
    session: AsyncSession, active_rows: Sequence[_ArticleRow]
) -> _ArticleRow | None:
    if not active_rows:
        return None
    chosen_id = await session.scalar(
        select(EditorialSettings.featured_publication_id).where(
            EditorialSettings.featured_publication_id.is_not(None)
        )
    )
    if chosen_id is not None:
        for row in active_rows:
            if row.id == chosen_id:
                return row
    return active_rows[0]


async def _topics_by_book_slug(session: AsyncSession) -> dict[str, list[str]]:
    rows = await session.execute(
        select(Publication.book_slug, PublicationTopic.topic)
        .join(PublicationTopic, PublicationTopic.publication_id == Publication.id)
        .where(Publication.state == "published")
        .order_by(Publication.published_at.desc(), PublicationTopic.position.asc())
    )
    topics: dict[str, list[str]] = {}
    for book_slug, topic in rows.all():
        book_topics = topics.setdefault(book_slug, [])
        if topic not in book_topics and len(book_topics) < PUBLIC_TOPICS_LIMIT:
            book_topics.append(topic)
    return topics


def _group_books(
    rows: Sequence[_ArticleRow], topics: dict[str, list[str]]
) -> list[PublicBookSummary]:
    # Rows arrive newest first, so the first row of a book carries its most
    # recent snapshot metadata and latest article.
    books: dict[str, PublicBookSummary] = {}
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.book_slug] = counts.get(row.book_slug, 0) + 1
        if row.book_slug not in books:
            books[row.book_slug] = PublicBookSummary(
                slug=row.book_slug,
                title=row.book_title,
                author=row.book_author,
                cover_image_url=_cover_url(row.public_cover_path),
                published_article_count=0,
                latest_article=PublicLatestArticle(
                    slug=row.slug, title=row.title, published_at=row.published_at
                ),
                public_topics=topics.get(row.book_slug, []),
            )
    return [
        books[slug].model_copy(update={"published_article_count": counts[slug]}) for slug in books
    ]


def _to_summary(row: _ArticleRow) -> PublicArticleSummary:
    return PublicArticleSummary(
        slug=row.slug,
        title=row.title,
        excerpt=row.excerpt,
        published_at=row.published_at,
        reading_minutes=row.reading_minutes,
        cover_image_url=_cover_url(row.public_cover_path),
        source_book=PublicSourceBook(
            slug=row.book_slug, title=row.book_title, author=row.book_author
        ),
    )


def _cover_url(public_cover_path: str | None) -> str | None:
    return f"/api/public/files/{public_cover_path}" if public_cover_path else None
