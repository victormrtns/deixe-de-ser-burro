from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALLOWED_ORIGIN

BOOK_KEYS = {"id", "title", "author", "coverUrl", "writingCount"}


async def test_book_responses_expose_exactly_the_frontend_contract(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(
        "/api/books",
        headers={"Origin": ALLOWED_ORIGIN, "Idempotency-Key": "book-contract"},
        json={"title": "Duna", "author": "Frank Herbert"},
    )
    listed = await authenticated_client.get("/api/books")
    detail = await authenticated_client.get(f"/api/books/{created.json()['id']}")

    assert set(created.json()) == BOOK_KEYS
    assert all(set(book) == BOOK_KEYS for book in listed.json())
    assert set(detail.json()) == BOOK_KEYS


async def test_validation_failures_use_the_stable_error_envelope(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/books", headers={"Origin": ALLOWED_ORIGIN}, json={"title": "Duna"}
    )
    body = response.json()

    assert response.status_code == 400
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert {"code", "message", "requestId"} <= set(body["error"])
    assert all({"field", "message"} == set(item) for item in body["error"]["details"]["errors"])
