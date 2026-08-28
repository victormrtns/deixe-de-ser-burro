from __future__ import annotations

from collections.abc import AsyncIterator
from importlib import import_module
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database, get_session
from app.main import create_app


def test_production_settings_require_secure_cookies() -> None:
    config = import_module("app.config")

    with pytest.raises(ValidationError, match="production requires secure cookies"):
        config.Settings(
            environment="production",
            database_url="postgresql+psycopg://user:password@localhost/entrelinhas",
            public_origin="https://example.com",
            files_root="/var/lib/entrelinhas/files",
            cookie_secure=False,
        )


def test_settings_expose_required_operational_defaults() -> None:
    config = import_module("app.config")

    settings = config.Settings(
        database_url="postgresql+psycopg://user:password@localhost/entrelinhas",
        public_origin="http://localhost:5173",
        files_root="./data/files",
    )

    assert settings.environment == "development"
    assert settings.session_cookie_name == "entrelinhas_session"
    assert settings.session_ttl_hours == 168
    assert settings.cookie_secure is False
    assert settings.max_cover_bytes == 5_000_000
    assert settings.log_level == "INFO"


def test_settings_reject_a_synchronous_postgresql_driver() -> None:
    config = import_module("app.config")

    with pytest.raises(ValidationError, match=r"postgresql\+psycopg"):
        config.Settings(
            database_url="postgresql://user:password@localhost/entrelinhas",
            public_origin="http://localhost:5173",
            files_root="./data/files",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("session_ttl_hours", 0), ("max_cover_bytes", -1)],
)
def test_settings_reject_non_positive_operational_limits(field: str, value: int) -> None:
    config = import_module("app.config")
    values = {
        "database_url": "postgresql+psycopg://user:password@localhost/entrelinhas",
        "public_origin": "http://localhost:5173",
        "files_root": "./data/files",
        field: value,
    }

    with pytest.raises(ValidationError):
        config.Settings(**values)


@pytest.mark.parametrize(
    "public_origin",
    ["http://localhost:5173/private", "http://localhost:5173?debug=true"],
)
def test_settings_reject_a_non_canonical_public_origin(public_origin: str) -> None:
    config = import_module("app.config")

    with pytest.raises(ValidationError, match="origin without path, query, or fragment"):
        config.Settings(
            database_url="postgresql+psycopg://user:password@localhost/entrelinhas",
            public_origin=public_origin,
            files_root="./data/files",
        )


async def test_app_error_uses_stable_envelope_without_exposing_its_cause() -> None:
    errors = import_module("app.errors")
    app = FastAPI()
    app.add_exception_handler(errors.AppError, errors.app_error_handler)

    @app.get("/failure")
    async def failure() -> None:
        try:
            raise RuntimeError("password=secret SQL SELECT private_markdown")
        except RuntimeError as cause:
            raise errors.AppError(
                "state_conflict",
                "A operação conflita com o estado atual.",
                409,
                {"currentVersion": 5},
            ) from cause

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as test_client:
        response = await test_client.get("/failure")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "state_conflict"
    assert payload["error"]["message"] == "A operação conflita com o estado atual."
    assert payload["error"]["details"] == {"currentVersion": 5}
    UUID(payload["error"]["requestId"])
    assert "secret" not in response.text
    assert "private_markdown" not in response.text


async def test_initial_migration_creates_every_specified_table(
    session: AsyncSession,
) -> None:
    tables = set(
        await session.scalars(
            text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema()")
        )
    )

    assert tables == {
        "alembic_version",
        "author_accounts",
        "author_sessions",
        "books",
        "editorial_settings",
        "idempotency_keys",
        "publication_topics",
        "publications",
        "writing_versions",
        "writings",
    }


async def test_migrations_reach_head_and_readiness_is_ok(
    migrated_database_url: str, client: AsyncClient
) -> None:
    result = await client.get("/api/health/ready")
    assert result.status_code == 200
    assert result.json() == {"status": "ready", "database": "ok", "migration": "head"}


async def test_readiness_rejects_a_database_behind_head(
    session: AsyncSession, client: AsyncClient
) -> None:
    await session.execute(text("UPDATE alembic_version SET version_num = 'behind'"))
    await session.commit()

    try:
        result = await client.get("/api/health/ready")
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "migration_not_ready"
        assert result.json()["error"]["message"] == "Banco aguardando migração."
    finally:
        await session.execute(text("UPDATE alembic_version SET version_num = '0001_initial'"))
        await session.commit()


async def test_readiness_reports_a_missing_migration_schema_without_leaking_sql(
    session: AsyncSession, client: AsyncClient
) -> None:
    await session.execute(text("ALTER TABLE alembic_version RENAME TO alembic_version_missing"))
    await session.commit()

    try:
        result = await client.get("/api/health/ready")
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "migration_not_ready"
        assert "alembic_version" not in result.text
        assert "UndefinedTable" not in result.text
    finally:
        await session.execute(text("ALTER TABLE alembic_version_missing RENAME TO alembic_version"))
        await session.commit()


async def test_readiness_reports_an_unavailable_database_without_leaking_connection_details() -> (
    None
):
    database = Database(
        "postgresql+psycopg://entrelinhas:entrelinhas@127.0.0.1:1/entrelinhas_test"
        "?connect_timeout=1"
    )

    async def unavailable_session() -> AsyncIterator[AsyncSession]:
        async with database.session() as current_session:
            yield current_session

    app = create_app()
    app.dependency_overrides[get_session] = unavailable_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as test_client:
            result = await test_client.get("/api/health/ready")
    finally:
        app.dependency_overrides.clear()
        await database.dispose()

    assert result.status_code == 503
    assert result.json()["error"]["code"] == "database_not_ready"
    assert "127.0.0.1" not in result.text
    assert "entrelinhas" not in result.text
