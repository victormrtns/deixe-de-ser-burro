from __future__ import annotations

import asyncio
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.errors import AppError
from app.writings.schemas import WritingSaveRequest
from app.writings.service import save_markdown
from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


async def create_writing(client: AsyncClient) -> UUID:
    book = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    writing = await client.post(
        f"/api/books/{book.json()['id']}/writings",
        headers=MUTATION_HEADERS,
        json={"title": "O deserto", "sourceRange": "Capítulos 1–2", "markdown": "# O deserto"},
    )
    assert writing.status_code == 201
    return UUID(str(writing.json()["id"]))


async def test_simultaneous_saves_commit_exactly_one_new_version(
    authenticated_client: AsyncClient, migrated_database_url: str, session: AsyncSession
) -> None:
    writing_id = await create_writing(authenticated_client)
    barrier = asyncio.Barrier(2)
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)

    async def attempt(database: Database, markdown: str) -> object:
        async with database.session() as current_session:
            await barrier.wait()
            request = WritingSaveRequest(markdown=markdown, expected_version=1)
            return await save_markdown(current_session, writing_id, request)

    try:
        results = await asyncio.gather(
            attempt(first_database, "vencedor"),
            attempt(second_database, "perdedor"),
            return_exceptions=True,
        )
        version_rows = (
            await session.execute(
                text(
                    "SELECT version_number, markdown FROM writing_versions ORDER BY version_number"
                )
            )
        ).all()
        current_markdown = await session.scalar(text("SELECT markdown FROM writings"))
    finally:
        await first_database.dispose()
        await second_database.dispose()

    conflicts = [result for result in results if isinstance(result, AppError)]
    assert len(conflicts) == 1
    assert conflicts[0].code == "writing_version_conflict"
    assert conflicts[0].details == {"currentVersion": 2}
    assert [row.version_number for row in version_rows] == [1, 2]
    assert current_markdown == version_rows[-1].markdown
    assert current_markdown in {"vencedor", "perdedor"}


async def test_restore_appends_a_new_version_instead_of_rewriting_history(
    authenticated_client: AsyncClient,
) -> None:
    writing_id = await create_writing(authenticated_client)
    await authenticated_client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Reescrita completa", "expectedVersion": 1},
    )

    restored = await authenticated_client.post(
        f"/api/writings/{writing_id}/versions/1/restore",
        headers=MUTATION_HEADERS,
        json={"expectedVersion": 2},
    )
    versions = await authenticated_client.get(f"/api/writings/{writing_id}/versions")

    assert restored.status_code == 200
    assert restored.json()["version"] == 3
    assert restored.json()["markdown"] == "# O deserto"
    assert [(item["version"], item["reason"]) for item in versions.json()["items"]] == [
        (3, "restored"),
        (2, "manual_save"),
        (1, "created"),
    ]


async def test_restore_with_a_stale_expected_version_conflicts(
    authenticated_client: AsyncClient,
) -> None:
    writing_id = await create_writing(authenticated_client)
    await authenticated_client.put(
        f"/api/writings/{writing_id}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Reescrita", "expectedVersion": 1},
    )

    stale = await authenticated_client.post(
        f"/api/writings/{writing_id}/versions/1/restore",
        headers=MUTATION_HEADERS,
        json={"expectedVersion": 1},
    )

    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "writing_version_conflict"
    assert stale.json()["error"]["details"] == {"currentVersion": 2}


async def test_restoring_a_missing_version_is_not_found(
    authenticated_client: AsyncClient,
) -> None:
    writing_id = await create_writing(authenticated_client)

    missing = await authenticated_client.post(
        f"/api/writings/{writing_id}/versions/9/restore",
        headers=MUTATION_HEADERS,
        json={"expectedVersion": 1},
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "resource_not_found"
