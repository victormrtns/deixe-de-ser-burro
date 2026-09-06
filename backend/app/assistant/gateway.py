from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

EventType = Literal["started", "text_delta", "completed"]
# Kept as our own literal on purpose: the gateway contract must not import the
# provider's types. The adapter is where these two vocabularies have to agree.
ReasoningEffort = Literal["minimal", "low", "medium", "high"]


@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    input: str
    model: str
    max_output_tokens: int
    # Reasoning tokens are billed and counted inside `max_output_tokens`, so the
    # effort is part of how much answer actually fits in the ceiling.
    reasoning_effort: ReasoningEffort = "low"


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ModelEvent:
    type: EventType
    response_id: str | None = None
    delta: str | None = None
    usage: ModelUsage | None = None
    # A `completed` event whose answer the provider cut short. The usage is
    # final and billable either way, but the text is not a whole answer, so the
    # caller must not persist it as one.
    truncated: bool = False
    truncation_reason: str | None = None


class GatewayError(Exception):
    """A provider failure reduced to a safe internal code.

    The message is written for the author; provider payloads, prompts, and the
    API key never reach it.
    """

    def __init__(self, code: str, message: str = "O assistente falhou nesta tentativa.") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ModelGateway(Protocol):
    """The only model capabilities Parte 1 uses: text, streaming, and usage."""

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]: ...
