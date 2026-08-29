from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}
PRIVATE_KEYS = {
    "id",
    "writingId",
    "writingVersionId",
    "version",
    "status",
    "state",
    "cleanupAt",
    "cleanupDueAt",
    "messages",
    "audio",
    "transcript",
    "suggestions",
    "privateCoverPath",
    "updatedAt",
    "createdAt",
}


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys |= walk_keys(nested)
    elif isinstance(value, list):
        for item in value:
            keys |= walk_keys(item)
    return keys


async def publish_article(client: AsyncClient, *, title: str, key: str) -> str:
    book = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": title, "sourceRange": "Cap. 1", "markdown": f"# {title}"},
    )
    published = await client.post(
        f"/api/writings/{writing.json()['id']}/publication",
        headers={**MUTATION_HEADERS, "Idempotency-Key": key},
    )
    assert published.status_code == 201
    return str(published.json()["slug"])


async def test_the_public_tree_contains_no_private_keys(
    authenticated_client: AsyncClient, client: AsyncClient
) -> None:
    slug = await publish_article(authenticated_client, title="O deserto", key="publish-1")

    for path in (
        "/api/public/landing",
        "/api/public/articles",
        f"/api/public/articles/{slug}",
        "/api/public/books",
        "/api/public/books/duna",
    ):
        body = (await client.get(path)).json()
        leaked = walk_keys(body) & PRIVATE_KEYS
        assert not leaked, f"{path} leaked {leaked}"


async def test_public_routes_do_not_require_authentication(
    authenticated_client: AsyncClient, client: AsyncClient
) -> None:
    slug = await publish_article(authenticated_client, title="O deserto", key="publish-1")

    article = await client.get(f"/api/public/articles/{slug}")

    assert article.status_code == 200
    assert article.json()["markdown"] == "# O deserto"
