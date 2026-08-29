from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from app.observability import configure_logging
from tests.conftest import ALLOWED_ORIGIN

PRIVATE_MARKDOWN_SENTINEL = "PRIVATE_MARKDOWN_SENTINEL"
PASSWORD_SENTINEL = "PASSWORD_SENTINEL"


async def test_logs_never_include_private_request_content(
    client: AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging()

    await client.post(
        "/api/auth/session",
        json={"email": "author@example.com", "password": PASSWORD_SENTINEL},
    )
    await client.put(
        "/api/writings/00000000-0000-0000-0000-000000000000",
        headers={"Origin": ALLOWED_ORIGIN, "Cookie": "entrelinhas_session=token-sentinel"},
        json={"markdown": PRIVATE_MARKDOWN_SENTINEL, "expectedVersion": 1},
    )

    output = capsys.readouterr().out
    assert PRIVATE_MARKDOWN_SENTINEL not in output
    assert PASSWORD_SENTINEL not in output
    assert "token-sentinel" not in output
    assert "cookie" not in output.casefold()


async def test_every_log_line_is_parseable_json(
    client: AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging()

    await client.get("/api/public/landing")

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    for line in lines:
        record = json.loads(line)
        assert {"event", "level", "timestamp"} <= set(record)
