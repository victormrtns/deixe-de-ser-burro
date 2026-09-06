from __future__ import annotations

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.assistant.models import (
    AiUsageEntry,
    Conversation,
    ConversationMessage,
    GenerationAttempt,
    WritingMemoryItem,
)
from app.clock import utc_now

DEFAULT_PAIR_WINDOW = 6


async def get_or_create_conversation(session: AsyncSession, writing_id: UUID) -> Conversation:
    """Return the writing's single conversation, creating it on first use."""
    statement = (
        insert(Conversation)
        .values(writing_id=writing_id)
        .on_conflict_do_nothing(index_elements=[Conversation.writing_id])
        .returning(Conversation)
    )
    created = (await session.execute(statement)).scalar_one_or_none()
    if created is not None:
        return created
    existing = await session.scalar(
        select(Conversation).where(Conversation.writing_id == writing_id)
    )
    assert existing is not None
    return existing


async def find_conversation(session: AsyncSession, writing_id: UUID) -> Conversation | None:
    return cast(
        Conversation | None,
        await session.scalar(select(Conversation).where(Conversation.writing_id == writing_id)),
    )


async def list_messages(
    session: AsyncSession, conversation_id: UUID
) -> Sequence[ConversationMessage]:
    return (
        await session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at, ConversationMessage.role.desc())
        )
    ).all()


def _completed_pairs_query(conversation_id: UUID, limit: int) -> Select[tuple[GenerationAttempt]]:
    author = aliased(ConversationMessage)
    assistant = aliased(ConversationMessage)
    return (
        select(GenerationAttempt)
        .join(author, GenerationAttempt.author_message_id == author.id)
        .join(assistant, GenerationAttempt.assistant_message_id == assistant.id)
        .where(author.conversation_id == conversation_id, assistant.state == "completed")
        .order_by(author.created_at.desc())
        .limit(limit)
    )


async def list_recent_complete_pairs(
    session: AsyncSession, conversation_id: UUID, limit: int = DEFAULT_PAIR_WINDOW
) -> list[ConversationMessage]:
    """Return the last `limit` completed author/assistant pairs, oldest first.

    Interrupted and failed answers stay visible in the history but never re-enter
    a new call's context.
    """
    attempts = list((await session.scalars(_completed_pairs_query(conversation_id, limit))).all())
    pairs: list[ConversationMessage] = []
    for attempt in reversed(attempts):
        author = await session.get(ConversationMessage, attempt.author_message_id)
        assistant = await session.get(ConversationMessage, attempt.assistant_message_id)
        if author is not None and assistant is not None:
            pairs.extend([author, assistant])
    return pairs


async def list_active_memory(
    session: AsyncSession, writing_id: UUID
) -> Sequence[WritingMemoryItem]:
    return (
        await session.scalars(
            select(WritingMemoryItem)
            .where(WritingMemoryItem.writing_id == writing_id, WritingMemoryItem.active.is_(True))
            .order_by(WritingMemoryItem.created_at, WritingMemoryItem.id)
        )
    ).all()


async def insert_memory_item(
    session: AsyncSession,
    writing_id: UUID,
    *,
    kind: str,
    content: str,
    source_message_id: UUID | None,
) -> WritingMemoryItem:
    item = WritingMemoryItem(
        writing_id=writing_id, kind=kind, content=content, source_message_id=source_message_id
    )
    session.add(item)
    await session.flush()
    return item


async def create_author_message_and_attempt(
    session: AsyncSession,
    conversation_id: UUID,
    *,
    content: str,
    model: str,
    instruction_version: str,
) -> GenerationAttempt:
    """Persist the author's message, the empty answer, and attempt number 1."""
    author_message = ConversationMessage(
        conversation_id=conversation_id, role="author", content=content, state="completed"
    )
    session.add(author_message)
    await session.flush()
    return await create_retry_attempt(
        session,
        conversation_id=conversation_id,
        author_message_id=author_message.id,
        model=model,
        instruction_version=instruction_version,
    )


async def create_retry_attempt(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    author_message_id: UUID,
    model: str,
    instruction_version: str,
) -> GenerationAttempt:
    """Add another auditable attempt for an existing author message."""
    assistant_message = ConversationMessage(
        conversation_id=conversation_id, role="assistant", content="", state="streaming"
    )
    session.add(assistant_message)
    await session.flush()
    attempt = GenerationAttempt(
        author_message_id=author_message_id,
        assistant_message_id=assistant_message.id,
        attempt_number=await next_attempt_number(session, author_message_id),
        model=model,
        instruction_version=instruction_version,
        state="pending",
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def next_attempt_number(session: AsyncSession, author_message_id: UUID) -> int:
    highest = await session.scalar(
        select(func.max(GenerationAttempt.attempt_number)).where(
            GenerationAttempt.author_message_id == author_message_id
        )
    )
    return int(highest or 0) + 1


async def find_attempt(session: AsyncSession, attempt_id: UUID) -> GenerationAttempt | None:
    return cast(GenerationAttempt | None, await session.get(GenerationAttempt, attempt_id))


async def find_message(session: AsyncSession, message_id: UUID) -> ConversationMessage | None:
    return cast(ConversationMessage | None, await session.get(ConversationMessage, message_id))


async def append_assistant_content(session: AsyncSession, message_id: UUID, content: str) -> None:
    """Append a buffered chunk without ever re-sending the whole answer."""
    if not content:
        return
    await session.execute(
        update(ConversationMessage)
        .where(ConversationMessage.id == message_id)
        .values(
            content=ConversationMessage.content + content,
            updated_at=utc_now(),
        )
    )


async def finish_message(session: AsyncSession, message_id: UUID, state: str) -> None:
    await session.execute(
        update(ConversationMessage)
        .where(ConversationMessage.id == message_id)
        .values(state=state, updated_at=utc_now())
    )


async def start_attempt(session: AsyncSession, attempt_id: UUID, *, model: str) -> None:
    await session.execute(
        update(GenerationAttempt)
        .where(GenerationAttempt.id == attempt_id, GenerationAttempt.state == "pending")
        .values(state="streaming", model=model, started_at=utc_now())
    )


async def finish_attempt(
    session: AsyncSession,
    attempt_id: UUID,
    *,
    state: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cost_micros: int = 0,
    latency_ms: int | None = None,
    provider_response_id: str | None = None,
    safe_error_code: str | None = None,
) -> None:
    """Move an attempt to a terminal state exactly once."""
    await session.execute(
        update(GenerationAttempt)
        .where(
            GenerationAttempt.id == attempt_id,
            GenerationAttempt.state.in_(("pending", "streaming")),
        )
        .values(
            state=state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd_micros=cost_micros,
            latency_ms=latency_ms,
            provider_response_id=provider_response_id,
            safe_error_code=safe_error_code,
            finished_at=utc_now(),
        )
    )


async def find_usage_entry(session: AsyncSession, attempt_id: UUID) -> AiUsageEntry | None:
    return cast(
        AiUsageEntry | None,
        await session.scalar(
            select(AiUsageEntry).where(AiUsageEntry.generation_attempt_id == attempt_id)
        ),
    )
