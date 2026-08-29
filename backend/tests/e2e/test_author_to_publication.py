from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthorAccount
from tests.conftest import ALLOWED_ORIGIN, AUTHOR_EMAIL, AUTHOR_PASSWORD

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}
PRIVATE_KEYS = {
    "id",
    "writingId",
    "writingVersionId",
    "version",
    "status",
    "cleanupAt",
    "messages",
    "audio",
    "transcript",
    "suggestions",
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


async def test_author_to_frozen_publication(
    client: AsyncClient, author: AuthorAccount, session: AsyncSession
) -> None:
    login = await client.post(
        "/api/auth/session", json={"email": AUTHOR_EMAIL, "password": AUTHOR_PASSWORD}
    )
    assert login.status_code == 200

    book = await client.post(
        "/api/books",
        headers={**MUTATION_HEADERS, "Idempotency-Key": "book"},
        json={"title": "Duna", "author": "Frank Herbert"},
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers={**MUTATION_HEADERS, "Idempotency-Key": "writing"},
        json={"title": "Medo", "sourceRange": "Cap. 1", "markdown": "# Medo"},
    )
    writing_id = writing.json()["id"]

    saved = await client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# O medo mata a mente", "expectedVersion": 1},
    )
    stale = await client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Sobrescrita perdida", "expectedVersion": 1},
    )
    restored = await client.post(
        f"/api/writings/{writing_id}/versions/1/restore",
        headers=MUTATION_HEADERS,
        json={"expectedVersion": saved.json()["version"]},
    )
    republished_content = await client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# O medo mata a mente", "expectedVersion": restored.json()["version"]},
    )

    published = await client.post(
        f"/api/writings/{writing_id}/publication",
        headers={**MUTATION_HEADERS, "Idempotency-Key": "publish"},
    )
    slug = published.json()["slug"]
    await client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={
            "markdown": "# Rascunho posterior",
            "expectedVersion": republished_content.json()["version"],
        },
    )

    public_article = await client.get(f"/api/public/articles/{slug}")
    cancelled = await client.post(
        f"/api/writings/{writing_id}/publication/cancel-cleanup", headers=MUTATION_HEADERS
    )
    signed_out = await client.delete("/api/auth/session")
    anonymous_private = await client.get("/api/books")
    anonymous_public = await client.get(f"/api/public/articles/{slug}")

    assert stale.status_code == 409
    assert published.status_code == 201
    assert public_article.status_code == 200
    assert public_article.json()["markdown"] == "# O medo mata a mente"
    assert not (walk_keys(public_article.json()) & PRIVATE_KEYS)
    assert cancelled.status_code == 200
    assert signed_out.status_code == 204
    assert anonymous_private.status_code == 401
    assert anonymous_public.status_code == 200
