from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

EventType = Literal["started", "text_delta", "completed"]


@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    input: str
    model: str
    max_output_tokens: int


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
