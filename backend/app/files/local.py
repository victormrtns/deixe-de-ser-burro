from __future__ import annotations

import asyncio
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from PIL import Image

from app.config import Settings, get_settings
from app.files.service import (
    FileStore,
    FileTooLarge,
    InvalidFileKey,
    StoredFile,
    UnsupportedImage,
    media_type_for_key,
)

DEFAULT_MAX_PIXELS = 25_000_000
PRIVATE_COVER_PREFIX = "covers/private"
PUBLIC_COVER_PREFIX = "covers/public"
_ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}
_KEY_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class LocalFileStore:
    """Stores validated images under one root with atomic writes."""

    def __init__(self, root: Path, *, max_bytes: int, max_pixels: int = DEFAULT_MAX_PIXELS) -> None:
        self._root = root
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels

    def path_for(self, key: str) -> Path:
        segments = key.split("/")
        if not key or any(_KEY_SEGMENT.fullmatch(segment) is None for segment in segments):
            raise InvalidFileKey(f"malformed file key: {key!r}")
        path = self._root.joinpath(*segments)
        if not path.resolve().is_relative_to(self._root.resolve()):
            raise InvalidFileKey(f"file key escapes the store root: {key!r}")
        return path

    async def put_private_cover(self, content: bytes) -> StoredFile:
        return await asyncio.to_thread(self._reencode_and_store, content)

    async def copy_public(self, private_key: str) -> StoredFile:
        content = await self.open(private_key)
        extension = Path(private_key).suffix
        key = f"{PUBLIC_COVER_PREFIX}/{uuid4().hex}{extension}"
        await asyncio.to_thread(self._write_atomically, self.path_for(key), content)
        return StoredFile(key, self._known_media_type(key))

    async def open(self, key: str) -> bytes:
        path = self.path_for(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as error:
            raise InvalidFileKey(f"no stored file for key: {key!r}") from error

    async def delete(self, key: str) -> None:
        path = self.path_for(key)
        await asyncio.to_thread(path.unlink, True)

    def _reencode_and_store(self, content: bytes) -> StoredFile:
        if len(content) > self._max_bytes:
            raise FileTooLarge(f"upload of {len(content)} bytes exceeds {self._max_bytes}")

        image = self._decoded_image(content)
        extension = _ALLOWED_FORMATS[image.format or ""]
        key = f"{PRIVATE_COVER_PREFIX}/{uuid4().hex}{extension}"
        self._write_atomically(self.path_for(key), self._clean_copy_bytes(image))
        return StoredFile(key, self._known_media_type(key))

    def _decoded_image(self, content: bytes) -> Image.Image:
        try:
            image = Image.open(BytesIO(content))
        except Exception as error:
            raise UnsupportedImage("content is not a decodable image") from error
        if image.format not in _ALLOWED_FORMATS:
            raise UnsupportedImage(f"unsupported image format: {image.format}")
        if image.width * image.height > self._max_pixels:
            raise FileTooLarge(
                f"image of {image.width}x{image.height} pixels exceeds {self._max_pixels}"
            )
        try:
            image.load()
        except Exception as error:
            raise UnsupportedImage("image body could not be decoded") from error
        return image

    @staticmethod
    def _clean_copy_bytes(image: Image.Image) -> bytes:
        # Re-encoding a pixel-only copy drops EXIF and other embedded metadata.
        clean = image.copy()
        clean.info = {}
        buffer = BytesIO()
        clean.save(buffer, format=image.format)
        return buffer.getvalue()

    @staticmethod
    def _write_atomically(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".tmp-{uuid4().hex}")
        try:
            with open(temporary, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _known_media_type(key: str) -> str:
        media_type = media_type_for_key(key)
        if media_type is None:
            raise InvalidFileKey(f"key without a known media type: {key!r}")
        return media_type


def get_file_store(settings: Annotated[Settings, Depends(get_settings)]) -> FileStore:
    return LocalFileStore(settings.files_root, max_bytes=settings.max_cover_bytes)
