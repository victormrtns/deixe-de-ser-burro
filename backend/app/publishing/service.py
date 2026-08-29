from __future__ import annotations

import math
import re
import unicodedata
from datetime import timedelta
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.files.service import FileStore
from app.idempotency.service import StoredResponse, canonical_request_hash, execute_idempotent
from app.library.persistence import find_book
from app.publishing import persistence
from app.publishing.models import Publication
from app.publishing.schemas import PublicationStatusDto, PublishResult
from app.schemas import ApiModel
from app.writings.models import Writing
from app.writings.persistence import find_version

PUBLISH_OPERATION = "publish_writing"
CLEANUP_WINDOW = timedelta(days=3)
EXCERPT_LIMIT = 220
WORDS_PER_MINUTE = 200
SLUG_FALLBACK = "artigo"

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_HEADING_LINE = re.compile(r"^#{1,6}\s.*$", re.MULTILINE)
_EMPHASIS_MARKS = re.compile(r"[*_>]")
_SLUG_WORDS = re.compile(r"[a-z0-9]+")


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    words = _SLUG_WORDS.findall(ascii_title.lower())
    return "-".join(words) or SLUG_FALLBACK


def excerpt_from_markdown(markdown: str) -> str:
    plain = _CODE_FENCE.sub(" ", markdown)
    plain = _IMAGE.sub(" ", plain)
    plain = _LINK.sub(r"\1", plain)
    plain = _INLINE_CODE.sub(r"\1", plain)
    plain = _HEADING_LINE.sub(" ", plain)
    plain = _EMPHASIS_MARKS.sub("", plain)
    normalized = " ".join(plain.split())
    if len(normalized) <= EXCERPT_LIMIT:
        return normalized
    return normalized[: EXCERPT_LIMIT - 1].rsplit(" ", 1)[0] + "…"


def reading_minutes(markdown: str) -> int:
    return max(1, math.ceil(len(markdown.split()) / WORDS_PER_MINUTE))


class _PublishPayload(ApiModel):
    """Hashing payload: publishing has no body, only the target writing."""

    writing_id: UUID


async def publish_writing(
    session: AsyncSession,
    store: FileStore,
    author_id: UUID,
    writing_id: UUID,
    *,
    idempotency_key: str | None,
) -> StoredResponse:
    if not idempotency_key:
        raise AppError("validation_error", "Publicar exige o cabeçalho Idempotency-Key.", 400)

    async def perform_publish() -> StoredResponse:
        publication = await _create_snapshot(session, store, writing_id)
        result = PublishResult(
            slug=publication.slug,
            published_at=publication.published_at,
            cleanup_at=publication.cleanup_due_at,
        )
        return StoredResponse(201, result.model_dump(mode="json", by_alias=True), publication.id)

    return await execute_idempotent(
        session,
        author_id=author_id,
        operation=PUBLISH_OPERATION,
        key=idempotency_key,
        request_hash=canonical_request_hash(_PublishPayload(writing_id=writing_id)),
        action=perform_publish,
    )


async def get_publication_status(session: AsyncSession, writing_id: UUID) -> PublicationStatusDto:
    publication = await persistence.latest_publication(session, writing_id)
    if publication is None:
        raise AppError("resource_not_found", "A escrita não possui publicação.", 404)
    return _to_status_dto(publication)


async def cancel_cleanup(session: AsyncSession, writing_id: UUID) -> PublicationStatusDto:
    publication, writing = await _lock_active_publication_pair(session, writing_id)
    if publication.cleanup_completed_at is not None:
        raise AppError("state_conflict", "A limpeza desta publicação já foi concluída.", 409)

    now = await persistence.database_now(session)
    if publication.cleanup_cancelled_at is None:
        publication.cleanup_cancelled_at = now
        publication.updated_at = now
    writing.status = "published"
    await session.commit()
    return _to_status_dto(publication)


async def withdraw_publication(session: AsyncSession, writing_id: UUID) -> PublicationStatusDto:
    publication, writing = await _lock_active_publication_pair(session, writing_id)
    now = await persistence.database_now(session)
    publication.state = "withdrawn"
    if publication.cleanup_cancelled_at is None and publication.cleanup_completed_at is None:
        publication.cleanup_cancelled_at = now
    publication.updated_at = now
    writing.status = "draft"
    await session.commit()
    return _to_status_dto(publication)


async def set_featured_publication(session: AsyncSession, slug: str) -> None:
    publication = await persistence.find_active_by_slug(session, slug)
    if publication is None:
        raise AppError("resource_not_found", "Não há publicação ativa com este slug.", 404)
    settings = await persistence.lock_editorial_settings(session)
    settings.featured_publication_id = publication.id
    settings.updated_at = await persistence.database_now(session)
    await session.commit()


async def clear_featured_publication(session: AsyncSession) -> None:
    settings = await persistence.lock_editorial_settings(session)
    settings.featured_publication_id = None
    settings.updated_at = await persistence.database_now(session)
    await session.commit()


async def _create_snapshot(
    session: AsyncSession, store: FileStore, writing_id: UUID
) -> Publication:
    writing = await persistence.lock_writing(session, writing_id)
    if writing is None:
        raise AppError("resource_not_found", "Escrita não encontrada.", 404)
    if await persistence.active_publication(session, writing_id) is not None:
        raise AppError("publication_already_active", "A escrita já está publicada.", 409)

    book = await find_book(session, writing.book_id)
    if book is None:
        raise AppError("resource_not_found", "Livro não encontrado.", 404)
    version = await find_version(session, writing_id, writing.version_number)
    if version is None:
        raise AppError("internal_error", "A escrita não possui a versão corrente.", 500)

    # The cover is copied before the snapshot insert so its public key can be
    # frozen with the row; a failed insert deletes the copy again. A copy left
    # behind by a lost idempotency race is swept by the maintenance command.
    public_cover_path = (
        (await store.copy_public(book.private_cover_path)).key if book.private_cover_path else None
    )
    try:
        now = await persistence.database_now(session)
        publication = await persistence.insert_publication(
            session,
            writing_id=writing.id,
            writing_version_id=version.id,
            slug=await _unique_slug(session, writing.title),
            title=writing.title,
            markdown=writing.markdown,
            excerpt=excerpt_from_markdown(writing.markdown),
            reading_minutes=reading_minutes(writing.markdown),
            published_at=now,
            book_slug=slugify(book.title),
            book_title=book.title,
            book_author=book.author,
            public_cover_path=public_cover_path,
            cleanup_due_at=now + CLEANUP_WINDOW,
        )
        writing.status = "cleanup_scheduled"
    except Exception:
        if public_cover_path is not None:
            await store.delete(public_cover_path)
        raise
    return publication


async def _lock_active_publication_pair(
    session: AsyncSession, writing_id: UUID
) -> tuple[Publication, Writing]:
    writing = await persistence.lock_writing(session, writing_id)
    if writing is None:
        raise AppError("resource_not_found", "Escrita não encontrada.", 404)
    publication = await persistence.lock_active_publication(session, writing_id)
    if publication is None:
        raise AppError("resource_not_found", "A escrita não possui publicação ativa.", 404)
    return publication, writing


async def _unique_slug(session: AsyncSession, title: str) -> str:
    base = slugify(title)
    candidate = base
    suffix = 2
    # ponytail: linear probing; fine for a single author's catalog size.
    while await persistence.is_slug_taken(session, candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _to_status_dto(publication: Publication) -> PublicationStatusDto:
    return PublicationStatusDto(
        slug=publication.slug,
        state=cast(Literal["published", "withdrawn"], publication.state),
        published_at=publication.published_at,
        cleanup_at=publication.cleanup_due_at,
        cleanup_cancelled_at=publication.cleanup_cancelled_at,
        cleanup_completed_at=publication.cleanup_completed_at,
    )
