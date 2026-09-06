from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import persistence
from app.assistant.models import (
    AiUsageEntry,
    Conversation,
    ConversationMessage,
    GenerationAttempt,
    WritingMemoryItem,
)
from app.auth.models import AuthorAccount
from app.library.models import Book
from app.writings.models import Writing


async def _writing(session: AsyncSession) -> Writing:
    book = Book(title="Duna", author="Frank Herbert")
    session.add(book)
    await session.flush()
    writing = Writing(
        book_id=book.id, title="O deserto", source_range="1–2", markdown="# O deserto"
    )
    session.add(writing)
    await session.flush()
    return writing


async def test_one_primary_conversation_per_writing(session: AsyncSession) -> None:
    writing = await _writing(session)
    first = await persistence.get_or_create_conversation(session, writing.id)
    await session.commit()

    second = await persistence.get_or_create_conversation(session, writing.id)
    await session.commit()

    assert second.id == first.id


async def test_attempt_state_is_checked(session: AsyncSession, author: AuthorAccount) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    author_message = ConversationMessage(
        conversation_id=conversation.id, role="author", content="Pergunta", state="completed"
    )
    assistant_message = ConversationMessage(
        conversation_id=conversation.id, role="assistant", content="", state="streaming"
    )
    session.add_all([author_message, assistant_message])
    await session.flush()

    session.add(
        GenerationAttempt(
            author_message_id=author_message.id,
            assistant_message_id=assistant_message.id,
            attempt_number=1,
            model="gpt-5-mini",
            instruction_version="parte-1-v1",
            state="unknown",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_author_message_cannot_be_blank(session: AsyncSession) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)

    session.add(
        ConversationMessage(
            conversation_id=conversation.id, role="author", content="   ", state="completed"
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_attempt_number_is_unique_per_author_message(session: AsyncSession) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    attempt = await persistence.create_author_message_and_attempt(
        session,
        conversation.id,
        content="Pergunta",
        model="gpt-5-mini",
        instruction_version="parte-1-v1",
    )
    await session.commit()

    session.add(
        GenerationAttempt(
            author_message_id=attempt.author_message_id,
            assistant_message_id=attempt.assistant_message_id,
            attempt_number=1,
            model="gpt-5-mini",
            instruction_version="parte-1-v1",
            state="pending",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_usage_entry_is_unique_per_attempt(session: AsyncSession) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    attempt = await persistence.create_author_message_and_attempt(
        session, conversation.id, content="Pergunta", model="m", instruction_version="v"
    )
    session.add(
        AiUsageEntry(
            writing_id=writing.id,
            generation_attempt_id=attempt.id,
            state="reserved",
            reserved_usd_micros=100,
        )
    )
    await session.flush()

    session.add(
        AiUsageEntry(
            writing_id=writing.id,
            generation_attempt_id=attempt.id,
            state="reserved",
            reserved_usd_micros=100,
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_memory_item_kind_is_checked(session: AsyncSession) -> None:
    writing = await _writing(session)
    session.add(WritingMemoryItem(writing_id=writing.id, kind="whatever", content="x"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_recent_complete_pairs_exclude_unfinished_answers(session: AsyncSession) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    for index in range(8):
        attempt = await persistence.create_author_message_and_attempt(
            session,
            conversation.id,
            content=f"Pergunta {index}",
            model="m",
            instruction_version="v",
        )
        state = "completed" if index < 7 else "interrupted"
        await persistence.append_assistant_content(
            session, attempt.assistant_message_id, f"Resposta {index}"
        )
        await persistence.finish_message(session, attempt.assistant_message_id, state)
        # One transaction per send, as in production: now() is transaction-scoped.
        await session.commit()

    pairs = await persistence.list_recent_complete_pairs(session, conversation.id, limit=6)

    assert [message.content for message in pairs] == [
        content for index in range(1, 7) for content in (f"Pergunta {index}", f"Resposta {index}")
    ]


async def test_active_memory_is_isolated_per_writing(session: AsyncSession) -> None:
    first = await _writing(session)
    second = await _writing(session)
    session.add_all(
        [
            WritingMemoryItem(writing_id=first.id, kind="preference", content="Tom seco"),
            WritingMemoryItem(writing_id=second.id, kind="preference", content="Tom lírico"),
        ]
    )
    await session.commit()

    items = await persistence.list_active_memory(session, first.id)

    assert [item.content for item in items] == ["Tom seco"]


async def test_deleting_a_writing_removes_its_conversation(session: AsyncSession) -> None:
    writing = await _writing(session)
    conversation = await persistence.get_or_create_conversation(session, writing.id)
    await session.commit()
    conversation_id = conversation.id

    await session.delete(writing)
    await session.commit()
    session.expunge_all()

    assert await session.get(Conversation, conversation_id) is None


async def test_missing_writing_cannot_hold_a_conversation(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await persistence.get_or_create_conversation(session, uuid4())
        await session.flush()
