from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas import ApiModel

MessageRole = Literal["author", "assistant"]
MessageState = Literal["streaming", "completed", "interrupted", "failed"]
MemoryKind = Literal["preference", "decision", "open_question"]
BudgetState = Literal["normal", "near_limit", "blocked"]


def _reject_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("não pode ficar em branco")
    return stripped


class MessageDto(ApiModel):
    id: UUID
    writing_id: UUID
    role: MessageRole
    content: str
    state: MessageState
    created_at: datetime


class ConversationDto(ApiModel):
    messages: list[MessageDto]


class SendMessageRequest(ApiModel):
    content: str = Field(min_length=1, max_length=8000)

    normalize_content = field_validator("content")(_reject_blank)


class MemoryCreateRequest(ApiModel):
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=2000)
    source_message_id: UUID | None = None

    normalize_content = field_validator("content")(_reject_blank)


class MemoryItemDto(ApiModel):
    id: UUID
    kind: MemoryKind
    content: str
    created_at: datetime


class UsageSummaryDto(ApiModel):
    period: str
    spent_usd_micros: int
    reserved_usd_micros: int
    limit_usd_micros: int
    limit_state: BudgetState


class GenerationUsageDto(ApiModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd_micros: int
    budget_state: BudgetState
