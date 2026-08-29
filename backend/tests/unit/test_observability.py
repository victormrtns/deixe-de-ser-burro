from __future__ import annotations

import json
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.errors import AppError, app_error_handler
from app.observability import RequestObservabilityMiddleware, configure_logging


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_middleware(RequestObservabilityMiddleware)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/conflict")
    async def conflict() -> None:
        raise AppError("writing_version_conflict", "Conflito.", 409)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("segredo interno que não deve vazar")

    return app


async def probe(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str]]:
    async with AsyncClient(
        transport=ASGITransport(app=build_app(), raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(path, headers=headers or {})
    return response.status_code, dict(response.headers)


async def test_a_valid_incoming_request_id_is_propagated() -> None:
    _, headers = await probe("/ok", {"X-Request-ID": "abcd1234-request"})

    assert headers["x-request-id"] == "abcd1234-request"


@pytest.mark.parametrize("incoming", ["", "x", "a" * 100, "has space", "bad!chars"])
async def test_an_invalid_request_id_is_replaced_with_a_uuid(incoming: str) -> None:
    _, headers = await probe("/ok", {"X-Request-ID": incoming} if incoming else None)

    assert UUID(headers["x-request-id"])


async def test_the_error_envelope_shares_the_response_request_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_app(), raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/conflict")

    assert response.status_code == 409
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]


async def test_requests_emit_one_parseable_json_event(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging()
    await probe("/ok", {"X-Request-ID": "abcd1234-request"})

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    completed = [event for event in events if event.get("event") == "request_completed"]

    assert completed, events
    record = completed[-1]
    assert record["request_id"] == "abcd1234-request"
    assert record["method"] == "GET"
    assert record["route"] == "/ok"
    assert record["status"] == 200
    assert record["service"] == "entrelinhas-api"
    assert "duration_ms" in record
    assert "timestamp" in record


async def test_unhandled_failures_log_only_the_exception_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging()
    status, _ = await probe("/boom")

    output = capsys.readouterr().out
    assert status == 500
    assert "segredo interno" not in output
    assert "RuntimeError" in output
