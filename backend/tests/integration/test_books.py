from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.idempotency.models import IdempotencyKey
from tests.conftest import ALLOWED_ORIGIN, AUTHOR_EMAIL, AUTHOR_PASSWORD

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


async def create_book(
    client: AsyncClient,
    title: str = "Duna",
    author: str = "Frank Herbert",
    idempotency_key: str | None = None,
) -> dict[str, object]:
    headers = dict(MUTATION_HEADERS)
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    response = await client.post(
        "/api/books", headers=headers, json={"title": title, "author": author}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_repeated_create_with_the_same_key_returns_the_same_resource(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    headers = {**MUTATION_HEADERS, "Idempotency-Key": "book-duna"}
    payload = {"title": "Duna", "author": "Frank Herbert"}

    first = await authenticated_client.post("/api/books", headers=headers, json=payload)
    second = await authenticated_client.post("/api/books", headers=headers, json=payload)
    book_count = await session.scalar(text("SELECT count(*) FROM books"))

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert book_count == 1


async def test_reusing_a_key_with_a_different_payload_conflicts(
    authenticated_client: AsyncClient,
) -> None:
    headers = {**MUTATION_HEADERS, "Idempotency-Key": "book-duna"}
    await authenticated_client.post(
        "/api/books", headers=headers, json={"title": "Duna", "author": "Frank Herbert"}
    )

    conflicting = await authenticated_client.post(
        "/api/books", headers=headers, json={"title": "Outro título", "author": "Frank Herbert"}
    )

    assert conflicting.status_code == 409
    assert conflicting.json()["error"]["code"] == "idempotency_conflict"


async def test_concurrent_creates_with_the_same_key_create_one_book(
    authenticated_client: AsyncClient, migrated_database_url: str, session: AsyncSession
) -> None:
    from app.auth.persistence import find_active_author
    from app.idempotency.service import StoredResponse
    from app.library.schemas import BookCreateRequest
    from app.library.service import create_book as create_book_service

    author = await find_active_author(session, AUTHOR_EMAIL)
    assert author is not None
    request = BookCreateRequest(title="Duna", author="Frank Herbert")
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)

    async def attempt(database: Database) -> StoredResponse:
        async with database.session() as current_session:
            return await create_book_service(
                current_session, author.id, request, idempotency_key="book-race"
            )

    try:
        results = await asyncio.gather(
            attempt(first_database), attempt(second_database), return_exceptions=True
        )
        book_count = await session.scalar(text("SELECT count(*) FROM books"))
    finally:
        await first_database.dispose()
        await second_database.dispose()

    responses = [result for result in results if isinstance(result, StoredResponse)]
    assert len(responses) == 2
    assert responses[0].body == responses[1].body
    assert book_count == 1


async def test_create_without_a_key_lists_the_book_with_zero_writings(
    authenticated_client: AsyncClient,
) -> None:
    created = await create_book(authenticated_client)

    listed = await authenticated_client.get("/api/books")

    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": created["id"],
            "title": "Duna",
            "author": "Frank Herbert",
            "coverUrl": None,
            "writingCount": 0,
        }
    ]


async def test_list_counts_writings_per_book(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    from app.writings.models import Writing

    first = await create_book(authenticated_client, title="Duna")
    second = await create_book(authenticated_client, title="Trabalho focado", author="Cal Newport")
    session.add(
        Writing(
            book_id=UUID(str(first["id"])),
            title="O deserto",
            source_range="Capítulos 1–2",
            markdown="# O deserto",
        )
    )
    await session.commit()

    listed = await authenticated_client.get("/api/books")

    counts = {book["id"]: book["writingCount"] for book in listed.json()}
    assert counts == {first["id"]: 1, second["id"]: 0}


async def test_detail_returns_the_book_and_missing_ids_are_not_found(
    authenticated_client: AsyncClient,
) -> None:
    created = await create_book(authenticated_client)

    found = await authenticated_client.get(f"/api/books/{created['id']}")
    missing = await authenticated_client.get(f"/api/books/{uuid4()}")

    assert found.status_code == 200
    assert found.json() == created
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "resource_not_found"


async def test_patch_updates_only_the_provided_metadata(
    authenticated_client: AsyncClient,
) -> None:
    created = await create_book(authenticated_client)

    updated = await authenticated_client.patch(
        f"/api/books/{created['id']}",
        headers=MUTATION_HEADERS,
        json={"title": "Duna Messias"},
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "Duna Messias"
    assert updated.json()["author"] == "Frank Herbert"


async def test_delete_removes_an_empty_book(authenticated_client: AsyncClient) -> None:
    created = await create_book(authenticated_client)

    deleted = await authenticated_client.delete(
        f"/api/books/{created['id']}", headers=MUTATION_HEADERS
    )
    listed = await authenticated_client.get("/api/books")

    assert deleted.status_code == 204
    assert listed.json() == []


async def test_delete_rejects_a_book_with_writings(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    from app.writings.models import Writing

    created = await create_book(authenticated_client)
    session.add(
        Writing(
            book_id=UUID(str(created["id"])),
            title="O deserto",
            source_range="Capítulos 1–2",
            markdown="# O deserto",
        )
    )
    await session.commit()

    rejected = await authenticated_client.delete(
        f"/api/books/{created['id']}", headers=MUTATION_HEADERS
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "book_not_empty"


async def test_blank_titles_are_rejected_as_validation_errors(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/books",
        headers=MUTATION_HEADERS,
        json={"title": "   ", "author": "Frank Herbert"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert "   " not in response.text


async def test_books_require_authentication(client: AsyncClient) -> None:
    listed = await client.get("/api/books")

    assert listed.status_code == 401
    assert listed.json()["error"]["code"] == "authentication_required"


async def test_book_mutations_require_the_allowed_origin(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/books",
        headers={"Origin": "https://evil.example"},
        json={"title": "Duna", "author": "Frank Herbert"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


async def test_replayed_creates_are_recorded_once(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    await create_book(authenticated_client, idempotency_key="book-duna")
    await create_book(authenticated_client, idempotency_key="book-duna")

    stored_keys = (await session.scalars(select(IdempotencyKey))).all()

    assert len(stored_keys) == 1
    assert stored_keys[0].operation == "create_book"
    assert stored_keys[0].response_status == 201
    assert AUTHOR_PASSWORD not in str(stored_keys[0].response_body)
