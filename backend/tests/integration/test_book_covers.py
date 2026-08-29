from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.files.local import LocalFileStore
from app.library.models import Book
from app.library.service import upload_cover
from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


def png_bytes(color: tuple[int, int, int] = (200, 40, 40)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def png_upload(color: tuple[int, int, int] = (200, 40, 40)) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("cover.png", png_bytes(color), "image/png")}


async def create_book(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": "Duna", "author": "Frank Herbert"}
    )
    assert response.status_code == 201
    return response.json()


def stored_cover_files(files_root: Path) -> list[Path]:
    if not files_root.exists():
        return []
    return sorted(path for path in files_root.rglob("*") if path.is_file())


async def test_uploading_a_cover_exposes_it_through_the_private_route(
    authenticated_client: AsyncClient, files_root: Path
) -> None:
    book = await create_book(authenticated_client)

    updated = await authenticated_client.put(
        f"/api/books/{book['id']}/cover", headers=MUTATION_HEADERS, files=png_upload()
    )
    cover = await authenticated_client.get(f"/api/books/{book['id']}/cover")

    assert updated.status_code == 200
    assert updated.json()["coverUrl"] == f"/api/books/{book['id']}/cover"
    assert cover.status_code == 200
    assert cover.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(cover.content)).format == "PNG"
    assert len(stored_cover_files(files_root)) == 1


async def test_cover_rejects_non_image_content(
    authenticated_client: AsyncClient, files_root: Path
) -> None:
    book = await create_book(authenticated_client)

    response = await authenticated_client.put(
        f"/api/books/{book['id']}/cover",
        headers=MUTATION_HEADERS,
        files={"file": ("cover.png", b"not an image", "image/png")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"
    assert stored_cover_files(files_root) == []


async def test_cover_rejects_oversized_uploads(
    authenticated_client: AsyncClient, files_root: Path
) -> None:
    book = await create_book(authenticated_client)

    response = await authenticated_client.put(
        f"/api/books/{book['id']}/cover",
        headers=MUTATION_HEADERS,
        files={"file": ("cover.png", b"0" * 6_000_000, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"
    assert stored_cover_files(files_root) == []


async def test_replacing_a_cover_removes_the_previous_file(
    authenticated_client: AsyncClient, files_root: Path
) -> None:
    book = await create_book(authenticated_client)
    await authenticated_client.put(
        f"/api/books/{book['id']}/cover", headers=MUTATION_HEADERS, files=png_upload()
    )
    first_files = stored_cover_files(files_root)

    await authenticated_client.put(
        f"/api/books/{book['id']}/cover",
        headers=MUTATION_HEADERS,
        files=png_upload(color=(10, 10, 200)),
    )
    second_files = stored_cover_files(files_root)

    assert len(first_files) == len(second_files) == 1
    assert first_files != second_files


async def test_deleting_a_cover_clears_the_url_and_the_file(
    authenticated_client: AsyncClient, files_root: Path
) -> None:
    book = await create_book(authenticated_client)
    await authenticated_client.put(
        f"/api/books/{book['id']}/cover", headers=MUTATION_HEADERS, files=png_upload()
    )

    deleted = await authenticated_client.delete(
        f"/api/books/{book['id']}/cover", headers=MUTATION_HEADERS
    )
    detail = await authenticated_client.get(f"/api/books/{book['id']}")
    missing = await authenticated_client.get(f"/api/books/{book['id']}/cover")

    assert deleted.status_code == 204
    assert detail.json()["coverUrl"] is None
    assert missing.status_code == 404
    assert stored_cover_files(files_root) == []


async def test_private_covers_require_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/api/books/{uuid4()}/cover")

    assert response.status_code == 401


async def test_upload_failure_removes_the_new_file(
    session: AsyncSession, files_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = Book(title="Duna", author="Frank Herbert")
    session.add(book)
    await session.commit()
    store = LocalFileStore(files_root, max_bytes=5_000_000)

    async def failing_commit() -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(session, "commit", failing_commit)
    upload = png_upload()["file"][1]

    with pytest.raises(RuntimeError):
        await upload_cover(session, store, book.id, upload)

    assert stored_cover_files(files_root) == []


async def test_public_files_serve_only_covers_referenced_by_active_publications(
    client: AsyncClient, session: AsyncSession, files_root: Path
) -> None:
    store = LocalFileStore(files_root, max_bytes=5_000_000)
    public_cover = await store.copy_public((await store.put_private_cover(png_bytes())).key)
    book_id, writing_id, version_id = uuid4(), uuid4(), uuid4()
    await session.execute(
        text("INSERT INTO books (id, title, author) VALUES (:id, 'Duna', 'Frank Herbert')"),
        {"id": book_id},
    )
    await session.execute(
        text(
            "INSERT INTO writings (id, book_id, title, source_range, markdown, status)"
            " VALUES (:id, :book_id, 'O deserto', 'Cap. 1', '# O deserto', 'published')"
        ),
        {"id": writing_id, "book_id": book_id},
    )
    await session.execute(
        text(
            "INSERT INTO writing_versions"
            " (id, writing_id, version_number, markdown, title, source_range, reason)"
            " VALUES (:id, :writing_id, 1, '# O deserto', 'O deserto', 'Cap. 1', 'created')"
        ),
        {"id": version_id, "writing_id": writing_id},
    )
    await session.execute(
        text(
            "INSERT INTO publications (id, writing_id, writing_version_id, slug, title,"
            " markdown, excerpt, reading_minutes, published_at, book_slug, book_title,"
            " book_author, public_cover_path, state, cleanup_due_at)"
            " VALUES (:id, :writing_id, :version_id, 'o-deserto', 'O deserto', '# O deserto',"
            " 'Um resumo.', 3, now(), 'duna', 'Duna', 'Frank Herbert', :cover, 'published',"
            " now() + interval '3 days')"
        ),
        {
            "id": uuid4(),
            "writing_id": writing_id,
            "version_id": version_id,
            "cover": public_cover.key,
        },
    )
    await session.commit()

    referenced = await client.get(f"/api/public/files/{public_cover.key}")
    unreferenced_key = (await store.copy_public(public_cover.key)).key
    unreferenced = await client.get(f"/api/public/files/{unreferenced_key}")

    assert referenced.status_code == 200
    assert referenced.headers["content-type"] == "image/png"
    assert unreferenced.status_code == 404
    assert unreferenced.json()["error"]["code"] == "resource_not_found"
