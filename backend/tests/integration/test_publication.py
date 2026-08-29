from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.errors import AppError
from tests.conftest import ALLOWED_ORIGIN, AUTHOR_EMAIL

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


def parse_moment(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


async def create_writing(client: AsyncClient, *, title: str = "O deserto") -> dict[str, Any]:
    book = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": title, "sourceRange": "Capítulos 1–2", "markdown": "# O medo mata a mente"},
    )
    assert writing.status_code == 201
    return dict(writing.json())


async def publish(client: AsyncClient, writing_id: object, key: str) -> Any:
    return await client.post(
        f"/api/writings/{writing_id}/publication",
        headers={**MUTATION_HEADERS, "Idempotency-Key": key},
    )


async def test_publish_freezes_the_current_version_with_a_three_day_window(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)

    published = await publish(authenticated_client, writing["id"], "publish-1")
    await authenticated_client.put(
        f"/api/writings/{writing['id']}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Rascunho alterado depois", "expectedVersion": 1},
    )
    snapshot_markdown = await session.scalar(text("SELECT markdown FROM publications"))
    writing_status = await session.scalar(text("SELECT status FROM writings"))
    body = published.json()

    assert published.status_code == 201
    assert set(body) == {"slug", "publishedAt", "cleanupAt"}
    assert body["slug"] == "o-deserto"
    assert parse_moment(body["cleanupAt"]) - parse_moment(body["publishedAt"]) == timedelta(days=3)
    assert snapshot_markdown == "# O medo mata a mente"
    assert writing_status == "cleanup_scheduled"


async def test_publish_replays_with_the_same_key_and_conflicts_with_another(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)

    first = await publish(authenticated_client, writing["id"], "publish-1")
    replay = await publish(authenticated_client, writing["id"], "publish-1")
    another_key = await publish(authenticated_client, writing["id"], "publish-2")
    snapshot_count = await session.scalar(text("SELECT count(*) FROM publications"))

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert another_key.status_code == 409
    assert another_key.json()["error"]["code"] == "publication_already_active"
    assert snapshot_count == 1


async def test_publish_requires_an_idempotency_key(authenticated_client: AsyncClient) -> None:
    writing = await create_writing(authenticated_client)

    response = await authenticated_client.post(
        f"/api/writings/{writing['id']}/publication", headers=MUTATION_HEADERS
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


async def test_publishing_a_missing_writing_is_not_found(
    authenticated_client: AsyncClient,
) -> None:
    response = await publish(authenticated_client, uuid4(), "publish-1")

    assert response.status_code == 404


async def test_slug_collisions_with_active_publications_get_a_suffix(
    authenticated_client: AsyncClient,
) -> None:
    first = await create_writing(authenticated_client, title="O deserto")
    second = await create_writing(authenticated_client, title="O deserto")

    first_published = await publish(authenticated_client, first["id"], "publish-1")
    second_published = await publish(authenticated_client, second["id"], "publish-2")

    assert first_published.json()["slug"] == "o-deserto"
    assert second_published.json()["slug"] == "o-deserto-2"


async def test_publish_copies_the_private_cover_to_an_immutable_public_key(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color=(9, 9, 200)).save(buffer, format="PNG")
    cover = await authenticated_client.put(
        f"/api/books/{writing['bookId']}/cover",
        headers=MUTATION_HEADERS,
        files={"file": ("cover.png", buffer.getvalue(), "image/png")},
    )
    assert cover.status_code == 200

    await publish(authenticated_client, writing["id"], "publish-1")
    public_cover_path = await session.scalar(text("SELECT public_cover_path FROM publications"))
    private_cover_path = await session.scalar(text("SELECT private_cover_path FROM books"))
    public_file = await authenticated_client.get(f"/api/public/files/{public_cover_path}")

    assert public_cover_path is not None
    assert public_cover_path != private_cover_path
    assert str(public_cover_path).startswith("covers/public/")
    assert public_file.status_code == 200


async def test_concurrent_publishes_create_a_single_snapshot(
    authenticated_client: AsyncClient, migrated_database_url: str, session: AsyncSession
) -> None:
    from app.auth.persistence import find_active_author
    from app.files.local import LocalFileStore
    from app.publishing.service import publish_writing

    writing = await create_writing(authenticated_client)
    author = await find_active_author(session, AUTHOR_EMAIL)
    assert author is not None
    writing_id = UUID(str(writing["id"]))
    barrier = asyncio.Barrier(2)
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)

    async def attempt(database: Database, key: str, files_root: object) -> object:
        store = LocalFileStore(files_root, max_bytes=5_000_000)  # type: ignore[arg-type]
        async with database.session() as current_session:
            await barrier.wait()
            return await publish_writing(
                current_session, store, author.id, writing_id, idempotency_key=key
            )

    try:
        results = await asyncio.gather(
            attempt(first_database, "key-a", "/tmp"),
            attempt(second_database, "key-b", "/tmp"),
            return_exceptions=True,
        )
        snapshot_count = await session.scalar(text("SELECT count(*) FROM publications"))
    finally:
        await first_database.dispose()
        await second_database.dispose()

    conflicts = [result for result in results if isinstance(result, AppError)]
    assert snapshot_count == 1
    assert len(conflicts) == 1
    assert conflicts[0].code == "publication_already_active"


async def test_publication_status_supports_cancel_cleanup(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    await publish(authenticated_client, writing["id"], "publish-1")

    cancelled = await authenticated_client.post(
        f"/api/writings/{writing['id']}/publication/cancel-cleanup", headers=MUTATION_HEADERS
    )
    status = await authenticated_client.get(f"/api/writings/{writing['id']}/publication")
    writing_status = await session.scalar(text("SELECT status FROM writings"))

    assert cancelled.status_code == 200
    assert cancelled.json()["cleanupCancelledAt"] is not None
    assert status.json()["state"] == "published"
    assert writing_status == "published"


async def test_withdrawing_returns_the_writing_to_draft_and_hides_the_snapshot(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    await publish(authenticated_client, writing["id"], "publish-1")

    withdrawn = await authenticated_client.delete(
        f"/api/writings/{writing['id']}/publication", headers=MUTATION_HEADERS
    )
    publication_state = await session.scalar(text("SELECT state FROM publications"))
    writing_status = await session.scalar(text("SELECT status FROM writings"))

    assert withdrawn.status_code == 200
    assert withdrawn.json()["state"] == "withdrawn"
    assert publication_state == "withdrawn"
    assert writing_status == "draft"


async def test_republishing_after_withdrawal_reuses_the_free_slug(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    await publish(authenticated_client, writing["id"], "publish-1")
    await authenticated_client.delete(
        f"/api/writings/{writing['id']}/publication", headers=MUTATION_HEADERS
    )

    republished = await publish(authenticated_client, writing["id"], "publish-2")
    snapshot_count = await session.scalar(text("SELECT count(*) FROM publications"))

    assert republished.status_code == 201
    assert republished.json()["slug"] == "o-deserto"
    assert snapshot_count == 2


async def test_featured_publication_selection_requires_an_active_publication(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    published = await publish(authenticated_client, writing["id"], "publish-1")
    slug = published.json()["slug"]

    chosen = await authenticated_client.put(
        "/api/editorial/featured-publication", headers=MUTATION_HEADERS, json={"slug": slug}
    )
    missing = await authenticated_client.put(
        "/api/editorial/featured-publication",
        headers=MUTATION_HEADERS,
        json={"slug": "inexistente"},
    )
    featured_id = await session.scalar(
        text("SELECT featured_publication_id FROM editorial_settings")
    )

    assert chosen.status_code == 204
    assert missing.status_code == 404
    assert featured_id is not None


async def test_clearing_the_featured_publication_restores_the_fallback(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    writing = await create_writing(authenticated_client)
    published = await publish(authenticated_client, writing["id"], "publish-1")
    await authenticated_client.put(
        "/api/editorial/featured-publication",
        headers=MUTATION_HEADERS,
        json={"slug": published.json()["slug"]},
    )

    cleared = await authenticated_client.delete(
        "/api/editorial/featured-publication", headers=MUTATION_HEADERS
    )
    featured_id = await session.scalar(
        text("SELECT featured_publication_id FROM editorial_settings")
    )

    assert cleared.status_code == 204
    assert featured_id is None


async def test_a_failed_cover_copy_rolls_the_publication_back(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    from app.auth.persistence import find_active_author
    from app.files.service import StoredFile
    from app.publishing.service import publish_writing

    writing = await create_writing(authenticated_client)
    await session.execute(text("UPDATE books SET private_cover_path = 'covers/private/x.png'"))
    await session.commit()
    author = await find_active_author(session, AUTHOR_EMAIL)
    assert author is not None

    class ExplodingStore:
        async def put_private_cover(self, content: bytes) -> StoredFile:
            raise AssertionError("unused")

        async def copy_public(self, private_key: str) -> StoredFile:
            raise RuntimeError("disk full")

        async def open(self, key: str) -> bytes:
            raise AssertionError("unused")

        async def delete(self, key: str) -> None:
            return None

    with pytest.raises(RuntimeError):
        await publish_writing(
            session,
            ExplodingStore(),
            author.id,
            UUID(str(writing["id"])),
            idempotency_key="publish-1",
        )

    await session.rollback()
    snapshot_count = await session.scalar(text("SELECT count(*) FROM publications"))
    key_count = await session.scalar(text("SELECT count(*) FROM idempotency_keys"))
    writing_status = await session.scalar(text("SELECT status FROM writings"))

    assert snapshot_count == 0
    assert key_count == 0
    assert writing_status == "draft"
