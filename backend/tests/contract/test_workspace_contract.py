from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALLOWED_ORIGIN

WRITING_KEYS = {
    "id",
    "bookId",
    "title",
    "markdown",
    "sourceRange",
    "status",
    "version",
    "updatedAt",
}


async def create_writing(client: AsyncClient) -> dict[str, object]:
    book = await client.post(
        "/api/books",
        headers={"Origin": ALLOWED_ORIGIN},
        json={"title": "Duna", "author": "Frank Herbert"},
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers={"Origin": ALLOWED_ORIGIN},
        json={"title": "O deserto", "sourceRange": "Capítulos 1–2", "markdown": "# O deserto"},
    )
    assert writing.status_code == 201
    return writing.json()


async def test_writing_responses_expose_exactly_the_frontend_contract(
    authenticated_client: AsyncClient,
) -> None:
    created = await create_writing(authenticated_client)
    detail = await authenticated_client.get(f"/api/writings/{created['id']}")

    assert set(created) == WRITING_KEYS
    assert set(detail.json()) == WRITING_KEYS


async def test_workspace_keeps_deferred_collections_empty(
    authenticated_client: AsyncClient,
) -> None:
    created = await create_writing(authenticated_client)

    workspace = await authenticated_client.get(f"/api/writings/{created['id']}/workspace")
    body = workspace.json()

    assert workspace.status_code == 200
    assert set(body) == {"writing", "messages", "audio", "suggestions"}
    assert set(body["writing"]) == WRITING_KEYS
    assert body["messages"] == body["audio"] == body["suggestions"] == []
