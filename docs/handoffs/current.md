# Handoff — Books Blog AI / Entrelinhas

## Estado atual (2026-08-28, fase backend CRUD concluída)

O backend P0 de CRUD, versões, publicação e leitura pública está implementado e
verificado, no monorepo (`frontend/` + `backend/` + `compose.yaml` + `ops/`).
O worktree `backend-crud` foi consolidado em `main` e removido.

### Implementado

- FastAPI + SQLAlchemy 2 async + Alembic (`0001_initial`, head verificado por readiness).
- Autor único: bootstrap por CLI, sessão por cookie HttpOnly (hash persistido),
  verificação de `Origin` em mutações, CORS fechado.
- Livros: CRUD com `Idempotency-Key`, contagem de escritas, capas locais
  validadas (Pillow, limites de bytes/pixels, re-encode sem metadados,
  escrita atômica, chaves opacas).
- Escritas: CRUD, versões imutáveis (`writing_versions`), autosave com
  compare-and-swap por `expectedVersion` (`409 writing_version_conflict`),
  restauração que anexa versão (`restored`), workspace com coleções diferidas vazias.
- Publicação: snapshot congelado idempotente (slug canônico com sufixo em
  colisão ativa), janela de 3 dias, cancelamento de limpeza, retirada,
  destaque editorial manual com fallback.
- Cleanup: `CleanupRunner` com `FOR UPDATE SKIP LOCKED`, uma transação por
  publicação, registro de purgadores (vazio nesta fase), CLI
  `cleanup-due-publications` e `systemd timer` em `ops/`.
- Leitura pública: projeções allowlisted (`/api/public/landing|articles|books`
  e detalhes por slug), capas públicas imutáveis em `/api/public/files/{key}`.
- Observabilidade: middleware com `X-Request-ID`, um evento JSON por request
  (sem headers, corpos ou mensagens de exceção), envelope 500 estável.
- Frontend: `httpApi` migrado para os contratos reais (auth, books, writings,
  versões, publicação, público) com `ApiError` do envelope; chat/áudio/
  sugestões/uso continuam explicitamente no mock. A aplicação ainda monta
  `createMockApi()` em `main.tsx` — a troca para `httpApi` é da próxima fase.
- Infra: `compose.yaml` (db sem porta externa, backend em loopback 8000,
  frontend 5173, one-shots `migrate`/`bootstrap-author`/`cleanup` no perfil
  `tools`), Dockerfile com migrações, scripts de backup criptografado (`age`)
  e drill de restauração em `ops/`, runbook `ops/deploy.md`.

### Comandos verificados

```bash
# suíte completa (183 passed; PostgreSQL 16 obrigatório)
cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest
uv run ruff format --check . && uv run ruff check . && uv run mypy app
uv run python scripts/check_public_schema.py

# stack local (verificado: cold start, readiness e persistência pós-restart)
docker compose up -d db && docker compose run --rm migrate && docker compose up -d backend
curl -fsS http://127.0.0.1:8000/api/health/ready

# ciclo completo com projeto descartável (verificado nesta sessão)
cd backend && RUN_COMPOSE_TESTS=1 uv run pytest tests/e2e/test_restart_and_restore.py

# frontend (todos verdes)
npm --prefix frontend run test:unit && npm --prefix frontend run typecheck \
  && npm --prefix frontend run build && npm --prefix frontend run verify:premium \
  && npm --prefix frontend run verify:bundles
```

### Limitações ambientais registradas

- Playwright E2E não roda nesta máquina: o Chromium não lança por falta de
  bibliotecas de sistema (`sudo npx playwright install-deps`). Nenhuma
  verificação de navegador é reivindicada nesta fase.
- Drill real de restauração exige `age` instalado e um artefato de backup;
  os scripts foram validados por `bash -n` + contrato estático.

### Explicitamente adiado (sem código nesta fase)

IA (SDKs, chamadas, chaves), chat, áudio, transcrição, sugestões, medição de
orçamento de IA, Redis, Celery, S3, múltiplos autores, busca e paginação
pública. O `WorkspacePayload` devolve `messages/audio/suggestions` vazios de
propósito.

## Próximos passos prováveis

1. Trocar `createMockApi()` por `httpApi` no frontend (sessão real, biblioteca
   real) e ligar as telas privadas de verdade.
2. Fase de IA: chat contextual, transcrição de áudio e sugestões, com contratos
   já reservados no workspace.
3. Deploy na VPS seguindo `ops/deploy.md`.
