from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


async def create_book(client: AsyncClient) -> str:
    response = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def create_writing(
    client: AsyncClient,
    book_id: str,
    *,
    title: str = "O deserto",
    idempotency_key: str | None = None,
) -> dict[str, object]:
    headers = dict(MUTATION_HEADERS)
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    response = await client.post(
        f"/api/books/{book_id}/writings",
        headers=headers,
        json={"title": title, "sourceRange": "Capítulos 1–2", "markdown": "# O deserto"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def save_markdown(
    client: AsyncClient, writing_id: object, markdown: str, expected_version: int
) -> object:
    return await client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": markdown, "expectedVersion": expected_version},
    )


async def test_create_writing_starts_at_version_one_with_a_created_version(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)

    writing = await create_writing(authenticated_client, book_id, idempotency_key="writing-1")
    versions = await authenticated_client.get(f"/api/writings/{writing['id']}/versions")

    assert writing["version"] == 1
    assert writing["status"] == "draft"
    assert writing["bookId"] == book_id
    assert [(item["version"], item["reason"]) for item in versions.json()["items"]] == [
        (1, "created")
    ]


async def test_create_writing_replays_with_the_same_idempotency_key(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client)

    first = await create_writing(authenticated_client, book_id, idempotency_key="writing-1")
    second = await create_writing(authenticated_client, book_id, idempotency_key="writing-1")
    writing_count = await session.scalar(text("SELECT count(*) FROM writings"))

    assert first == second
    assert writing_count == 1


async def test_create_writing_in_a_missing_book_is_not_found(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        f"/api/books/{uuid4()}/writings",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto", "sourceRange": "Cap. 1", "markdown": ""},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"


async def test_listing_returns_only_the_writings_of_the_book(
    authenticated_client: AsyncClient,
) -> None:
    first_book = await create_book(authenticated_client)
    second_book = await create_book(authenticated_client)
    created = await create_writing(authenticated_client, first_book)
    await create_writing(authenticated_client, second_book, title="Outra escrita")

    listed = await authenticated_client.get(f"/api/books/{first_book}/writings")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]


async def test_saving_markdown_increments_the_version_and_records_history(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)

    saved = await save_markdown(
        authenticated_client, writing["id"], "# O medo mata a mente", expected_version=1
    )
    versions = await authenticated_client.get(f"/api/writings/{writing['id']}/versions")

    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert saved.json()["markdown"] == "# O medo mata a mente"
    assert [(item["version"], item["reason"]) for item in versions.json()["items"]] == [
        (2, "manual_save"),
        (1, "created"),
    ]


async def test_stale_save_conflicts_with_the_current_version_and_keeps_content(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)
    await save_markdown(authenticated_client, writing["id"], "first", expected_version=1)

    stale = await save_markdown(authenticated_client, writing["id"], "lost", expected_version=1)
    current = await authenticated_client.get(f"/api/writings/{writing['id']}")

    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "writing_version_conflict"
    assert stale.json()["error"]["details"] == {"currentVersion": 2}
    assert current.json()["markdown"] == "first"


async def test_saving_identical_markdown_at_the_current_version_does_not_increment(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)

    unchanged = await save_markdown(
        authenticated_client, writing["id"], "# O deserto", expected_version=1
    )
    versions = await authenticated_client.get(f"/api/writings/{writing['id']}/versions")

    assert unchanged.status_code == 200
    assert unchanged.json()["version"] == 1
    assert len(versions.json()["items"]) == 1


async def test_patch_creates_a_version_only_when_canonical_fields_change(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)

    renamed = await authenticated_client.patch(
        f"/api/writings/{writing['id']}",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto profundo", "expectedVersion": 1},
    )
    unchanged = await authenticated_client.patch(
        f"/api/writings/{writing['id']}",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto profundo", "expectedVersion": 2},
    )
    versions = await authenticated_client.get(f"/api/writings/{writing['id']}/versions")

    assert renamed.status_code == 200
    assert renamed.json()["version"] == 2
    assert renamed.json()["title"] == "O deserto profundo"
    assert unchanged.status_code == 200
    assert unchanged.json()["version"] == 2
    assert len(versions.json()["items"]) == 2


async def test_deleting_a_writing_removes_its_history(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)
    await save_markdown(authenticated_client, writing["id"], "conteúdo", expected_version=1)

    deleted = await authenticated_client.delete(
        f"/api/writings/{writing['id']}", headers=MUTATION_HEADERS
    )
    remaining_versions = await session.scalar(text("SELECT count(*) FROM writing_versions"))

    assert deleted.status_code == 204
    assert remaining_versions == 0


async def test_deleting_a_writing_with_an_active_publication_conflicts(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)
    version_id = await session.scalar(text("SELECT id FROM writing_versions LIMIT 1"))
    await session.execute(
        text(
            "INSERT INTO publications (id, writing_id, writing_version_id, slug, title,"
            " markdown, excerpt, reading_minutes, published_at, book_slug, book_title,"
            " book_author, state, cleanup_due_at) VALUES (:id, :writing_id, :version_id,"
            " 'o-deserto', 'O deserto', '# O deserto', 'Resumo.', 3, now(), 'duna', 'Duna',"
            " 'Frank Herbert', 'published', now() + interval '3 days')"
        ),
        {"id": uuid4(), "writing_id": writing["id"], "version_id": version_id},
    )
    await session.commit()

    rejected = await authenticated_client.delete(
        f"/api/writings/{writing['id']}", headers=MUTATION_HEADERS
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "state_conflict"


async def test_version_listing_paginates_with_an_opaque_cursor(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    writing = await create_writing(authenticated_client, book_id)
    for version in range(1, 4):
        await save_markdown(
            authenticated_client, writing["id"], f"revisão {version}", expected_version=version
        )

    first_page = await authenticated_client.get(
        f"/api/writings/{writing['id']}/versions", params={"limit": 2}
    )
    second_page = await authenticated_client.get(
        f"/api/writings/{writing['id']}/versions",
        params={"limit": 2, "cursor": first_page.json()["nextCursor"]},
    )

    assert [item["version"] for item in first_page.json()["items"]] == [4, 3]
    assert [item["version"] for item in second_page.json()["items"]] == [2, 1]
    assert second_page.json()["nextCursor"] is None


async def test_version_detail_is_scoped_to_its_writing(
    authenticated_client: AsyncClient,
) -> None:
    book_id = await create_book(authenticated_client)
    first = await create_writing(authenticated_client, book_id)
    second = await create_writing(authenticated_client, book_id, title="Outra escrita")
    await save_markdown(authenticated_client, first["id"], "novo conteúdo", expected_version=1)

    owned = await authenticated_client.get(f"/api/writings/{first['id']}/versions/2")
    foreign = await authenticated_client.get(f"/api/writings/{second['id']}/versions/2")

    assert owned.status_code == 200
    assert owned.json()["markdown"] == "novo conteúdo"
    assert foreign.status_code == 404


async def test_writings_require_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/api/writings/{uuid4()}")

    assert response.status_code == 401
