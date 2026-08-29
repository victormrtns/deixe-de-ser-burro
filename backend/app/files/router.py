from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.files.local import get_file_store
from app.files.service import FileStore, InvalidFileKey, media_type_for_key

router = APIRouter(prefix="/api/public/files", tags=["public"])

_ACTIVE_PUBLICATION_REFERENCES_KEY = text(
    "SELECT 1 FROM publications WHERE state = 'published' AND public_cover_path = :key"
)


def _public_file_not_found() -> AppError:
    return AppError("resource_not_found", "Arquivo não encontrado.", 404)


@router.get("/{key:path}")
async def read_public_file(
    key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    store: Annotated[FileStore, Depends(get_file_store)],
) -> Response:
    referenced = await session.scalar(_ACTIVE_PUBLICATION_REFERENCES_KEY, {"key": key})
    media_type = media_type_for_key(key)
    if referenced is None or media_type is None:
        raise _public_file_not_found()

    try:
        content = await store.open(key)
    except InvalidFileKey as error:
        raise _public_file_not_found() from error
    return Response(content=content, media_type=media_type)
