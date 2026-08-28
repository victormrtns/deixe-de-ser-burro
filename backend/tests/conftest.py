from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

_SCHEMA_PATTERN = re.compile(r"^entrelinhas_test_[a-z0-9_]+_[0-9a-f]{32}$")


def _required_test_database_url() -> URL:
    raw_url = os.getenv("TEST_DATABASE_URL")
    if raw_url is None:
        pytest.fail("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL must begin with postgresql")
    return url


def _validated_schema_name(schema_name: str) -> str:
    if _SCHEMA_PATTERN.fullmatch(schema_name) is None:
        raise ValueError("refusing to operate on an unvalidated test schema")
    return schema_name


def _schema_url(database_url: URL, schema_name: str) -> str:
    validated = _validated_schema_name(schema_name)
    return database_url.update_query_dict(
        {"options": f"-csearch_path={validated}"}
    ).render_as_string(hide_password=False)


@pytest_asyncio.fixture(scope="session")
async def migrated_database_url() -> AsyncIterator[str]:
    database_url = _required_test_database_url()
    worker = re.sub(r"[^a-z0-9_]", "_", os.getenv("PYTEST_XDIST_WORKER", "main").lower())
    schema_name = _validated_schema_name(f"entrelinhas_test_{worker}_{uuid4().hex}")
    engine = create_async_engine(database_url)

    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    schema_database_url = _schema_url(database_url, schema_name)
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    alembic_config.attributes["database_url"] = schema_database_url

    try:
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
        yield schema_database_url
    finally:
        validated = _validated_schema_name(schema_name)
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{validated}" CASCADE'))
        await engine.dispose()


@pytest_asyncio.fixture
async def session(migrated_database_url: str) -> AsyncIterator[AsyncSession]:
    from app.db import Database

    database = Database(migrated_database_url)
    try:
        async with database.session() as current_session:
            yield current_session
    finally:
        await database.dispose()


@pytest_asyncio.fixture
async def client(migrated_database_url: str) -> AsyncIterator[AsyncClient]:
    from app.db import Database, get_session
    from app.main import create_app

    database = Database(migrated_database_url)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with database.session() as current_session:
            yield current_session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await database.dispose()
