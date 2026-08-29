from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Annotated

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pwdlib import PasswordHash
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthorAccount, AuthorSession
from app.auth.schemas import CurrentAuthor
from app.auth.service import (
    IssuedSession,
    authenticate,
    bootstrap_author,
    require_allowed_origin,
    require_author,
)
from app.config import Settings, get_settings
from app.db import Database, get_session
from app.errors import AppError

PASSWORD = "correct horse"


@pytest_asyncio.fixture
async def author(session: AsyncSession) -> AuthorAccount:
    await bootstrap_author(session, "  AUTHOR@Example.COM ", PASSWORD)
    author = await session.scalar(select(AuthorAccount))
    assert author is not None
    return author


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, author: AuthorAccount) -> AsyncClient:
    response = await client.post(
        "/api/auth/session",
        json={"email": "AUTHOR@example.com", "password": PASSWORD},
    )
    assert response.status_code == 200
    return client


async def test_bootstrap_normalizes_email_and_hashes_password(
    session: AsyncSession,
) -> None:
    created = await bootstrap_author(session, "  AUTHOR@Example.COM ", PASSWORD)

    assert created.email == "author@example.com"
    assert created.password_hash != PASSWORD
    assert PasswordHash.recommended().verify(PASSWORD, created.password_hash)


async def test_concurrent_bootstrap_creates_only_one_active_author(
    migrated_database_url: str,
) -> None:
    first_database = Database(migrated_database_url)
    second_database = Database(migrated_database_url)

    async def create(database: Database, email: str) -> AuthorAccount:
        async with database.session() as current_session:
            return await bootstrap_author(current_session, email, PASSWORD)

    try:
        results = await asyncio.gather(
            create(first_database, "first@example.com"),
            create(second_database, "second@example.com"),
            return_exceptions=True,
        )
        async with first_database.session() as current_session:
            active_count = await current_session.scalar(
                text("SELECT count(*) FROM author_accounts WHERE is_active")
            )
    finally:
        await first_database.dispose()
        await second_database.dispose()

    assert sum(isinstance(result, AuthorAccount) for result in results) == 1
    conflicts = [result for result in results if isinstance(result, AppError)]
    assert len(conflicts) == 1
    assert conflicts[0].code == "author_already_exists"
    assert active_count == 1


async def test_login_sets_opaque_cookie_and_private_session_requires_it(
    client: AsyncClient, author: AuthorAccount
) -> None:
    anonymous = await client.get("/api/auth/session")
    login = await client.post(
        "/api/auth/session",
        json={"email": author.email, "password": PASSWORD},
    )
    authenticated = await client.get("/api/auth/session")

    assert anonymous.status_code == 200
    assert anonymous.json() == {"state": "anonymous"}
    assert login.status_code == 200
    assert login.json() == {"state": "author", "author": {"email": author.email}}
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert author.password_hash not in cookie
    assert PASSWORD not in cookie
    assert authenticated.json() == {"state": "author", "author": {"email": author.email}}


async def test_only_the_session_token_hash_is_persisted(
    client: AsyncClient, author: AuthorAccount, session: AsyncSession
) -> None:
    await client.post(
        "/api/auth/session",
        json={"email": author.email, "password": PASSWORD},
    )
    token = client.cookies["entrelinhas_session"]
    stored_hash = await session.scalar(select(AuthorSession.token_hash))

    assert stored_hash == sha256(token.encode()).hexdigest()
    assert stored_hash != token


async def test_authenticate_returns_the_opaque_issued_session_contract(
    session: AsyncSession, author: AuthorAccount
) -> None:
    issued = await authenticate(session, author.email, PASSWORD)

    assert isinstance(issued, IssuedSession)
    assert issued.expires_at > datetime.now(UTC)
    assert issued.token not in repr(issued)


@pytest.mark.parametrize(
    ("email", "password"),
    [("missing@example.com", PASSWORD), ("author@example.com", "wrong password")],
)
async def test_login_rejects_invalid_credentials_without_setting_cookie(
    client: AsyncClient, author: AuthorAccount, email: str, password: str
) -> None:
    response = await client.post("/api/auth/session", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "set-cookie" not in response.headers


async def test_expired_cookie_is_anonymous(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    await session.execute(
        text("UPDATE author_sessions SET expires_at = now() - interval '1 second'")
    )
    await session.commit()

    response = await authenticated_client.get("/api/auth/session")

    assert response.json() == {"state": "anonymous"}


async def test_revoked_cookie_is_anonymous(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    await session.execute(text("UPDATE author_sessions SET revoked_at = now()"))
    await session.commit()

    response = await authenticated_client.get("/api/auth/session")

    assert response.json() == {"state": "anonymous"}


async def test_logout_revokes_the_session_and_clears_the_cookie(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    response = await authenticated_client.delete("/api/auth/session")
    remaining = await session.scalar(
        select(AuthorSession).where(AuthorSession.revoked_at.is_(None))
    )

    assert response.status_code == 204
    assert response.content == b""
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert remaining is None
    assert (await authenticated_client.get("/api/auth/session")).json() == {"state": "anonymous"}


async def test_session_touch_is_throttled(
    authenticated_client: AsyncClient, session: AsyncSession
) -> None:
    original = datetime.now(UTC) - timedelta(hours=1)
    await session.execute(
        text("UPDATE author_sessions SET last_seen_at = :original"), {"original": original}
    )
    await session.commit()

    first = await authenticated_client.get("/api/auth/session")
    first_seen = await session.scalar(select(AuthorSession.last_seen_at))
    second = await authenticated_client.get("/api/auth/session")
    second_seen = await session.scalar(select(AuthorSession.last_seen_at))

    assert first.status_code == second.status_code == 200
    assert first_seen is not None and first_seen > original
    assert second_seen == first_seen


async def test_auth_session_is_not_cors_enabled(client: AsyncClient, author: AuthorAccount) -> None:
    response = await client.post(
        "/api/auth/session",
        headers={"Origin": "https://evil.example"},
        json={"email": author.email, "password": PASSWORD},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_private_dependencies_require_authentication_and_allowed_origin(
    migrated_database_url: str,
) -> None:
    from app.main import create_app

    database = Database(migrated_database_url)
    settings = Settings(
        environment="test",
        database_url=migrated_database_url,
        public_origin="http://localhost:5173",
        files_root="./data/test-files",
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with database.session() as current_session:
            yield current_session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings

    @app.api_route(
        "/api/private",
        methods=["GET", "POST"],
        dependencies=[Depends(require_allowed_origin)],
    )
    async def private(
        author: Annotated[CurrentAuthor, Depends(require_author)],
    ) -> dict[str, str]:
        return {"email": author.email}

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as private_client:
            anonymous = await private_client.get("/api/private")
            await bootstrap_author_for_client(database)
            login = await private_client.post(
                "/api/auth/session",
                json={"email": "author@example.com", "password": PASSWORD},
            )
            missing_origin = await private_client.post("/api/private")
            foreign_origin = await private_client.post(
                "/api/private", headers={"Origin": "https://evil.example"}
            )
            allowed = await private_client.post(
                "/api/private", headers={"Origin": "http://localhost:5173"}
            )
    finally:
        app.dependency_overrides.clear()
        await database.dispose()

    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "authentication_required"
    assert login.status_code == 200
    assert missing_origin.status_code == 403
    assert foreign_origin.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json() == {"email": "author@example.com"}


async def bootstrap_author_for_client(database: Database) -> None:
    async with database.session() as session:
        await bootstrap_author(session, "author@example.com", PASSWORD)


def test_cli_uses_a_non_echoing_prompt_when_environment_credentials_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import cli

    monkeypatch.delenv("AUTHOR_EMAIL", raising=False)
    monkeypatch.delenv("AUTHOR_PASSWORD", raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "author@example.com")
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: PASSWORD)

    credentials = cli.read_bootstrap_credentials()

    assert credentials == ("author@example.com", PASSWORD)


async def test_cli_bootstrap_uses_environment_without_printing_credentials(
    migrated_database_url: str,
) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": migrated_database_url,
            "PUBLIC_ORIGIN": "http://localhost:5173",
            "FILES_ROOT": "./data/test-files",
            "AUTHOR_EMAIL": "Author@Example.COM",
            "AUTHOR_PASSWORD": PASSWORD,
        }
    )
    backend_root = Path(__file__).parents[2]

    first = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.cli", "bootstrap-author"],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    second = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.cli", "bootstrap-author"],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = first.stdout + first.stderr + second.stdout + second.stderr
    assert first.returncode == 0
    assert first.stdout.strip() == "Autor criado."
    assert second.returncode == 1
    assert "O autor já foi criado." in second.stderr
    assert PASSWORD not in combined_output
    assert "Author@Example.COM" not in combined_output
