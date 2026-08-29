"""Restart persistence against a disposable Compose project.

Slow and Docker-dependent: runs only with RUN_COMPOSE_TESTS=1, e.g.
    RUN_COMPOSE_TESTS=1 uv run pytest tests/e2e/test_restart_and_restore.py -v
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_COMPOSE_TESTS") != "1",
    reason="RUN_COMPOSE_TESTS=1 required for Docker Compose lifecycle tests",
)

REPO_ROOT = Path(__file__).parents[3]
PROJECT = "entrelinhas-restart-test"
BASE_URL = "http://127.0.0.1:8000"
AUTHOR = {"email": "author@example.com", "password": "restart horse battery"}


def compose(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": "restart-test-secret",
            "AUTHOR_EMAIL": AUTHOR["email"],
            "AUTHOR_PASSWORD": AUTHOR["password"],
        }
    )
    return subprocess.run(
        ["docker", "compose", "-p", PROJECT, *arguments],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def wait_for_readiness(timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/api/health/ready", timeout=3)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise AssertionError("backend readiness timed out")


def test_restart_preserves_database_files_and_schedules() -> None:
    compose("down", "--volumes")
    try:
        assert compose("up", "-d", "db").returncode == 0
        assert compose("run", "--rm", "migrate").returncode == 0
        assert compose("run", "--rm", "bootstrap-author").returncode == 0
        assert compose("up", "-d", "backend").returncode == 0
        wait_for_readiness()

        with httpx.Client(base_url=BASE_URL) as api:
            login = api.post("/api/auth/session", json=AUTHOR)
            assert login.status_code == 200, login.text
            created = api.post(
                "/api/books",
                headers={"Origin": "http://127.0.0.1:5173", "Idempotency-Key": "restart-book"},
                json={"title": "Duna", "author": "Frank Herbert"},
                cookies=login.cookies,
            )
            assert created.status_code == 201, created.text
            book_id = created.json()["id"]

        assert compose("restart", "db", "backend").returncode == 0
        wait_for_readiness()

        with httpx.Client(base_url=BASE_URL) as api:
            login = api.post("/api/auth/session", json=AUTHOR)
            assert login.status_code == 200
            books = api.get("/api/books", cookies=login.cookies)
            assert [book["id"] for book in books.json()] == [book_id]
    finally:
        compose("down", "--volumes")
