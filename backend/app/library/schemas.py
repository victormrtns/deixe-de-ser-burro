from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator

from app.schemas import ApiModel

TEXT_FIELD_MAX_LENGTH = 500


def _reject_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("não pode ficar em branco")
    return stripped


class BookCreateRequest(ApiModel):
    title: str = Field(min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)
    author: str = Field(min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)

    normalize_text = field_validator("title", "author")(_reject_blank)


class BookUpdateRequest(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)
    author: str | None = Field(default=None, min_length=1, max_length=TEXT_FIELD_MAX_LENGTH)

    @field_validator("title", "author")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _reject_blank(value)


class BookSummary(ApiModel):
    id: UUID
    title: str
    author: str
    cover_url: str | None = None
    writing_count: int
