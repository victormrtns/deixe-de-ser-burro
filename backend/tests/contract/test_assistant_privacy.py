from __future__ import annotations

import json
import logging
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.assistant.fake_gateway import FakeModelGateway
from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}
SECRET_MARKDOWN = "# Segredo editorial do autor sobre Duna"
SECRET_PROMPT = "Confidencial: o que falta nesta ideia sobre o deserto?"
SECRET_ANSWER = "Resposta privada do assistente"


@pytest.fixture
def settings_overrides() -> dict[str, object]:
    return {"ai_gateway": "fake"}


@pytest.fixture
def gateway(api_app: FastAPI) -> FakeModelGateway:
    from app.assistant.dependencies import get_model_gateway

    fake = FakeModelGateway([SECRET_ANSWER])
    api_app.dependency_overrides[get_model_gateway] = lambda: fake
    return fake


async def _writing_with_a_conversation(client: AsyncClient) -> str:
    book = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto", "sourceRange": "Capítulos 1–2", "markdown": SECRET_MARKDOWN},
    )
    writing_id = str(writing.json()["id"])
    await client.post(
        f"/api/writings/{writing_id}/conversation/messages",
        headers={**MUTATION_HEADERS, "Idempotency-Key": str(uuid4())},
        json={"content": SECRET_PROMPT},
    )
    await client.post(
        f"/api/writings/{writing_id}/memory",
        headers=MUTATION_HEADERS,
        json={"kind": "preference", "content": "Preferência privada desta escrita"},
    )
    return writing_id


async def test_public_routes_never_expose_conversation_artifacts(
    authenticated_client: AsyncClient, gateway: FakeModelGateway
) -> None:
    await _writing_with_a_conversation(authenticated_client)

    landing = await authenticated_client.get("/api/public/landing")
    articles = await authenticated_client.get("/api/public/articles")
    books = await authenticated_client.get("/api/public/books")

    for response in (landing, articles, books):
        body = response.text
        assert SECRET_MARKDOWN not in body
        assert SECRET_PROMPT not in body
        assert SECRET_ANSWER not in body
        assert "Preferência privada" not in body
        for private in ("attemptId", "conversation", "memory", "usdMicros", "instructionVersion"):
            assert private not in body


async def test_anonymous_readers_cannot_reach_any_assistant_route(
    client: AsyncClient, authenticated_client: AsyncClient, gateway: FakeModelGateway
) -> None:
    writing_id = await _writing_with_a_conversation(authenticated_client)
    await authenticated_client.delete("/api/auth/session", headers=MUTATION_HEADERS)

    routes = [
        await client.get(f"/api/writings/{writing_id}/conversation"),
        await client.get(f"/api/writings/{writing_id}/usage"),
        await client.post(
            f"/api/writings/{writing_id}/memory",
            headers=MUTATION_HEADERS,
            json={"kind": "preference", "content": "x"},
        ),
    ]

    for response in routes:
        assert response.status_code == 401
        assert SECRET_MARKDOWN not in response.text
        assert SECRET_ANSWER not in response.text


async def test_request_logs_carry_no_private_content(
    authenticated_client: AsyncClient,
    gateway: FakeModelGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        await _writing_with_a_conversation(authenticated_client)

    emitted = "\n".join(record.getMessage() for record in caplog.records)

    assert SECRET_MARKDOWN not in emitted
    assert SECRET_PROMPT not in emitted
    assert SECRET_ANSWER not in emitted
    assert "Preferência privada" not in emitted


async def test_pre_stream_errors_use_the_stable_envelope(
    authenticated_client: AsyncClient, api_app: FastAPI, settings_overrides: dict[str, object]
) -> None:
    settings_overrides["ai_gateway"] = "disabled"
    book = await authenticated_client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await authenticated_client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto", "sourceRange": "1–2", "markdown": SECRET_MARKDOWN},
    )

    response = await authenticated_client.post(
        f"/api/writings/{writing.json()['id']}/conversation/messages",
        headers={**MUTATION_HEADERS, "Idempotency-Key": str(uuid4())},
        json={"content": SECRET_PROMPT},
    )

    assert response.status_code == 503
    assert not response.headers["content-type"].startswith("text/event-stream")
    envelope = cast(dict[str, Any], response.json())["error"]
    assert set(envelope) >= {"code", "message", "requestId"}
    assert envelope["code"] == "ai_unavailable"
    assert SECRET_PROMPT not in json.dumps(envelope)


async def test_the_openapi_document_never_names_the_api_key(api_app: FastAPI) -> None:
    document = json.dumps(api_app.openapi())

    for forbidden in ("openai_api_key", "OPENAI_API_KEY", "apiKey", "sk-"):
        assert forbidden not in document
