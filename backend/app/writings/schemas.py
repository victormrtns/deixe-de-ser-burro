from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas import ApiModel

TEXT_FIELD_MAX_LENGTH = 500
VersionReason = Literal["created", "manual_save", "restored", "published"]


def _reject_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("não pode ficar em branco")
    return stripped


class WritingCreateRequest(ApiModel):
    title: str = Field(min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)
    source_range: str = Field(min_length=1, max_length=2000)
    markdown: str = ""

    normalize_text = field_validator("title", "source_range")(_reject_blank)


class WritingSaveRequest(ApiModel):
    markdown: str
    expected_version: int = Field(ge=1)


class WritingMetadataRequest(ApiModel):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)
    source_range: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("title", "source_range")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _reject_blank(value)


class WritingDto(ApiModel):
    id: UUID
    book_id: UUID
    title: str
    markdown: str
    source_range: str
    status: str
    version: int
    updated_at: datetime


class WritingVersionDto(ApiModel):
    version: int
    title: str
    source_range: str
    markdown: str
    reason: VersionReason
    created_at: datetime


class WritingVersionPage(ApiModel):
    items: list[WritingVersionDto]
    next_cursor: str | None = None


class WorkspacePayload(ApiModel):
    writing: WritingDto
    messages: list[Any] = Field(default_factory=list)
    audio: list[Any] = Field(default_factory=list)
    suggestions: list[Any] = Field(default_factory=list)
