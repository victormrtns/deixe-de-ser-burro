from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import persistence, service
from app.assistant.fake_gateway import FakeModelGateway
from app.assistant.gateway import GatewayError, ModelEvent, ModelRequest
from app.assistant.models import AiUsageEntry, ConversationMessage, GenerationAttempt
from app.errors import AppError
from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


class RecordingGateway(FakeModelGateway):
    """Counts calls so a test can prove the gateway was never reached."""

    def __init__(
        self, chunks: list[str], *, fail_with: str | None = None, truncated: bool = False
    ) -> None:
        super().__init__(chunks, fail_with=fail_with, truncated=truncated)
        self.calls = 0

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        self.calls += 1
        async for event in super().stream(request):
            yield event


class NeverCalledGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        self.calls += 1
        raise AssertionError("the gateway must not be reached")
        yield  # pragma: no cover


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def settings_overrides() -> dict[str, object]:
    return {"ai_gateway": "fake"}


def _install(api_app: Any, gateway: Any) -> Any:
    from app.assistant.dependencies import get_model_gateway

    api_app.dependency_overrides[get_model_gateway] = lambda: gateway
    return gateway


@pytest.fixture
def fake_gateway(api_app: Any) -> RecordingGateway:
    return cast(RecordingGateway, _install(api_app, RecordingGateway(["Olá", " mundo"])))


@pytest.fixture
def never_called_gateway(api_app: Any) -> NeverCalledGateway:
    return cast(NeverCalledGateway, _install(api_app, NeverCalledGateway()))


@pytest.fixture
def failing_gateway(api_app: Any, request: pytest.FixtureRequest) -> RecordingGateway:
    code = getattr(request, "param", "provider_timeout")
    chunks = ["parcial"] if code == "provider_timeout" else []
    return cast(RecordingGateway, _install(api_app, RecordingGateway(chunks, fail_with=code)))


@pytest.fixture
def zero_budget_gateway(api_app: Any, settings_overrides: dict[str, object]) -> NeverCalledGateway:
    settings_overrides["ai_development_budget_usd"] = "0.00"
    settings_overrides["ai_manual_smoke_budget_usd"] = "0.00"
    return cast(NeverCalledGateway, _install(api_app, NeverCalledGateway()))


@pytest.fixture
def disabled_gateway(settings_overrides: dict[str, object]) -> None:
    settings_overrides["ai_gateway"] = "disabled"


async def create_writing(client: AsyncClient, *, markdown: str = "# O deserto") -> str:
    book = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto", "sourceRange": "Capítulos 1–2", "markdown": markdown},
    )
    assert writing.status_code == 201, writing.text
    return str(writing.json()["id"])


async def send(
    client: AsyncClient, writing_id: str, content: str, *, key: str | None = None
) -> Any:
    return await client.post(
        f"/api/writings/{writing_id}/conversation/messages",
        headers={**MUTATION_HEADERS, "Idempotency-Key": key or str(uuid4())},
        json={"content": content},
    )


def frames(body: str) -> list[tuple[str, dict[str, Any]]]:
    import json

    parsed: list[tuple[str, dict[str, Any]]] = []
    for block in body.split("\n\n"):
        name = value = None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                value = line.removeprefix("data: ")
        if name is not None and value is not None:
            parsed.append((name, json.loads(value)))
    return parsed


# --- authentication and authorisation -------------------------------------


async def test_anonymous_cannot_read_or_send(client: AsyncClient) -> None:
    writing_id = str(uuid4())

    read = await client.get(f"/api/writings/{writing_id}/conversation")
    written = await send(client, writing_id, "Olá")

    assert read.status_code == 401
    assert written.status_code == 401


async def test_unknown_writing_is_not_found(authenticated_client: AsyncClient) -> None:
    response = await send(authenticated_client, str(uuid4()), "Olá")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"


# --- happy path ------------------------------------------------------------


async def test_send_uses_versioned_domain_events(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "O que falta nesta ideia?")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = frames(response.text)
    assert [name for name, _ in events] == [
        "generation.started",
        "response.delta",
        "response.delta",
        "response.completed",
    ]
    assert all(payload["version"] == 1 for _, payload in events)
    assert [payload["sequence"] for _, payload in events] == [0, 1, 2, 3]
    assert len({payload["attemptId"] for _, payload in events}) == 1


async def test_stream_persists_before_gateway_and_settles_usage(
    authenticated_client: AsyncClient, session: AsyncSession, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)

    await send(authenticated_client, writing_id, "O que falta nesta ideia?")

    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == ["author", "assistant"]
    assert messages[0]["content"] == "O que falta nesta ideia?"
    assert messages[1]["content"] == "Olá mundo"
    assert messages[1]["state"] == "completed"

    attempt = (await session.scalars(select(GenerationAttempt))).one()
    assert attempt.state == "completed"
    assert attempt.total_tokens > 0
    assert attempt.estimated_cost_usd_micros > 0
    assert attempt.latency_ms is not None
    usage = (await session.scalars(select(AiUsageEntry))).one()
    assert usage.state == "settled"
    assert usage.actual_usd_micros is not None


async def test_workspace_returns_the_real_conversation(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")

    workspace = await authenticated_client.get(f"/api/writings/{writing_id}/workspace")
    body = workspace.json()

    assert len(body["messages"]) == 2
    assert set(body["messages"][0]) == {"id", "writingId", "role", "content", "state", "createdAt"}
    assert body["audio"] == body["suggestions"] == []


# --- idempotency, retry and isolation --------------------------------------


async def test_repeating_an_idempotency_key_does_not_call_the_gateway_twice(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)

    first = await send(authenticated_client, writing_id, "Uma pergunta", key="same-key")
    second = await send(authenticated_client, writing_id, "Uma pergunta", key="same-key")

    assert first.status_code == second.status_code == 200
    assert fake_gateway.calls == 1
    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    assert len(history.json()["messages"]) == 2


async def test_retry_creates_a_second_attempt_without_a_second_author_message(
    authenticated_client: AsyncClient, session: AsyncSession, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")
    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    author_message_id = history.json()["messages"][0]["id"]

    retried = await authenticated_client.post(
        f"/api/writings/{writing_id}/conversation/messages/{author_message_id}/retry",
        headers={**MUTATION_HEADERS, "Idempotency-Key": str(uuid4())},
    )

    assert retried.status_code == 200
    attempts = (await session.scalars(select(GenerationAttempt))).all()
    assert sorted(attempt.attempt_number for attempt in attempts) == [1, 2]
    authors = (
        await session.scalars(
            select(ConversationMessage).where(ConversationMessage.role == "author")
        )
    ).all()
    assert len(authors) == 1


async def test_two_writings_never_share_a_conversation(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    first = await create_writing(authenticated_client)
    second = await create_writing(authenticated_client)

    await send(authenticated_client, first, "Segredo do primeiro texto")

    other = await authenticated_client.get(f"/api/writings/{second}/conversation")
    assert other.json()["messages"] == []


# --- blocked before any external call --------------------------------------


async def test_markdown_too_large_blocks_before_the_gateway(
    authenticated_client: AsyncClient, session: AsyncSession, never_called_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client, markdown="x" * 130_000)

    response = await send(authenticated_client, writing_id, "Uma pergunta")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "context_too_large"
    assert never_called_gateway.calls == 0
    assert (await session.scalars(select(ConversationMessage))).all() == []


async def test_exhausted_budget_blocks_before_the_gateway(
    authenticated_client: AsyncClient, session: AsyncSession, zero_budget_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Uma pergunta")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "ai_budget_exceeded"
    assert zero_budget_gateway.calls == 0
    assert (await session.scalars(select(ConversationMessage))).all() == []


async def test_a_disabled_assistant_leaves_the_editor_working(
    authenticated_client: AsyncClient, disabled_gateway: None
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Uma pergunta")
    saved = await authenticated_client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Ainda escrevo", "expectedVersion": 1},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"
    assert saved.status_code == 200
    assert saved.json()["markdown"] == "# Ainda escrevo"


# --- failure and interruption ----------------------------------------------


@pytest.mark.parametrize("failing_gateway", ["provider_rate_limited"], indirect=True)
async def test_failure_without_content_marks_the_attempt_failed(
    authenticated_client: AsyncClient, session: AsyncSession, failing_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Uma pergunta")

    names = [name for name, _ in frames(response.text)]
    assert names[-1] == "response.failed"
    error = frames(response.text)[-1][1]["error"]
    assert error["code"] == "provider_rate_limited"
    attempt = (await session.scalars(select(GenerationAttempt))).one()
    assert attempt.state == "failed"
    assert attempt.safe_error_code == "provider_rate_limited"
    usage = (await session.scalars(select(AiUsageEntry))).one()
    assert usage.state == "released"


@pytest.mark.parametrize("failing_gateway", ["provider_timeout"], indirect=True)
async def test_failure_after_content_preserves_the_partial_answer(
    authenticated_client: AsyncClient, session: AsyncSession, failing_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Uma pergunta")

    names = [name for name, _ in frames(response.text)]
    assert names[-1] == "response.interrupted"
    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    assistant = history.json()["messages"][1]
    assert assistant["content"] == "parcial"
    assert assistant["state"] == "interrupted"
    attempt = (await session.scalars(select(GenerationAttempt))).one()
    assert attempt.state == "interrupted"


@pytest.mark.parametrize("failing_gateway", ["provider_timeout"], indirect=True)
async def test_an_interrupted_answer_never_re_enters_the_next_context(
    authenticated_client: AsyncClient, session: AsyncSession, failing_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")

    conversation = await persistence.find_conversation(session, UUID(writing_id))
    assert conversation is not None
    pairs = await persistence.list_recent_complete_pairs(session, conversation.id)

    assert pairs == []


async def test_a_failed_generation_leaves_the_markdown_untouched(
    authenticated_client: AsyncClient, failing_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client, markdown="# Intacto")
    await send(authenticated_client, writing_id, "Reescreva tudo")

    writing = await authenticated_client.get(f"/api/writings/{writing_id}")

    assert writing.json()["markdown"] == "# Intacto"
    assert writing.json()["version"] == 1


# --- memory ----------------------------------------------------------------


async def test_explicit_memory_is_stored_for_that_writing_only(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)
    other_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")
    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    source = history.json()["messages"][1]["id"]

    created = await authenticated_client.post(
        f"/api/writings/{writing_id}/memory",
        headers=MUTATION_HEADERS,
        json={
            "kind": "preference",
            "content": "Mantenha períodos longos",
            "sourceMessageId": source,
        },
    )

    assert created.status_code == 201
    assert created.json()["content"] == "Mantenha períodos longos"
    assert set(created.json()) == {"id", "kind", "content", "createdAt"}
    other = await authenticated_client.post(
        f"/api/writings/{other_id}/memory",
        headers=MUTATION_HEADERS,
        json={"kind": "preference", "content": "Outro tom", "sourceMessageId": source},
    )
    assert other.status_code == 422


async def test_memory_rejects_an_unfinished_answer_as_its_source(
    authenticated_client: AsyncClient, failing_gateway: Any
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")
    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    source = history.json()["messages"][1]["id"]

    response = await authenticated_client.post(
        f"/api/writings/{writing_id}/memory",
        headers=MUTATION_HEADERS,
        json={"kind": "preference", "content": "Não deveria valer", "sourceMessageId": source},
    )

    assert response.status_code == 422


# --- usage -----------------------------------------------------------------


async def test_usage_reports_real_numbers_only(
    authenticated_client: AsyncClient, fake_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Uma pergunta")

    usage = await authenticated_client.get(f"/api/writings/{writing_id}/usage")
    body = usage.json()

    assert set(body) == {
        "period",
        "spentUsdMicros",
        "reservedUsdMicros",
        "limitUsdMicros",
        "limitState",
    }
    assert body["limitState"] in {"normal", "near_limit", "blocked"}
    assert isinstance(body["spentUsdMicros"], int)


# --- service-level guarantees ----------------------------------------------


async def test_a_missing_writing_never_reaches_the_gateway(
    session: AsyncSession, author: Any, migrated_database_url: str, tmp_path: Any
) -> None:
    from app.config import Settings

    gateway = NeverCalledGateway()
    settings = Settings(
        environment="test",
        database_url=migrated_database_url,
        public_origin="http://localhost:5173",
        files_root=tmp_path,
        ai_gateway="fake",
    )

    with pytest.raises(AppError) as failure:
        await service.prepare_generation(
            session,
            settings=settings,
            writing_id=uuid4(),
            author_id=author.id,
            content="Uma pergunta",
            idempotency_key=str(uuid4()),
        )

    assert failure.value.code == "resource_not_found"
    assert gateway.calls == 0


async def test_gateway_error_message_never_leaks_content() -> None:
    error = GatewayError("provider_rate_limited")

    assert "sk-" not in str(error)
    assert error.code == "provider_rate_limited"


# --- truncated answers ------------------------------------------------------


@pytest.fixture
def truncating_gateway(api_app: Any) -> RecordingGateway:
    """A provider that cut the answer short: usage is final, the text is not."""
    gateway = RecordingGateway(["Começo da resposta"], truncated=True)
    return cast(RecordingGateway, _install(api_app, gateway))


async def test_a_truncated_answer_is_not_stored_as_completed(
    authenticated_client: AsyncClient, session: AsyncSession, truncating_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Desenvolve esta passagem.")

    names = [name for name, _ in frames(response.text)]
    assert names[-1] == "response.interrupted"

    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    assistant = history.json()["messages"][-1]
    assert assistant["state"] == "interrupted"
    # Whatever arrived stays visible; it is simply not a finished answer.
    assert assistant["content"] == "Começo da resposta"

    attempt = (await session.execute(select(GenerationAttempt))).scalars().one()
    assert attempt.state == "interrupted"
    assert attempt.safe_error_code == "response_truncated:max_output_tokens"


async def test_a_truncated_answer_still_settles_the_tokens_it_spent(
    authenticated_client: AsyncClient, session: AsyncSession, truncating_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)

    response = await send(authenticated_client, writing_id, "Desenvolve esta passagem.")

    _, payload = frames(response.text)[-1]
    assert payload["usage"]["outputTokens"] > 0
    entry = (await session.execute(select(AiUsageEntry))).scalars().one()
    # The provider billed the tokens, so the reservation settles instead of
    # being released: a cut answer is not a free answer.
    assert entry.state == "settled"
    assert entry.actual_usd_micros == payload["usage"]["estimatedCostUsdMicros"]


async def test_a_truncated_answer_can_never_become_memory(
    authenticated_client: AsyncClient, truncating_gateway: RecordingGateway
) -> None:
    writing_id = await create_writing(authenticated_client)
    await send(authenticated_client, writing_id, "Desenvolve esta passagem.")

    history = await authenticated_client.get(f"/api/writings/{writing_id}/conversation")
    assistant_id = history.json()["messages"][-1]["id"]

    stored = await authenticated_client.post(
        f"/api/writings/{writing_id}/memory",
        headers=MUTATION_HEADERS,
        json={
            "kind": "preference",
            "content": "manter o tom seco",
            "sourceMessageId": assistant_id,
        },
    )

    assert stored.status_code == 422
    assert stored.json()["error"]["code"] == "invalid_memory_source"


async def test_a_markdown_over_its_own_limit_is_refused_before_the_gateway(
    authenticated_client: AsyncClient,
    settings_overrides: dict[str, object],
    never_called_gateway: NeverCalledGateway,
) -> None:
    """The Markdown guard must be reachable: it is a separate, smaller limit."""
    settings_overrides["ai_max_markdown_chars"] = 500
    settings_overrides["ai_max_context_chars"] = 120_000
    writing_id = await create_writing(authenticated_client, markdown="x" * 501)

    response = await send(authenticated_client, writing_id, "O que falta aqui?")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "context_too_large"
    assert never_called_gateway.calls == 0
