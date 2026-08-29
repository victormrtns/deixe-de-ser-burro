from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.service import normalize_origin, require_allowed_origin
from app.config import Settings, get_settings
from app.errors import AppError, app_error_handler


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("HTTP://Example.COM", ("http", "example.com", 80)),
        ("https://example.com:443/", ("https", "example.com", 443)),
        ("http://[::1]:8080", ("http", "::1", 8080)),
    ],
)
def test_origin_normalization_compares_scheme_host_and_effective_port(
    candidate: str, expected: tuple[str, str, int]
) -> None:
    assert normalize_origin(candidate) == expected


@pytest.mark.parametrize(
    "candidate",
    [
        "null",
        "ftp://example.com",
        "https://user@example.com",
        "https://example.com/private",
        "https://example.com?debug=true",
        "https://example.com#fragment",
        "https://example.com https://evil.example",
    ],
)
def test_origin_normalization_rejects_values_that_are_not_http_origins(candidate: str) -> None:
    assert normalize_origin(candidate) is None


async def _origin_client() -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url="postgresql+psycopg://user:password@localhost/entrelinhas",
        public_origin="https://example.com",
        files_root="./data/files",
    )
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[get_settings] = lambda: settings

    @app.api_route(
        "/private",
        methods=["GET", "POST"],
        dependencies=[Depends(require_allowed_origin)],
    )
    async def private() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


async def test_safe_method_does_not_require_origin() -> None:
    async for client in _origin_client():
        response = await client.get("/private")

    assert response.status_code == 200


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null"])
async def test_unsafe_method_rejects_missing_or_foreign_origin(origin: str | None) -> None:
    headers = {} if origin is None else {"Origin": origin}
    async for client in _origin_client():
        response = await client.post("/private", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


@pytest.mark.parametrize("origin", ["https://example.com", "https://EXAMPLE.com:443/"])
async def test_unsafe_method_accepts_the_configured_origin(origin: str) -> None:
    async for client in _origin_client():
        response = await client.post("/private", headers={"Origin": origin})

    assert response.status_code == 200
