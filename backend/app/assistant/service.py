from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import budget, persistence
from app.assistant.context import (
    ComposedContext,
    ContextInput,
    ContextLimits,
    compose_context,
    load_editorial_policy,
)
from app.assistant.gateway import GatewayError, ModelGateway, ModelRequest, ModelUsage
from app.assistant.models import ConversationMessage, GenerationAttempt
from app.assistant.schemas import (
    ConversationDto,
    MemoryCreateRequest,
    MemoryItemDto,
    MessageDto,
    MessageRole,
    MessageState,
    UsageSummaryDto,
)
from app.config import Settings
from app.errors import AppError
from app.idempotency.service import StoredResponse, execute_idempotent
from app.writings.persistence import find_writing

SEND_OPERATION = "assistant_send_message"
RETRY_OPERATION = "assistant_retry_message"
# Deltas reach the client immediately but only touch the database in batches:
# whichever of these two comes first ends the batch.
FLUSH_INTERVAL_SECONDS = 1.0
FLUSH_BYTES = 4096

StreamFrame = tuple[str, dict[str, Any]]


@dataclass(frozen=True)
class Prepared:
    """Everything committed before the first external call."""

    writing_id: UUID
    attempt_id: UUID
    author_message_id: UUID
    assistant_message_id: UUID
    attempt_number: int
    model: str
    budget_limit: int
    request: ModelRequest
    replayed: bool


# --- reads -----------------------------------------------------------------


async def list_messages(session: AsyncSession, writing_id: UUID) -> list[MessageDto]:
    conversation = await persistence.find_conversation(session, writing_id)
    if conversation is None:
        return []
    stored = await persistence.list_messages(session, conversation.id)
    return [_to_message_dto(message, writing_id) for message in stored]


async def get_conversation(session: AsyncSession, writing_id: UUID) -> ConversationDto:
    await _require_writing(session, writing_id)
    return ConversationDto(messages=await list_messages(session, writing_id))


async def get_usage(session: AsyncSession, settings: Settings) -> UsageSummaryDto:
    return await budget.summary(session, limit=budget.limit_micros(settings))


# --- explicit memory -------------------------------------------------------


async def create_memory_item(
    session: AsyncSession, writing_id: UUID, request: MemoryCreateRequest
) -> MemoryItemDto:
    """Persist one memory item from text the author explicitly confirmed.

    No model call happens here: automatic extraction of preferences is out of
    scope, and only a completed answer of this writing may be the source.
    """
    await _require_writing(session, writing_id)
    if request.source_message_id is not None:
        await _require_completed_source(session, writing_id, request.source_message_id)
    item = await persistence.insert_memory_item(
        session,
        writing_id,
        kind=request.kind,
        content=request.content,
        source_message_id=request.source_message_id,
    )
    await session.commit()
    return MemoryItemDto(
        id=item.id, kind=request.kind, content=item.content, created_at=item.created_at
    )


async def _require_completed_source(
    session: AsyncSession, writing_id: UUID, source_message_id: UUID
) -> None:
    conversation = await persistence.find_conversation(session, writing_id)
    message = await persistence.find_message(session, source_message_id)
    invalid = (
        conversation is None
        or message is None
        or message.conversation_id != conversation.id
        or message.role != "assistant"
        or message.state != "completed"
    )
    if invalid:
        raise AppError(
            "invalid_memory_source",
            "A memória só pode vir de uma resposta concluída desta escrita.",
            422,
        )


# --- generation ------------------------------------------------------------


async def prepare_generation(
    session: AsyncSession,
    *,
    settings: Settings,
    writing_id: UUID,
    author_id: UUID,
    content: str | None = None,
    author_message_id: UUID | None = None,
    idempotency_key: str,
) -> Prepared:
    """Validate, reserve and persist. Nothing external happens before this returns."""
    writing = await _require_writing(session, writing_id)
    conversation = await persistence.get_or_create_conversation(session, writing_id)
    await session.commit()

    author_message = await _resolve_author_message(session, conversation.id, author_message_id)
    prompt = author_message.content if author_message is not None else (content or "")
    if not prompt.strip():
        raise AppError("validation_error", "A mensagem não pode ficar em branco.", 400)

    policy, instruction_version = load_editorial_policy()
    composed = compose_context(
        ContextInput(
            markdown=writing.markdown,
            memory=await persistence.list_active_memory(session, writing_id),
            completed_pairs=await persistence.list_recent_complete_pairs(session, conversation.id),
            current_prompt=prompt,
            editorial_policy=policy,
            instruction_version=instruction_version,
        ),
        ContextLimits(
            max_markdown_chars=settings.ai_max_markdown_chars,
            max_total_chars=settings.ai_max_context_chars,
        ),
    )

    limit = budget.limit_micros(settings)
    worst_case = budget.worst_case_micros(
        settings.ai_model,
        input_chars=len(composed.instructions) + len(composed.input),
        max_output_tokens=settings.ai_max_output_tokens,
    )
    await _reject_when_budget_is_already_gone(session, worst_case=worst_case, limit=limit)

    stored = await _persist_intent(
        session,
        settings=settings,
        author_id=author_id,
        writing_id=writing_id,
        conversation_id=conversation.id,
        instruction_version=composed.instruction_version,
        prompt=prompt,
        author_message=author_message,
        worst_case=worst_case,
        limit=limit,
        idempotency_key=idempotency_key,
    )
    return await _to_prepared(
        session, stored, writing_id=writing_id, settings=settings, composed=composed
    )


async def run_generation(
    session: AsyncSession, gateway: ModelGateway, prepared: Prepared
) -> AsyncIterator[StreamFrame]:
    """Stream the answer. This never raises: every ending is a terminal frame."""
    sequence = _Sequence()
    yield sequence.frame(
        "generation.started",
        prepared,
        messageId=str(prepared.assistant_message_id),
        attemptNumber=prepared.attempt_number,
    )

    if prepared.replayed:
        async for frame in _replay(session, prepared, sequence):
            yield frame
        return

    await persistence.start_attempt(session, prepared.attempt_id, model=prepared.model)
    await session.commit()

    buffer = _Buffer(session, prepared.assistant_message_id)
    started = time.perf_counter()
    usage: ModelUsage | None = None
    response_id: str | None = None
    truncated = False
    truncation_reason: str | None = None
    try:
        async for event in gateway.stream(prepared.request):
            if event.type == "started":
                response_id = event.response_id
            elif event.type == "text_delta" and event.delta:
                await buffer.add(event.delta)
                yield sequence.frame("response.delta", prepared, delta=event.delta)
            elif event.type == "completed":
                usage = event.usage
                truncated = event.truncated
                truncation_reason = event.truncation_reason
        if usage is None:
            raise GatewayError("provider_protocol_error")
    except GatewayError as failure:
        await buffer.flush()
        yield await _terminate_on_failure(session, prepared, sequence, failure, buffer, started)
        return
    except (asyncio.CancelledError, GeneratorExit):
        # The author stopped the generation or the connection dropped: whatever
        # arrived is preserved instead of discarded.
        await buffer.flush()
        await _finish(session, prepared, "interrupted", latency_ms=_elapsed_ms(started))
        await budget.release(session, prepared.attempt_id)
        await session.commit()
        raise

    await buffer.flush()
    cost = budget.actual_cost_micros(prepared.model, usage)
    # A truncated answer is not a finished one: it is stored as `interrupted`,
    # so it stays visible, never re-enters the next context, and can never be
    # the source of a memory item. The tokens were spent, so the cost settles.
    state: MessageState = "interrupted" if truncated else "completed"
    await _finish(
        session,
        prepared,
        state,
        latency_ms=_elapsed_ms(started),
        usage=usage,
        cost_micros=cost,
        response_id=response_id,
        error_code=f"response_truncated:{truncation_reason}" if truncated else None,
    )
    await budget.settle(session, prepared.attempt_id, actual_micros=cost)
    await session.commit()
    settled, reserved = await budget.totals(session)
    yield sequence.frame(
        "response.interrupted" if truncated else "response.completed",
        prepared,
        usage={
            "inputTokens": usage.input_tokens,
            "outputTokens": usage.output_tokens,
            "totalTokens": usage.total_tokens,
            "estimatedCostUsdMicros": cost,
            "budgetState": budget.state_for(settled + reserved, prepared.budget_limit),
        },
    )


# --- internals -------------------------------------------------------------


class _Sequence:
    def __init__(self) -> None:
        self.value = -1

    def frame(self, name: str, prepared: Prepared, **payload: Any) -> StreamFrame:
        self.value += 1
        return name, {
            "version": 1,
            "attemptId": str(prepared.attempt_id),
            "sequence": self.value,
            **payload,
        }


class _Buffer:
    """Holds deltas until a second or 4 KiB has passed, then persists them."""

    def __init__(self, session: AsyncSession, message_id: UUID) -> None:
        self._session = session
        self._message_id = message_id
        self._pending = ""
        self._last_flush = time.monotonic()
        self.received = 0

    async def add(self, delta: str) -> None:
        self._pending += delta
        self.received += len(delta)
        overdue = time.monotonic() - self._last_flush >= FLUSH_INTERVAL_SECONDS
        if len(self._pending.encode()) >= FLUSH_BYTES or overdue:
            await self.flush()

    async def flush(self) -> None:
        if not self._pending:
            return
        await persistence.append_assistant_content(self._session, self._message_id, self._pending)
        await self._session.commit()
        self._pending = ""
        self._last_flush = time.monotonic()


async def _replay(
    session: AsyncSession, prepared: Prepared, sequence: _Sequence
) -> AsyncIterator[StreamFrame]:
    """Serve a repeated idempotency key from storage: never a second paid call."""
    message = await persistence.find_message(session, prepared.assistant_message_id)
    content = message.content if message is not None else ""
    state = message.state if message is not None else "failed"
    if content:
        yield sequence.frame("response.delta", prepared, delta=content)
    if state == "completed":
        attempt = await persistence.find_attempt(session, prepared.attempt_id)
        yield sequence.frame(
            "response.completed",
            prepared,
            usage={
                "inputTokens": attempt.input_tokens if attempt else 0,
                "outputTokens": attempt.output_tokens if attempt else 0,
                "totalTokens": attempt.total_tokens if attempt else 0,
                "estimatedCostUsdMicros": 0,
                "budgetState": "normal",
            },
        )
    elif state == "interrupted":
        yield sequence.frame("response.interrupted", prepared)
    else:
        yield sequence.frame(
            "response.failed",
            prepared,
            error={
                "code": "ai_unavailable",
                "message": "A tentativa anterior com esta chave não foi concluída.",
                "requestId": "",
            },
        )


async def _terminate_on_failure(
    session: AsyncSession,
    prepared: Prepared,
    sequence: _Sequence,
    failure: GatewayError,
    buffer: _Buffer,
    started: float,
) -> StreamFrame:
    interrupted = buffer.received > 0
    state: MessageState = "interrupted" if interrupted else "failed"
    await _finish(
        session, prepared, state, latency_ms=_elapsed_ms(started), error_code=failure.code
    )
    await budget.release(session, prepared.attempt_id)
    await session.commit()
    if interrupted:
        return sequence.frame("response.interrupted", prepared)
    return sequence.frame(
        "response.failed",
        prepared,
        error={"code": failure.code, "message": failure.message, "requestId": ""},
    )


async def _finish(
    session: AsyncSession,
    prepared: Prepared,
    state: MessageState,
    *,
    latency_ms: int,
    usage: ModelUsage | None = None,
    cost_micros: int = 0,
    response_id: str | None = None,
    error_code: str | None = None,
) -> None:
    await persistence.finish_message(session, prepared.assistant_message_id, state)
    await persistence.finish_attempt(
        session,
        prepared.attempt_id,
        state=state,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        total_tokens=usage.total_tokens if usage else 0,
        cost_micros=cost_micros,
        latency_ms=latency_ms,
        provider_response_id=response_id,
        safe_error_code=error_code,
    )


async def _resolve_author_message(
    session: AsyncSession, conversation_id: UUID, author_message_id: UUID | None
) -> ConversationMessage | None:
    if author_message_id is None:
        return None
    message = await persistence.find_message(session, author_message_id)
    if message is None or message.conversation_id != conversation_id or message.role != "author":
        raise AppError("resource_not_found", "Mensagem não encontrada.", 404)
    return message


async def _reject_when_budget_is_already_gone(
    session: AsyncSession, *, worst_case: int, limit: int
) -> None:
    settled, reserved = await budget.totals(session)
    if settled + reserved + worst_case > limit:
        raise AppError("ai_budget_exceeded", "O orçamento de IA desta fase foi atingido.", 429)


async def _persist_intent(
    session: AsyncSession,
    *,
    settings: Settings,
    author_id: UUID,
    writing_id: UUID,
    conversation_id: UUID,
    instruction_version: str,
    prompt: str,
    author_message: ConversationMessage | None,
    worst_case: int,
    limit: int,
    idempotency_key: str,
) -> StoredResponse:
    async def action() -> StoredResponse:
        if author_message is None:
            attempt = await persistence.create_author_message_and_attempt(
                session,
                conversation_id,
                content=prompt,
                model=settings.ai_model,
                instruction_version=instruction_version,
            )
        else:
            attempt = await persistence.create_retry_attempt(
                session,
                conversation_id=conversation_id,
                author_message_id=author_message.id,
                model=settings.ai_model,
                instruction_version=instruction_version,
            )
        await budget.reserve(
            session,
            writing_id=writing_id,
            attempt_id=attempt.id,
            worst_case=worst_case,
            limit=limit,
        )
        return StoredResponse(200, _intent_body(attempt), attempt.id)

    operation = SEND_OPERATION if author_message is None else RETRY_OPERATION
    try:
        return await execute_idempotent(
            session,
            author_id=author_id,
            operation=operation,
            key=idempotency_key,
            request_hash=_intent_hash(writing_id, prompt),
            action=action,
        )
    except AppError:
        await session.rollback()
        raise


def _intent_body(attempt: GenerationAttempt) -> dict[str, Any]:
    return {
        "attemptId": str(attempt.id),
        "authorMessageId": str(attempt.author_message_id),
        "assistantMessageId": str(attempt.assistant_message_id),
        "attemptNumber": attempt.attempt_number,
    }


def _intent_hash(writing_id: UUID, prompt: str) -> str:
    from hashlib import sha256

    return sha256(f"{writing_id}\n{prompt}".encode()).hexdigest()


async def _to_prepared(
    session: AsyncSession,
    stored: StoredResponse,
    *,
    writing_id: UUID,
    settings: Settings,
    composed: ComposedContext,
) -> Prepared:
    body = stored.body
    attempt_id = UUID(str(body["attemptId"]))
    # A repeated idempotency key returns the winner's attempt. If that attempt
    # already left `pending`, the call was made once and must not be paid twice.
    attempt = await persistence.find_attempt(session, attempt_id)
    return Prepared(
        writing_id=writing_id,
        attempt_id=attempt_id,
        author_message_id=UUID(str(body["authorMessageId"])),
        assistant_message_id=UUID(str(body["assistantMessageId"])),
        attempt_number=int(body["attemptNumber"]),
        model=settings.ai_model,
        request=ModelRequest(
            instructions=composed.instructions,
            input=composed.input,
            model=settings.ai_model,
            max_output_tokens=settings.ai_max_output_tokens,
            reasoning_effort=settings.ai_reasoning_effort,
        ),
        budget_limit=budget.limit_micros(settings),
        replayed=attempt is not None and attempt.state != "pending",
    )


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _to_message_dto(message: ConversationMessage, writing_id: UUID) -> MessageDto:
    from typing import cast

    return MessageDto(
        id=message.id,
        writing_id=writing_id,
        role=cast(MessageRole, message.role),
        content=message.content,
        state=cast(MessageState, message.state),
        created_at=message.created_at,
    )


async def _require_writing(session: AsyncSession, writing_id: UUID) -> Any:
    writing = await find_writing(session, writing_id)
    if writing is None:
        raise AppError("resource_not_found", "Escrita não encontrada.", 404)
    return writing


__all__ = [
    "Prepared",
    "create_memory_item",
    "get_conversation",
    "get_usage",
    "list_messages",
    "prepare_generation",
    "run_generation",
]
