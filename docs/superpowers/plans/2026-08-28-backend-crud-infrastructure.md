# Backend CRUD, Infrastructure, and Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a production-shaped FastAPI/PostgreSQL backend for single-author authentication, books, versioned Markdown writings, frozen publication, cleanup scheduling, and privacy-safe public reading.

**Architecture:** Build one capability-oriented modular monolith under `backend/app`, with FastAPI routers calling transactional application services and SQLAlchemy persistence. Private CRUD and immutable public snapshots share PostgreSQL but never share response schemas; local files, cleanup, and operations are ports/commands that can move to external infrastructure later without introducing Redis, Celery, S3, or AI now.

**Tech Stack:** Python 3.12+, uv, FastAPI, Pydantic Settings, SQLAlchemy 2 async, psycopg 3, Alembic, PostgreSQL 16, pwdlib/Argon2, structlog, Pillow, pytest, pytest-asyncio, HTTPX, Ruff, mypy, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-28-backend-crud-infrastructure-design.md`

## Global Constraints

- Preserve the approved modular monolith: one FastAPI process and one PostgreSQL database, local-first and deployable to a simple VPS.
- JSON fields are camelCase; database columns and Python internals are snake_case.
- Markdown is canonical. Every accepted create, save, metadata edit, or restore produces an immutable recoverable version.
- Public routes read frozen allowlisted snapshots only. Never expose private UUIDs, draft state, version numbers, cleanup timestamps, chat, audio, transcripts, or suggestions.
- Use UUID primary keys, timezone-aware UTC timestamps, database foreign keys/indexes, and slugs only as public lookup keys.
- Require optimistic concurrency for writing mutations and idempotency keys for book creation, writing creation, and publication.
- Protect every `/api/*` route except health, session creation/read, and `/api/public/*`; mutations verify `Origin` for the same-origin deployment.
- Keep CORS closed by default. Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- Alembic is the only schema authority; application startup must never call `create_all`.
- PostgreSQL is mandatory for integration tests; SQLite is not an acceptable substitute.
- Store files outside the source tree, validate content and size, and publish immutable cover copies rather than private paths.
- Do not add AI SDKs/calls, chat, audio, transcription, suggestions, usage billing, Redis, Celery, S3, multiple authors, reader accounts, comments, search, or client-only pagination.
- Do not log Markdown, passwords, cookies, tokens, file bodies, or private request payloads.
- Before each task, run `git status --short` and preserve unrelated user changes. The repository root must be initialized/selected as a valid Git worktree before executing commit steps.

## Target File Map

```text
backend/
├── pyproject.toml                 # locked toolchain, commands, quality configuration
├── uv.lock                        # reproducible Python dependency graph
├── alembic.ini                    # migration runner configuration
├── Dockerfile                     # API and one-shot command image
├── app/
│   ├── main.py                    # FastAPI composition root and routers
│   ├── config.py                  # validated environment settings
│   ├── db.py                      # async engine/session and transaction dependency
│   ├── errors.py                  # typed service errors and HTTP envelope
│   ├── models.py                  # shared SQLAlchemy registry/import surface
│   ├── observability.py           # request IDs and structured HTTP logs
│   ├── cli.py                     # bootstrap, cleanup, fixture, backup-check commands
│   ├── auth/{models,persistence,schemas,service,router}.py
│   ├── library/{models,persistence,schemas,service,router}.py
│   ├── writings/{models,persistence,schemas,service,router}.py
│   ├── idempotency/{models,service}.py
│   ├── files/{service,local}.py
│   ├── publishing/{models,persistence,schemas,service,router,cleanup}.py
│   └── public_read/{schemas,queries,router}.py
├── migrations/
│   ├── env.py
│   └── versions/0001_initial.py
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    ├── contract/
    └── e2e/
frontend/src/services/{contracts,httpApi,api.test}.ts
compose.yaml
.env.example
ops/{backup-postgres.sh,backup-files.sh,restore-smoke.sh,cleanup.service,cleanup.timer,deploy.md}
```

---

### Task 1: Bootstrap the Backend Toolchain and Health API

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/uv.lock`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/unit/test_health.py`
- Create: `backend/Dockerfile`
- Create: `.env.example`

**Interfaces:**
- Consumes: no earlier task.
- Produces: `create_app() -> FastAPI`, `GET /api/health/live -> {"status": "ok"}`, and standard commands `uv run pytest`, `uv run ruff check .`, `uv run mypy app`.

- [ ] **Step 1: Declare the locked project and test dependencies**

Create `backend/pyproject.toml` with a build-free application project and these dependency groups:

```toml
[project]
name = "entrelinhas-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.13", "fastapi>=0.115", "httpx>=0.27",
  "pillow>=10.4", "psycopg[binary]>=3.2", "pwdlib[argon2]>=0.2",
  "pydantic-settings>=2.5", "python-multipart>=0.0.9",
  "sqlalchemy[asyncio]>=2.0", "structlog>=24.4", "uvicorn>=0.30",
]

[dependency-groups]
dev = ["mypy>=1.11", "pytest>=8.3", "pytest-asyncio>=0.24", "ruff>=0.6"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
```

Run: `cd backend && uv lock`
Expected: `uv.lock` is generated with no AI, Redis, Celery, or S3 dependency.

- [ ] **Step 2: Write the failing liveness test**

```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_liveness_does_not_require_dependencies() -> None:
    response = TestClient(create_app()).get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the focused test and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_health.py -v`
Expected: FAIL because `app.main` or `create_app` does not exist.

- [ ] **Step 4: Add the minimal application factory and container image**

```python
# backend/app/main.py
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Entrelinhas API")

    @app.get("/api/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
```

Create `backend/Dockerfile` from `python:3.12-slim`, copy the locked project, run `uv sync --frozen --no-dev`, use a non-root user, and set `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Put only documented non-secret names in `.env.example`.

- [ ] **Step 5: Run tests and static checks**

Run: `cd backend && uv run pytest tests/unit/test_health.py -v && uv run ruff check . && uv run mypy app`
Expected: PASS with one liveness test and no static errors.

- [ ] **Step 6: Commit the toolchain slice**

```bash
git add backend .env.example
git commit -m "build: bootstrap FastAPI backend"
```

---

### Task 2: Add Validated Configuration, PostgreSQL Sessions, Errors, and Initial Migration

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/errors.py`
- Create: `backend/app/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_initial.py`
- Create: `backend/tests/integration/test_migrations_and_readiness.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `create_app()` from Task 1.
- Produces: `Settings`, `get_settings()`, `Database.session()`, `get_session()`, `AppError`, `GET /api/health/ready`, and migration revision `0001_initial` containing every table named by the spec.

- [ ] **Step 1: Define test database fixtures and a failing migration/readiness test**

```python
async def test_migrations_reach_head_and_readiness_is_ok(
    migrated_database_url: str, client: AsyncClient
) -> None:
    result = await client.get("/api/health/ready")
    assert result.status_code == 200
    assert result.json() == {"status": "ready", "database": "ok", "migration": "head"}
```

`tests/conftest.py` must require `TEST_DATABASE_URL` beginning with `postgresql`, create a unique schema per test worker, run `alembic upgrade head`, yield an async session/client with dependency overrides, then drop only that validated schema.

- [ ] **Step 2: Verify the test fails before database infrastructure exists**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_migrations_and_readiness.py -v`
Expected: FAIL because Alembic/config/readiness is absent. Use the documented `TEST_DATABASE_URL` for an existing local PostgreSQL during this task; Task 10 later makes that database reproducible through Compose.

- [ ] **Step 3: Implement settings, session ownership, and the error envelope**

```python
class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn
    public_origin: AnyHttpUrl
    files_root: Path
    session_cookie_name: str = "entrelinhas_session"
    session_ttl_hours: int = 168
    cookie_secure: bool = False
    max_cover_bytes: int = 5_000_000
    log_level: str = "INFO"

    @model_validator(mode="after")
    def production_is_secure(self) -> "Settings":
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        return self
```

`Database.session()` yields `AsyncSession`; service functions own `async with session.begin()` boundaries. `AppError(code, message, status_code, details)` maps to `{"error": {..., "requestId": request_id}}` without exposing exceptions.

- [ ] **Step 4: Create all specified tables in one reviewed initial migration**

Implement `0001_initial.py` explicitly with `author_accounts`, `author_sessions`, `books`, `writings`, `writing_versions`, `publications`, `publication_topics`, `editorial_settings`, and `idempotency_keys`; add unique/index/check constraints described by the spec. The downgrade drops them in reverse dependency order. `app.models` defines the shared declarative `Base`; later capability tasks map ORM classes to this already-migrated schema and register their imports for future Alembic autogeneration. Never invoke `metadata.create_all`.

- [ ] **Step 5: Implement readiness against PostgreSQL and Alembic head**

```python
async def readiness(session: AsyncSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    current = await session.scalar(text("SELECT version_num FROM alembic_version"))
    if current != EXPECTED_ALEMBIC_HEAD:
        raise AppError("migration_not_ready", "Banco aguardando migração.", 503)
    return {"status": "ready", "database": "ok", "migration": "head"}
```

- [ ] **Step 6: Run migration upgrade/downgrade and tests**

Run: `cd backend && uv run alembic upgrade head && uv run pytest tests/integration/test_migrations_and_readiness.py -v && uv run alembic downgrade base && uv run alembic upgrade head`
Expected: every command PASS; readiness uses a migrated PostgreSQL database.

- [ ] **Step 7: Commit the database foundation**

```bash
git add backend/app backend/migrations backend/alembic.ini backend/tests
git commit -m "feat: add PostgreSQL schema and readiness"
```

---

### Task 3: Implement Single-Author Bootstrap, Sessions, and Origin Protection

**Files:**
- Create: `backend/app/auth/models.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/persistence.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/cli.py`
- Create: `backend/tests/unit/test_origin.py`
- Create: `backend/tests/integration/test_auth.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Settings`, `AsyncSession`, `AppError`, `AuthorAccount`, and `AuthorSession` from Tasks 1–2.
- Produces: `CurrentAuthor(id: UUID, email: str)`, `require_author()`, `require_allowed_origin()`, and CLI `python -m app.cli bootstrap-author`.

- [ ] **Step 1: Write failing session and origin tests**

```python
async def test_login_sets_opaque_cookie_and_private_route_requires_it(client, author) -> None:
    login = await client.post("/api/auth/session", json={"email": author.email, "password": "correct horse"})
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert author.password_hash not in login.headers["set-cookie"]

async def test_mutation_rejects_foreign_origin(authenticated_client) -> None:
    response = await authenticated_client.post(
        "/api/books", headers={"Origin": "https://evil.example", "Idempotency-Key": "book-1"},
        json={"title": "Duna", "author": "Frank Herbert"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"
```

- [ ] **Step 2: Run auth tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_origin.py tests/integration/test_auth.py -v`
Expected: FAIL with missing auth modules/routes.

- [ ] **Step 3: Implement password hashing, opaque sessions, and bootstrap**

```python
@dataclass(frozen=True)
class IssuedSession:
    token: str
    expires_at: datetime

async def authenticate(session: AsyncSession, email: str, password: str) -> IssuedSession:
    author = await find_active_author(session, email.casefold())
    if author is None or not password_hash.verify(password, author.password_hash):
        raise AppError("invalid_credentials", "Credenciais inválidas.", 401)
    token = secrets.token_urlsafe(32)
    await insert_session(session, author.id, sha256(token.encode()).hexdigest(), utc_now() + ttl)
    return IssuedSession(token, expires_at)
```

Bootstrap refuses to create a second active author, normalizes email, reads `AUTHOR_EMAIL`/`AUTHOR_PASSWORD` or uses a non-echoing prompt, and never prints the password/hash.

- [ ] **Step 4: Add session routes and reusable dependencies**

`POST` sets the configured cookie; `GET` returns `{state: "anonymous"}` or `{state: "author", author: {email}}`; `DELETE` hashes the cookie, revokes its row, and clears it. `require_author` updates `last_seen_at` at most once per configured interval. `require_allowed_origin` compares normalized scheme/host/port for unsafe methods.

- [ ] **Step 5: Verify auth, expiration, revocation, bootstrap idempotence, and Origin**

Run: `cd backend && uv run pytest tests/unit/test_origin.py tests/integration/test_auth.py -v`
Expected: PASS for correct/incorrect credentials, expired/revoked cookies, anonymous reads, second-author rejection, missing/foreign Origin, and allowed same Origin.

- [ ] **Step 6: Commit authentication**

```bash
git add backend/app/auth backend/app/cli.py backend/app/main.py backend/tests
git commit -m "feat: secure the single-author API"
```

---

### Task 4: Add Transactional Book CRUD, Idempotency, and Safe Covers

**Files:**
- Create: `backend/app/idempotency/models.py`
- Create: `backend/app/idempotency/service.py`
- Create: `backend/app/library/models.py`
- Create: `backend/app/library/schemas.py`
- Create: `backend/app/library/persistence.py`
- Create: `backend/app/library/service.py`
- Create: `backend/app/library/router.py`
- Create: `backend/tests/unit/test_idempotency.py`
- Create: `backend/tests/integration/test_books.py`
- Create: `backend/tests/contract/test_book_contract.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: authenticated `CurrentAuthor`, allowed-origin dependency, `AsyncSession`, `AppError`, and migrated `books`/`idempotency_keys` tables.
- Produces: `IdempotencyService.execute(author_id, operation, key, payload, action)`, `BookSummary(id, title, author, coverUrl, writingCount)`, and all non-cover `/api/books` routes.

- [ ] **Step 1: Write failing idempotency and book contract tests**

```python
async def test_repeated_create_book_returns_same_resource(authenticated_client) -> None:
    headers = {"Origin": "http://localhost:5173", "Idempotency-Key": "book-duna"}
    first = await authenticated_client.post("/api/books", headers=headers, json={"title": "Duna", "author": "Frank Herbert"})
    second = await authenticated_client.post("/api/books", headers=headers, json={"title": "Duna", "author": "Frank Herbert"})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()

async def test_book_contract_is_camel_case(authenticated_client) -> None:
    body = (await authenticated_client.get("/api/books")).json()[0]
    assert set(body) == {"id", "title", "author", "coverUrl", "writingCount"}
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_idempotency.py tests/integration/test_books.py tests/contract/test_book_contract.py -v`
Expected: FAIL because the modules/routes do not exist.

- [ ] **Step 3: Implement request hashing and transactional replay**

```python
def canonical_request_hash(payload: BaseModel) -> str:
    raw = payload.model_dump_json(by_alias=True, exclude_none=False)
    return sha256(raw.encode()).hexdigest()

async def execute(..., action: Callable[[], Awaitable[StoredResponse]]) -> StoredResponse:
    existing = await repo.lock_key(author_id, operation, key)
    if existing and existing.request_hash != request_hash:
        raise AppError("idempotency_conflict", "Chave reutilizada com outro conteúdo.", 409)
    if existing:
        return existing.as_response()
    response = await action()
    await repo.store(..., response_status=response.status, response_body=response.body)
    return response
```

Handle concurrent insertion by the unique constraint and a transaction retry/read, never by creating a second resource.

- [ ] **Step 4: Implement book DTOs, repository, service, and routes**

Use Pydantic aliases via `ConfigDict(alias_generator=to_camel, populate_by_name=True)`. List computes `writingCount` with one grouped query. `DELETE` checks for writings and returns `409 book_not_empty`; it never cascades implicitly.

- [ ] **Step 5: Run CRUD, authorization, idempotency, and query-count tests**

Run: `cd backend && uv run pytest tests/unit/test_idempotency.py tests/integration/test_books.py tests/contract/test_book_contract.py -v`
Expected: PASS for create/replay/conflicting payload, list/detail/update, empty delete, non-empty conflict fixture, anonymous denial, and exact response keys.

- [ ] **Step 6: Commit book CRUD**

```bash
git add backend/app/idempotency backend/app/library backend/app/main.py backend/tests
git commit -m "feat: add idempotent book CRUD"
```

---

#### Phase 4B: Add Safe Local Cover Storage

**Files:**
- Create: `backend/app/files/service.py`
- Create: `backend/app/files/local.py`
- Create: `backend/tests/unit/test_local_files.py`
- Create: `backend/tests/integration/test_book_covers.py`
- Modify: `backend/app/library/router.py`
- Modify: `backend/app/library/service.py`

**Interfaces:**
- Consumes: book CRUD and `Settings.files_root/max_cover_bytes`.
- Produces: `FileStore.put_private_cover`, `copy_public`, `open_private`, `open_public`, `delete`; authenticated cover PUT/DELETE and controlled file GET routes.

- [ ] **Step 1: Write failing traversal, validation, and replacement tests**

```python
async def test_cover_rejects_non_image_content(authenticated_client, book_id) -> None:
    response = await authenticated_client.put(
        f"/api/books/{book_id}/cover", headers={"Origin": "http://localhost:5173"},
        files={"file": ("cover.png", b"not an image", "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"

def test_store_never_accepts_relative_escape(store: LocalFileStore) -> None:
    with pytest.raises(InvalidFileKey):
        store.path_for("../../secret")
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_local_files.py tests/integration/test_book_covers.py -v`
Expected: FAIL because file ports and routes are missing.

- [ ] **Step 3: Implement the file port and atomic local adapter**

```python
class FileStore(Protocol):
    async def put_private_cover(self, content: BinaryIO, media_type: str) -> StoredFile: ...
    async def copy_public(self, private_key: str) -> StoredFile: ...
    async def open(self, key: str) -> AsyncIterator[bytes]: ...
    async def delete(self, key: str) -> None: ...
```

Detect image format with Pillow, enforce bytes and pixel limits, strip metadata by decoding/re-encoding, generate opaque keys, write under a validated root to a temporary sibling, fsync, then `os.replace`. Never trust filename, MIME header, path, or extension.

- [ ] **Step 4: Add transactional cover association and controlled reads**

Upload writes the new file, updates `private_cover_path`, commits, then idempotently removes the former unreferenced file. On database failure remove the new file. Private reads require the author; `/api/public/files/{key}` verifies an active publication references the exact public key.

- [ ] **Step 5: Verify limits, metadata stripping, rollback cleanup, and access control**

Run: `cd backend && uv run pytest tests/unit/test_local_files.py tests/integration/test_book_covers.py -v`
Expected: PASS for valid PNG/JPEG, disguised input, oversized bytes/pixels, traversal, replace/delete, rollback orphan removal, anonymous private denial, and unreferenced public 404.

- [ ] **Step 6: Commit local covers**

```bash
git add backend/app/files backend/app/library backend/tests
git commit -m "feat: store validated book covers locally"
```

---

### Task 5: Add Writing CRUD, Immutable Versions, and Optimistic Concurrency

**Files:**
- Create: `backend/app/writings/models.py`
- Create: `backend/app/writings/schemas.py`
- Create: `backend/app/writings/persistence.py`
- Create: `backend/app/writings/service.py`
- Create: `backend/app/writings/router.py`
- Create: `backend/tests/integration/test_writings.py`
- Create: `backend/tests/contract/test_workspace_contract.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: book service, transactional idempotency, auth, and `writings`/`writing_versions` tables.
- Produces: `WritingDto`, `WritingVersionDto`, `WorkspacePayload`, create/list/detail/patch/delete/workspace/version routes, and `save_writing(... expected_version: int)`.

- [ ] **Step 1: Write failing create/version/workspace tests**

```python
async def test_create_writing_creates_version_one(authenticated_client, book_id) -> None:
    response = await authenticated_client.post(
        f"/api/books/{book_id}/writings",
        headers={"Origin": ORIGIN, "Idempotency-Key": "writing-1"},
        json={"title": "O deserto", "sourceRange": "Capítulos 1–2", "markdown": "# O deserto"},
    )
    assert response.status_code == 201
    assert response.json()["version"] == 1
    versions = await authenticated_client.get(f"/api/writings/{response.json()['id']}/versions")
    assert [(v["version"], v["reason"]) for v in versions.json()["items"]] == [(1, "created")]

async def test_workspace_keeps_deferred_collections_empty(authenticated_client, writing_id) -> None:
    body = (await authenticated_client.get(f"/api/writings/{writing_id}/workspace")).json()
    assert body["messages"] == body["audio"] == body["suggestions"] == []
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && uv run pytest tests/integration/test_writings.py tests/contract/test_workspace_contract.py -v`
Expected: FAIL with missing writing routes.

- [ ] **Step 3: Implement creation and private DTOs atomically**

```python
async def create_writing(session, book_id, request) -> WritingDto:
    async with session.begin():
        await books.require(session, book_id)
        writing = await repo.insert_writing(session, book_id, request, version_number=1)
        await repo.insert_version(session, writing, reason="created")
    return WritingDto.from_model(writing)
```

List is scoped to its book. Patch creates a version only when canonical fields change. Delete rejects an active publication and otherwise deletes the writing/version rows in one transaction.

- [ ] **Step 4: Implement version list/detail and cursor semantics**

Use opaque base64url cursor encoding `(created_at, id)` and deterministic descending order. Restore is added in Phase 5B because it shares concurrency mechanics. Return `404` for a version not belonging to the writing.

- [ ] **Step 5: Implement the compatibility workspace response**

Return exact frontend keys `writing`, `messages`, `audio`, `suggestions`; the latter three are typed empty lists in this phase. Do not create their database tables.

- [ ] **Step 6: Run writing, version, deletion, idempotency, and contract tests**

Run: `cd backend && uv run pytest tests/integration/test_writings.py tests/contract/test_workspace_contract.py -v`
Expected: PASS including transaction rollback when initial version insertion is forced to fail.

- [ ] **Step 7: Commit writing history**

```bash
git add backend/app/writings backend/app/main.py backend/tests
git commit -m "feat: add versioned writing CRUD"
```

---

#### Phase 5B: Enforce Optimistic Concurrency and Restoration

**Files:**
- Create: `backend/tests/unit/test_writing_transitions.py`
- Create: `backend/tests/integration/test_writing_concurrency.py`
- Modify: `backend/app/writings/persistence.py`
- Modify: `backend/app/writings/service.py`
- Modify: `backend/app/writings/router.py`

**Interfaces:**
- Consumes: `WritingDto`, version repository, error envelope from earlier tasks.
- Produces: compare-and-swap autosave/metadata update and `restore_version(writing_id, source_version, expected_version) -> WritingDto`.

- [ ] **Step 1: Write failing stale-save and restore tests**

```python
async def test_stale_save_returns_current_version_without_overwriting(client, writing) -> None:
    first = await put_markdown(client, writing.id, "first", expected_version=1)
    stale = await put_markdown(client, writing.id, "lost", expected_version=1)
    assert first.json()["version"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["details"] == {"currentVersion": 2}
    assert (await get_writing(client, writing.id))["markdown"] == "first"

async def test_restore_appends_instead_of_rewriting_history(client, writing) -> None:
    restored = await client.post(
        f"/api/writings/{writing.id}/versions/1/restore",
        headers={"Origin": ORIGIN}, json={"expectedVersion": 2},
    )
    assert restored.json()["version"] == 3
```

- [ ] **Step 2: Run concurrency tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_writing_transitions.py tests/integration/test_writing_concurrency.py -v`
Expected: FAIL because updates do not yet perform compare-and-swap/restore.

- [ ] **Step 3: Implement a single compare-and-swap primitive**

```python
stmt = (
    update(Writing)
    .where(Writing.id == writing_id, Writing.version_number == expected_version)
    .values(**changes, version_number=Writing.version_number + 1, updated_at=func.now())
    .returning(Writing)
)
updated = (await session.execute(stmt)).scalar_one_or_none()
if updated is None:
    current = await repo.current_version(session, writing_id)
    raise AppError("writing_version_conflict", "A escrita foi alterada em outra sessão.", 409, {"currentVersion": current})
await repo.insert_version(session, updated, reason=reason)
```

Autosave, metadata patch, and restore call this primitive inside one transaction. No-op Markdown saves return the current DTO without incrementing only when `expectedVersion` is current.

- [ ] **Step 4: Add the restore route and simultaneous transaction test**

Use two independent PostgreSQL sessions released by a barrier; assert exactly one update commits at the shared expected version and exactly one immutable version row is appended.

- [ ] **Step 5: Run all writing tests**

Run: `cd backend && uv run pytest tests/unit/test_writing_transitions.py tests/integration/test_writing_concurrency.py tests/integration/test_writings.py -v`
Expected: PASS with no lost update, duplicate version, or implicit merge.

- [ ] **Step 6: Commit concurrency control**

```bash
git add backend/app/writings backend/tests
git commit -m "feat: enforce writing version concurrency"
```

---

### Task 6: Implement Idempotent Frozen Publication and Editorial Selection

**Files:**
- Create: `backend/app/publishing/models.py`
- Create: `backend/app/publishing/schemas.py`
- Create: `backend/app/publishing/persistence.py`
- Create: `backend/app/publishing/service.py`
- Create: `backend/app/publishing/router.py`
- Create: `backend/tests/unit/test_publication_rules.py`
- Create: `backend/tests/integration/test_publication.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: writing/book repositories, `FileStore.copy_public`, idempotency, database clock, and publication tables.
- Produces: `PublishResult(slug, publishedAt, cleanupAt)`, `PublicationStatusDto`, publish/get/withdraw/cancel-cleanup, and featured-publication PUT/DELETE routes.

- [ ] **Step 1: Write failing snapshot and idempotency tests**

```python
async def test_publish_freezes_current_version(client, writing) -> None:
    published = await client.post(
        f"/api/writings/{writing.id}/publication",
        headers={"Origin": ORIGIN, "Idempotency-Key": "publish-1"},
    )
    assert published.status_code == 201
    assert parse_dt(published.json()["cleanupAt"]) - parse_dt(published.json()["publishedAt"]) == timedelta(days=3)
    await put_markdown(client, writing.id, "changed draft", expected_version=writing.version + 1)
    article = await client.get(f"/api/public/articles/{published.json()['slug']}")
    assert article.json()["markdown"] != "changed draft"
```

Add cases for same-key replay, another-key active conflict, slug collision, cover copy, exactly one active publication, and rollback if cover copy/snapshot insertion fails.

- [ ] **Step 2: Run publication tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_publication_rules.py tests/integration/test_publication.py -v`
Expected: FAIL because publishing is absent.

- [ ] **Step 3: Implement slug/read-time/excerpt helpers and transactional publish**

```python
async def publish(session, writing_id, key) -> PublishResult:
    async with session.begin():
        writing = await repo.lock_writing(session, writing_id)
        if await repo.active_publication(session, writing_id):
            raise AppError("publication_already_active", "A escrita já está publicada.", 409)
        now = await repo.database_now(session)
        snapshot = await repo.insert_snapshot(
            session, writing=writing, slug=await unique_slug(session, writing.title),
            excerpt=excerpt(writing.markdown), reading_minutes=reading_minutes(writing.markdown),
            published_at=now, cleanup_due_at=now + timedelta(days=3),
        )
        await repo.mark_cleanup_scheduled(session, writing.id)
    return PublishResult.from_model(snapshot)
```

Insert a `writing_versions` row with reason `published` only if publishing itself increments the canonical version; otherwise point to the existing current version and do not duplicate it. Adopt the latter consistently: publication references the current immutable version without changing `versionNumber`.

- [ ] **Step 4: Implement withdrawal, cleanup cancellation, and featured selection**

Cancel cleanup sets `cleanupCancelledAt` and writing status `published`. Withdrawal locks the active publication, marks it `withdrawn`, hides its public cover, cancels pending cleanup, and returns writing to `draft`. Featured selection accepts `{slug}` and rejects a withdrawn/missing publication; delete restores fallback.

- [ ] **Step 5: Run publication transaction and state tests**

Run: `cd backend && uv run pytest tests/unit/test_publication_rules.py tests/integration/test_publication.py -v`
Expected: PASS including simultaneous publish attempts producing one snapshot and a deterministic conflict.

- [ ] **Step 6: Commit frozen publication**

```bash
git add backend/app/publishing backend/app/main.py backend/tests
git commit -m "feat: publish immutable writing snapshots"
```

---

### Task 7: Add Persisted, Restart-Safe Cleanup

**Files:**
- Create: `backend/app/publishing/cleanup.py`
- Create: `backend/tests/unit/test_cleanup_registry.py`
- Create: `backend/tests/integration/test_cleanup.py`
- Modify: `backend/app/cli.py`
- Modify: `backend/app/publishing/service.py`

**Interfaces:**
- Consumes: publication repository and transaction/session factory.
- Produces: `PrivateDataPurger.purge(session, writing_id)`, `CleanupRunner.run_batch(limit: int) -> CleanupResult`, and CLI `cleanup-due-publications --limit N`.

- [ ] **Step 1: Write failing retry/cancellation/locking tests**

```python
class RecordingPurger:
    async def purge(self, session: AsyncSession, writing_id: UUID) -> None:
        self.calls.append(writing_id)

async def test_cleanup_is_repeatable_and_skips_cancelled(runner, due, cancelled) -> None:
    first = await runner.run_batch(limit=10)
    second = await runner.run_batch(limit=10)
    assert first.completed_ids == [due.id]
    assert second.completed_ids == []
    assert cancelled.id not in first.completed_ids
```

- [ ] **Step 2: Run cleanup tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_cleanup_registry.py tests/integration/test_cleanup.py -v`
Expected: FAIL because cleanup runner/CLI is absent.

- [ ] **Step 3: Implement the purger protocol and batch runner**

```python
class PrivateDataPurger(Protocol):
    async def purge(self, session: AsyncSession, writing_id: UUID) -> None: ...

stmt = (
    select(Publication)
    .where(Publication.state == "published", Publication.cleanup_due_at <= func.now(),
           Publication.cleanup_cancelled_at.is_(None), Publication.cleanup_completed_at.is_(None))
    .order_by(Publication.cleanup_due_at, Publication.id)
    .limit(limit).with_for_update(skip_locked=True)
)
```

Run registered purgers and mark `cleanupCompletedAt` plus writing status `published` in one transaction per publication. The registry is empty in this phase, so Markdown, versions, book, and snapshot remain. A failed purger rolls back and leaves the publication retryable.

- [ ] **Step 4: Expose the one-shot CLI with safe exit codes**

`python -m app.cli cleanup-due-publications --limit 100` prints counts only, exits `0` on success and nonzero on any failed item; it never logs private content.

- [ ] **Step 5: Verify competing runners and restart recovery**

Run: `cd backend && uv run pytest tests/unit/test_cleanup_registry.py tests/integration/test_cleanup.py -v`
Expected: PASS; two concurrent runners never purge the same publication and a rolled-back attempt succeeds later.

- [ ] **Step 6: Commit cleanup**

```bash
git add backend/app/publishing/cleanup.py backend/app/cli.py backend/tests
git commit -m "feat: process persisted publication cleanup"
```

---

### Task 8: Implement Explicit Public Read Projections

**Files:**
- Create: `backend/app/public_read/schemas.py`
- Create: `backend/app/public_read/queries.py`
- Create: `backend/app/public_read/router.py`
- Create: `backend/tests/integration/test_public_queries.py`
- Create: `backend/tests/contract/test_public_privacy.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: active publication snapshots/topics/editorial setting only; no private schema serializer.
- Produces: `PublicArticleSummary`, `PublicArticleDetail`, `PublicBookSummary`, `PublicBookDetail`, `PublicLanding`, and all `/api/public/*` endpoints.

- [ ] **Step 1: Write failing public fallback and privacy tests**

```python
PRIVATE_KEYS = {"id", "writingId", "version", "status", "cleanupAt", "messages", "audio", "transcript", "suggestions"}

async def test_public_tree_contains_no_private_keys(client, published_fixture) -> None:
    for path in ("/api/public/landing", "/api/public/articles", "/api/public/books"):
        body = (await client.get(path)).json()
        assert not (walk_keys(body) & PRIVATE_KEYS)

async def test_featured_falls_back_to_newest_active(client, two_publications) -> None:
    landing = (await client.get("/api/public/landing")).json()
    assert landing["featuredArticle"]["slug"] == two_publications.newest.slug
```

- [ ] **Step 2: Run public contract tests and verify RED**

Run: `cd backend && uv run pytest tests/integration/test_public_queries.py tests/contract/test_public_privacy.py -v`
Expected: FAIL because public queries/routes are absent.

- [ ] **Step 3: Define allowlisted public schemas without inheritance from private DTOs**

```python
class PublicArticleSummary(ApiModel):
    slug: str
    title: str
    excerpt: str
    published_at: datetime
    reading_minutes: int
    cover_image_url: str | None = None
    source_book: PublicSourceBook

class PublicArticleDetail(PublicArticleSummary):
    markdown: str
```

Define book and landing types exactly as `frontend/src/services/contracts.ts`; no UUID/status/cleanup fields exist on these classes.

- [ ] **Step 4: Implement projection-only SQL queries**

Every query selects explicit publication/topic columns and filters `state = 'published'`. Landing uses configured active feature or newest `(published_at DESC, slug ASC)`, up to five recent articles, and groups books from active publications only. Topics are ordered and deduplicated only from `publication_topics`.

- [ ] **Step 5: Verify empty state, withdrawal, snapshot isolation, and 404s**

Run: `cd backend && uv run pytest tests/integration/test_public_queries.py tests/contract/test_public_privacy.py -v`
Expected: PASS for empty landing, featured fallback, private-only books absent, withdrawn slugs 404, deterministic order, and draft/book edits not changing snapshots.

- [ ] **Step 6: Commit public projections**

```bash
git add backend/app/public_read backend/app/main.py backend/tests
git commit -m "feat: expose privacy-safe public projections"
```

---

### Task 9: Migrate the Frontend HTTP Adapter to Real Session and CRUD Contracts

**Files:**
- Modify: `frontend/src/services/contracts.ts`
- Modify: `frontend/src/services/httpApi.ts`
- Modify: `frontend/src/services/api.test.ts`
- Create: `frontend/src/services/httpApi.test.ts`

**Interfaces:**
- Consumes: backend endpoint/DTO contracts from Tasks 3–8.
- Produces: typed client methods for auth, complete book/writing/version/publication/public-read operations; legacy chat/audio/suggestions/usage ports remain on mocks and are not sent to missing backend endpoints.

- [ ] **Step 1: Write failing adapter tests for credentials, Origin-safe methods, IDs, and errors**

```ts
it('sends cookies, expectedVersion, and an idempotency key', async () => {
  server.use(http.put('/api/writings/w1', async ({ request }) => {
    expect(request.credentials).toBe('include')
    expect(await request.json()).toEqual({ markdown: '# Saved', expectedVersion: 4 })
    return HttpResponse.json(writingFixture)
  }))
  await httpApi.writings.save({ id: 'w1', markdown: '# Saved', expectedVersion: 4 })
})
```

Add tests asserting the backend error envelope becomes an `ApiError` with `code`, `message`, `details`, and `requestId`; publish sends `Idempotency-Key`; public GETs do not require auth.

- [ ] **Step 2: Run adapter tests and verify RED**

Run: `cd frontend && npm test -- --run src/services/httpApi.test.ts`
Expected: FAIL because the adapter lacks the new types/headers/error parser.

- [ ] **Step 3: Extend exact TypeScript interfaces**

```ts
export interface ApiErrorShape { code: string; message: string; details?: Record<string, unknown>; requestId: string }
export interface WritingVersion { version: number; markdown: string; title: string; sourceRange: string; reason: 'created'|'manual_save'|'restored'|'published'; createdAt: string }
export interface AuthApi { getSession(): Promise<Session>; signIn(email: string, password: string): Promise<Session>; signOut(): Promise<void> }
export interface PublishingApi {
  publish(writingId: string, idempotencyKey: string): Promise<{slug: string; publishedAt: string; cleanupAt: string}>
  cancelCleanup(writingId: string): Promise<PublicationStatus>
  unpublish(writingId: string): Promise<PublicationStatus>
}
```

Add CRUD/version/detail public methods using the paths fixed by the spec. Keep existing DTO property names unchanged.

- [ ] **Step 4: Implement one shared JSON request helper**

Set `credentials: 'include'`; add JSON content type only when there is a body; accept optional idempotency key; parse the stable error envelope. Do not hardcode `Origin`—the browser supplies it. Do not route deferred chat/audio/suggestion/usage calls to FastAPI; keep the composite adapter explicit until those backends exist.

- [ ] **Step 5: Run service tests, typecheck, and build**

Run: `cd frontend && npm test -- --run src/services/api.test.ts src/services/httpApi.test.ts && npm run typecheck && npm run build`
Expected: PASS; initial-route bundle does not gain a backend/AI dependency.

- [ ] **Step 6: Commit the frontend boundary migration**

```bash
git add frontend/src/services
git commit -m "feat: connect CRUD and publishing API contracts"
```

---

### Task 10: Integrate Local/VPS Operations and Run Release Gates

**Files:**
- Create: `compose.yaml`
- Create: `backend/tests/contract/test_compose_config.py`
- Modify: `backend/Dockerfile`
- Modify: `.env.example`
- Modify: `frontend/vite.config.ts`
- Modify: `docs/handoffs/current.md`

**Interfaces:**
- Consumes: every backend and frontend service interface from Tasks 1–9.
- Produces: `db`, `backend`, `frontend`, `migrate`, `bootstrap-author`, and `cleanup` services/profiles; structured request observability; encrypted backup/restore and cleanup scheduling; reproducible release evidence.

- [ ] **Step 1: Write a failing Compose contract test**

```python
def test_only_frontend_is_externally_bound(compose_config: dict) -> None:
    services = compose_config["services"]
    assert services["db"].get("ports", []) == []
    assert services["backend"].get("ports", []) in ([], ["127.0.0.1:8000:8000"])
    assert services["frontend"]["ports"] == ["127.0.0.1:5173:5173"]
    assert {"db_data", "app_files"} <= set(compose_config["volumes"])
```

- [ ] **Step 2: Run the contract and verify RED**

Run: `cd backend && uv run pytest tests/contract/test_compose_config.py -v`
Expected: FAIL because `compose.yaml` is absent.

- [ ] **Step 3: Define services, health checks, profiles, and volumes**

Use PostgreSQL 16 with a health check; backend waits for healthy DB, mounts `app_files`, and has its own readiness check. `migrate`, `bootstrap-author`, and `cleanup` reuse the backend image as one-shot profile services. Frontend proxies `/api` to `backend:8000` inside Compose. No database port is published; development backend binds loopback only when enabled.

- [ ] **Step 4: Verify cold start and persistence manually**

Run: `docker compose config && docker compose up -d db && docker compose run --rm migrate && docker compose up -d backend frontend && curl -fsS http://127.0.0.1:5173/api/health/ready`
Expected: config is valid and readiness returns `{"status":"ready","database":"ok","migration":"head"}`.

Run: `docker compose restart db backend && curl -fsS http://127.0.0.1:5173/api/health/ready`
Expected: readiness returns the same success and previously seeded records remain.

- [ ] **Step 5: Run Compose contract and document the verified commands**

Run: `cd backend && uv run pytest tests/contract/test_compose_config.py -v`
Expected: PASS. Update `docs/handoffs/current.md` with current backend phase, commands, and no claim that IA is implemented.

- [ ] **Step 6: Commit local infrastructure**

```bash
git add compose.yaml backend/Dockerfile backend/tests/contract/test_compose_config.py frontend/vite.config.ts .env.example docs/handoffs/current.md
git commit -m "build: run the stack with Docker Compose"
```

---

#### Phase 10B: Add Request Observability Without Private Data

**Files:**
- Create: `backend/app/observability.py`
- Create: `backend/tests/unit/test_observability.py`
- Create: `backend/tests/contract/test_log_privacy.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/errors.py`

**Interfaces:**
- Consumes: `Settings.log_level` and `AppError`.
- Produces: `configure_logging()`, request-ID middleware, `X-Request-ID`, and JSON request completion/error events.

- [ ] **Step 1: Write failing request-ID and secret-redaction tests**

```python
def test_logs_never_include_private_request_content(client, capsys) -> None:
    secret = "PRIVATE_MARKDOWN_SENTINEL"
    client.put("/api/writings/missing", headers={"Origin": ORIGIN}, json={"markdown": secret, "expectedVersion": 1})
    output = capsys.readouterr().out
    assert secret not in output
    assert "cookie" not in output.casefold()
```

Also assert a valid incoming `X-Request-ID` is propagated and an invalid/absent value is replaced with a UUID.

- [ ] **Step 2: Run observability tests and verify RED**

Run: `cd backend && uv run pytest tests/unit/test_observability.py tests/contract/test_log_privacy.py -v`
Expected: FAIL because middleware/structured logging is absent.

- [ ] **Step 3: Implement structured event-only logging**

Middleware records timestamp, level, service, environment, request ID, route template, method, status, and duration; it never logs headers, query values, bodies, response bodies, or exception strings from database drivers. Add safe named counters/events for version conflict, publication, overdue cleanup, and cleanup failure.

- [ ] **Step 4: Verify logs and error envelopes share request IDs**

Run: `cd backend && uv run pytest tests/unit/test_observability.py tests/contract/test_log_privacy.py -v`
Expected: PASS with parseable JSON per line and no private sentinel.

- [ ] **Step 5: Commit observability**

```bash
git add backend/app/observability.py backend/app/main.py backend/app/errors.py backend/tests
git commit -m "feat: add privacy-safe request observability"
```

---

#### Phase 10C: Add VPS Cleanup Scheduling, Encrypted Backup, and Restore Smoke Test

**Files:**
- Create: `ops/backup-postgres.sh`
- Create: `ops/backup-files.sh`
- Create: `ops/restore-smoke.sh`
- Create: `ops/cleanup.service`
- Create: `ops/cleanup.timer`
- Create: `ops/deploy.md`
- Create: `backend/tests/contract/test_ops_scripts.py`

**Interfaces:**
- Consumes: Compose services/volumes and cleanup CLI.
- Produces: daily off-host encrypted backup commands, disposable restore verification, systemd cleanup timer, and ordered VPS deploy runbook.

- [ ] **Step 1: Write failing static operation contracts**

```python
def test_backup_scripts_require_encryption_and_remote_destination(repo_root: Path) -> None:
    postgres = (repo_root / "ops/backup-postgres.sh").read_text()
    files = (repo_root / "ops/backup-files.sh").read_text()
    for script in (postgres, files):
        assert "set -euo pipefail" in script
        assert "age" in script
        assert "BACKUP_REMOTE" in script
        assert "mktemp -d" in script
```

Also assert `cleanup.timer` invokes the one-shot command, restore uses a uniquely named disposable database, and deploy ordering is backup → migrate → start → readiness.

- [ ] **Step 2: Run operation contracts and verify RED**

Run: `cd backend && uv run pytest tests/contract/test_ops_scripts.py -v`
Expected: FAIL because `ops/` files are absent.

- [ ] **Step 3: Implement safe backup scripts**

Scripts validate non-empty `BACKUP_REMOTE` and `AGE_RECIPIENT`, create `mktemp -d`, trap cleanup, stream `pg_dump --format=custom` or a deterministic file tar through `age`, checksum the encrypted artifact, then transfer it off-host. They never reuse `$HOME`, never print secrets, and never delete a path not created by their own `mktemp`.

- [ ] **Step 4: Implement restore smoke and cleanup timer**

Restore decrypts into a task-owned temporary directory, creates a unique validated database name, restores, runs integrity counts/readiness, then drops that exact database. The timer runs `docker compose run --rm cleanup` at least hourly with `Persistent=true` so downtime is recovered.

- [ ] **Step 5: Write the deploy and recovery runbook**

Document: secrets placement; reverse proxy/TLS; database/backend private network; off-host retention; pre-migration backup; expand/contract migration; migrate before app switch; readiness; rollback; daily backups; periodic restore drill; and the fact that backups may retain private material until their encrypted retention expires.

- [ ] **Step 6: Verify scripts and shell syntax without contacting remote storage**

Run: `bash -n ops/backup-postgres.sh ops/backup-files.sh ops/restore-smoke.sh && cd backend && uv run pytest tests/contract/test_ops_scripts.py -v`
Expected: PASS; scripts are only syntax/static-tested here. A real restore drill is required in Phase 10D with disposable infrastructure.

- [ ] **Step 7: Commit VPS operations**

```bash
git add ops backend/tests/contract/test_ops_scripts.py
git commit -m "ops: add backup cleanup and VPS runbooks"
```

---

#### Phase 10D: Run Full Security, Recovery, Contract, and Quality Gates

**Files:**
- Create: `backend/tests/e2e/test_author_to_publication.py`
- Create: `backend/tests/e2e/test_restart_and_restore.py`
- Create: `backend/scripts/check_public_schema.py`
- Modify: `backend/pyproject.toml`
- Modify: `docs/handoffs/current.md`

**Interfaces:**
- Consumes: every interface from Tasks 1–9 and Phases 10A–10C.
- Produces: reproducible release gates and evidence for the complete backend phase.

- [ ] **Step 1: Write the failing full-flow acceptance test**

```python
async def test_author_to_frozen_publication(api, author) -> None:
    await api.sign_in(author)
    book = await api.create_book("Duna", "Frank Herbert", key="book")
    writing = await api.create_writing(book["id"], "Medo", "# Medo", key="writing")
    saved = await api.save(writing["id"], "# O medo mata a mente", expected=1)
    assert (await api.stale_save(writing["id"], expected=1)).status_code == 409
    published = await api.publish(writing["id"], key="publish")
    await api.save(writing["id"], "# Rascunho posterior", expected=saved["version"])
    public = await api.public_article(published["slug"])
    assert public["markdown"] == "# O medo mata a mente"
    assert not (walk_keys(public) & PRIVATE_KEYS)
```

Add restart/cleanup persistence and backup-restore tests that run against disposable Compose project/volumes and verify restored publication counts plus readiness.

- [ ] **Step 2: Run new acceptance tests and verify they expose any remaining gap**

Run: `cd backend && uv run pytest tests/e2e -v`
Expected: FAIL until fixtures/gates are fully wired; failures must identify concrete missing integration, not skipped assertions.

- [ ] **Step 3: Add a public OpenAPI schema guard**

`backend/scripts/check_public_schema.py` loads `app.openapi()`, inspects every `/api/public/` response schema recursively, and exits nonzero if private field names or private schema references occur. Add its invocation to the documented gate command.

- [ ] **Step 4: Fix only integration defects revealed by the gates**

Apply minimal changes in the owning modules. Do not introduce deferred capabilities. For each defect, add a focused regression assertion before changing implementation, then rerun that focused test.

- [ ] **Step 5: Run the complete backend gate**

Run: `cd backend && uv sync --frozen && uv run ruff format --check . && uv run ruff check . && uv run mypy app && uv run pytest -v && uv run python scripts/check_public_schema.py`
Expected: PASS with no skips for PostgreSQL integration, public privacy, concurrency, migration, or acceptance tests.

- [ ] **Step 6: Run migration, container, restart, and restore gates**

Run: `docker compose config && docker compose build --pull && docker compose up -d db && docker compose run --rm migrate && docker compose up -d backend frontend && curl -fsS http://127.0.0.1:5173/api/health/ready && docker compose restart db backend && curl -fsS http://127.0.0.1:5173/api/health/ready`
Expected: PASS; readiness succeeds before and after restart and persisted fixture IDs remain queryable.

Run: `TEST_RESTORE=1 ops/restore-smoke.sh`
Expected: PASS against a disposable database, printing only artifact/checksum and aggregate verification data.

- [ ] **Step 7: Run the complete frontend gate**

Run: `cd frontend && npm test -- --run && npm run typecheck && npm run build && npm run verify:premium && npm run check:bundle`
Expected: PASS. If Playwright is included in the repository's full gate, run it only after installing the documented Chromium system dependencies; do not claim browser verification when Chromium cannot launch.

- [ ] **Step 8: Update the persistent handoff with exact evidence**

Record implemented scope, migration head, commands/results, Compose/backup verification, remaining browser limitation if present, and explicit AI/Redis/Celery/S3 deferral in `docs/handoffs/current.md`. Do not record secrets, tokens, Markdown fixtures, or temporary paths.

- [ ] **Step 9: Commit the verified backend phase**

```bash
git add backend frontend/src/services compose.yaml ops docs/handoffs/current.md .env.example
git commit -m "test: verify backend CRUD and publication phase"
```

## Plan Self-Review Record

- **Spec coverage:** Tasks 1–3 cover bootstrap/config/database/migrations/auth; Tasks 4–5 cover idempotent books, local covers, writings, immutable versions, restoration, and concurrency; Tasks 6–8 cover snapshot publication/idempotency, editorial choice, cancellation/withdrawal/cleanup, and explicit public projections; Task 9 migrates the existing frontend boundary; Task 10 integrates Compose, same-origin local/VPS topology, observability, scheduling, backups, restore, deploy, and all acceptance/recovery gates in four ordered phases.
- **Scope check:** The tasks form one dependency chain around a shared schema and public/private boundary. Deferred AI and distributed infrastructure do not appear as dependencies or empty database modules.
- **Type consistency:** `WritingDto.version` maps to database `version_number`; `PublishResult` consistently contains `slug`, `publishedAt`, and `cleanupAt` (adding `publishedAt` to the older frontend mock contract as required by the approved spec); public response types match `frontend/src/services/contracts.ts`; `PrivateDataPurger.purge(session, writing_id)` is the only future cleanup extension point.
- **Placeholder scan:** The plan contains no TBD, TODO, “similar to”, generic test instruction, or undefined implementation placeholder. Every code-producing task has a focused RED command, concrete minimal implementation direction, GREEN command, and commit.
