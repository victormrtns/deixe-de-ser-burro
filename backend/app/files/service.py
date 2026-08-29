from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class InvalidFileKey(Exception):
    """The key is malformed, escapes the store root, or names no stored file."""


class UnsupportedImage(Exception):
    """The uploaded content is not a decodable PNG or JPEG image."""


class FileTooLarge(Exception):
    """The upload exceeds the configured byte or pixel budget."""


@dataclass(frozen=True)
class StoredFile:
    key: str
    media_type: str


MEDIA_TYPES_BY_EXTENSION = {".png": "image/png", ".jpg": "image/jpeg"}


def media_type_for_key(key: str) -> str | None:
    for extension, media_type in MEDIA_TYPES_BY_EXTENSION.items():
        if key.endswith(extension):
            return media_type
    return None


class FileStore(Protocol):
    async def put_private_cover(self, content: bytes) -> StoredFile: ...

    async def copy_public(self, private_key: str) -> StoredFile: ...

    async def open(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...
