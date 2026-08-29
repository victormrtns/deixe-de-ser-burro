from __future__ import annotations

from datetime import datetime

from app.schemas import ApiModel


class PublicSourceBook(ApiModel):
    slug: str
    title: str
    author: str


class PublicArticleSummary(ApiModel):
    slug: str
    title: str
    excerpt: str
    published_at: datetime
    reading_minutes: int
    cover_image_url: str | None = None
    source_book: PublicSourceBook


class PublicArticleDetail(PublicArticleSummary):
    markdown: str


class PublicLatestArticle(ApiModel):
    slug: str
    title: str
    published_at: datetime


class PublicBookSummary(ApiModel):
    slug: str
    title: str
    author: str
    cover_image_url: str | None = None
    published_article_count: int
    latest_article: PublicLatestArticle
    public_topics: list[str]


class PublicBookDetail(PublicBookSummary):
    articles: list[PublicArticleSummary]


class PublicLanding(ApiModel):
    featured_article: PublicArticleSummary | None
    recent_articles: list[PublicArticleSummary]
    published_books: list[PublicBookSummary]
