from __future__ import annotations

import base64
import binascii
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.idempotency.service import StoredResponse, canonical_request_hash, execute_idempotent
from app.library.persistence import find_book
from app.writings import persistence
from app.writings.models import Writing, WritingVersion
from app.writings.schemas import (
    VersionReason,
    WorkspacePayload,
    WritingCreateRequest,
    WritingDto,
    WritingMetadataRequest,
    WritingSaveRequest,
    WritingVersionDto,
    WritingVersionPage,
)

CREATE_WRITING_OPERATION = "create_writing"
DEFAULT_VERSION_PAGE_SIZE = 50


async def create_writing(
    session: AsyncSession,
    author_id: UUID,
    book_id: UUID,
    request: WritingCreateRequest,
    *,
    idempotency_key: str | None = None,
) -> StoredResponse:
    if await find_book(session, book_id) is None:
        raise _not_found("Livro não encontrado.")

    async def perform_create() -> StoredResponse:
        writing = await persistence.insert_writing(
            session,
            book_id,
            title=request.title,
            source_range=request.source_range,
            markdown=request.markdown,
        )
        await persistence.insert_version(session, writing, reason="created")
        dto = _to_dto(writing)
        return StoredResponse(201, dto.model_dump(mode="json", by_alias=True), writing.id)

    if idempotency_key is None:
        response = await perform_create()
        await session.commit()
        return response

    return await execute_idempotent(
        session,
        author_id=author_id,
        operation=CREATE_WRITING_OPERATION,
        key=idempotency_key,
        request_hash=canonical_request_hash(request),
        action=perform_create,
    )


async def list_book_writings(session: AsyncSession, book_id: UUID) -> list[WritingDto]:
    if await find_book(session, book_id) is None:
        raise _not_found("Livro não encontrado.")
    return [_to_dto(writing) for writing in await persistence.list_writings(session, book_id)]


async def get_writing(session: AsyncSession, writing_id: UUID) -> WritingDto:
    return _to_dto(await _require_writing(session, writing_id))


async def get_workspace(session: AsyncSession, writing_id: UUID) -> WorkspacePayload:
    writing = await _require_writing(session, writing_id)
    # Chat, audio, and suggestions are deferred modules: the payload keeps their
    # collections present and empty so the frontend contract stays stable.
    return WorkspacePayload(writing=_to_dto(writing))


async def save_markdown(
    session: AsyncSession, writing_id: UUID, request: WritingSaveRequest
) -> WritingDto:
    writing = await _require_writing(session, writing_id)
    is_noop = (
        writing.version_number == request.expected_version and writing.markdown == request.markdown
    )
    if is_noop:
        return _to_dto(writing)
    return await _apply_versioned_change(
        session,
        writing_id,
        request.expected_version,
        {"markdown": request.markdown},
        reason="manual_save",
    )


async def update_metadata(
    session: AsyncSession, writing_id: UUID, request: WritingMetadataRequest
) -> WritingDto:
    writing = await _require_writing(session, writing_id)
    changes = {
        field: value
        for field, value in request.model_dump(exclude_none=True).items()
        if field != "expected_version" and value != getattr(writing, field)
    }
    if not changes:
        return _to_dto(writing)
    return await _apply_versioned_change(
        session, writing_id, request.expected_version, changes, reason="manual_save"
    )


async def delete_writing(session: AsyncSession, writing_id: UUID) -> None:
    writing = await _require_writing(session, writing_id)
    if await persistence.has_active_publication(session, writing_id):
        raise AppError(
            "state_conflict",
            "Retire a publicação ativa antes de excluir a escrita.",
            409,
        )
    await persistence.delete_writing(session, writing)
    await session.commit()


async def list_versions(
    session: AsyncSession,
    writing_id: UUID,
    *,
    cursor: str | None,
    limit: int = DEFAULT_VERSION_PAGE_SIZE,
) -> WritingVersionPage:
    await _require_writing(session, writing_id)
    before_version = _decode_cursor(cursor)
    versions = await persistence.list_versions(
        session, writing_id, limit=limit + 1, before_version=before_version
    )
    page = list(versions[:limit])
    next_cursor = _encode_cursor(page[-1].version_number) if len(versions) > limit else None
    return WritingVersionPage(
        items=[_to_version_dto(version) for version in page],
        next_cursor=next_cursor,
    )


async def restore_version(
    session: AsyncSession, writing_id: UUID, source_version: int, expected_version: int
) -> WritingDto:
    await _require_writing(session, writing_id)
    source = await persistence.find_version(session, writing_id, source_version)
    if source is None:
        raise _not_found("Versão não encontrada.")
    return await _apply_versioned_change(
        session,
        writing_id,
        expected_version,
        {"markdown": source.markdown, "title": source.title, "source_range": source.source_range},
        reason="restored",
    )


async def get_version(
    session: AsyncSession, writing_id: UUID, version_number: int
) -> WritingVersionDto:
    version = await persistence.find_version(session, writing_id, version_number)
    if version is None:
        raise _not_found("Versão não encontrada.")
    return _to_version_dto(version)


async def _apply_versioned_change(
    session: AsyncSession,
    writing_id: UUID,
    expected_version: int,
    changes: dict[str, str],
    *,
    reason: str,
) -> WritingDto:
    updated = await persistence.compare_and_swap(session, writing_id, expected_version, changes)
    if updated is None:
        current = await persistence.current_version(session, writing_id)
        raise AppError(
            "writing_version_conflict",
            "A escrita foi alterada em outra sessão.",
            409,
            {"currentVersion": current},
        )
    await persistence.insert_version(session, updated, reason=reason)
    await session.commit()
    return _to_dto(updated)


async def _require_writing(session: AsyncSession, writing_id: UUID) -> Writing:
    writing = await persistence.find_writing(session, writing_id)
    if writing is None:
        raise _not_found("Escrita não encontrada.")
    return writing


def _not_found(message: str) -> AppError:
    return AppError("resource_not_found", message, 404)


def _encode_cursor(version_number: int) -> str:
    return base64.urlsafe_b64encode(str(version_number).encode()).decode()


def _decode_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    try:
        version_number = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise AppError("validation_error", "Cursor de paginação inválido.", 400) from error
    if version_number < 1:
        raise AppError("validation_error", "Cursor de paginação inválido.", 400)
    return version_number


def _to_dto(writing: Writing) -> WritingDto:
    return WritingDto(
        id=writing.id,
        book_id=writing.book_id,
        title=writing.title,
        markdown=writing.markdown,
        source_range=writing.source_range,
        status=writing.status,
        version=writing.version_number,
        updated_at=writing.updated_at,
    )


def _to_version_dto(version: WritingVersion) -> WritingVersionDto:
    return WritingVersionDto(
        version=version.version_number,
        title=version.title,
        source_range=version.source_range,
        markdown=version.markdown,
        reason=cast(VersionReason, version.reason),
        created_at=version.created_at,
    )
