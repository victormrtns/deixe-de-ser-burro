# Handoff — Books Blog AI / deixedeserburro

## Estado atual (2026-08-29, integração frontend-backend implementada)

O frontend monta `httpApi` em produção e usa mocks apenas por injeção nos
testes. Sessão real, rotas privadas, biblioteca, detalhe do livro, workspace
versionado, publicação e artigo público congelado estão conectados aos
contratos do backend.

### Integração implementada

- `SessionProvider` com estados loading/anonymous/author, login com retorno à
  rota solicitada, logout limpando o cache privado e expiração global em 401.
- `/studio`, `/studio/livros/:bookId` e `/studio/escritas/:id` são páginas
  roteadas e protegidas, sem a antiga shell `App.tsx` dirigida por `useState`.
- Criação de livro, escrita e publicação usa `crypto.randomUUID()` estável por
  intenção e reutilizado em retries.
- Workspace carrega payload real, salva com `expectedVersion`, preserva texto
  em conflito, permite recarregar o canônico e listar/restaurar versões.
- Publicação exibe slug e prazo em `pt-BR`, cancela limpeza e retira snapshot.
- Artigo público usa `getArticle(slug)` e renderizador Markdown sanitizado
  carregado sob demanda; o bundle público inicial segue sem módulos privados.
- Orçamento fictício removido e conversa marcada como demonstrativa.
- E2E real documentado em `ops/dev-stack.md`, com auth, jornada integral e
  concorrência em desktop/mobile.

### Verificação desta fase

```bash
npm --prefix frontend run lint                 # 0 erros, 15 warnings
npm --prefix frontend run typecheck            # passou
npm --prefix frontend run test:unit            # 47 passed
npm --prefix frontend run build                # passou
npm --prefix frontend run verify:premium       # 81 arquivos, 0 violações
npm --prefix frontend run verify:bundles       # passou
npm --prefix frontend run test:a11y             # 2 passed
```

O Playwright foi executado contra a stack alcançável e enumerou os casos, mas
todos foram bloqueados antes da navegação porque o Chromium não inicia sem
`libnspr4.so`. Instalar as dependências com `sudo npx playwright install-deps`
e repetir `npm --prefix frontend run test:e2e`; nenhuma aprovação de navegador
é reivindicada neste handoff.

---

## Estado anterior (2026-08-28, fase backend CRUD concluída)

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

---

## Fase: conversa contextual real (Parte 1 do Crawl de IA) — 2026-09-05

Plano: `docs/superpowers/plans/2026-09-05-contextual-ai-conversation.md`
Spec: `docs/superpowers/specs/2026-09-05-contextual-ai-conversation-design.md`

**Nenhum comando Git foi executado.** Tudo abaixo está no working tree.

### Arquivos criados

Backend:
- `backend/migrations/versions/0002_contextual_ai_conversation.py`
- `backend/app/assistant/__init__.py`, `models.py`, `persistence.py`, `schemas.py`,
  `context.py`, `budget.py`, `gateway.py`, `fake_gateway.py`, `openai_gateway.py`,
  `dependencies.py`, `service.py`, `router.py`, `editorial.md`
- `backend/tests/unit/test_assistant_context.py`, `test_assistant_budget.py`,
  `test_fake_model_gateway.py`, `test_openai_gateway.py`, `test_config.py`
- `backend/tests/integration/test_assistant_schema.py`, `test_assistant_conversation.py`,
  `test_assistant_budget_db.py`
- `backend/tests/contract/test_assistant_privacy.py`

Avaliação e operação:
- `ia/evals/parte-1-casos.json`, `ia/evals/parte-1-rubrica.md`

### Arquivos modificados

- `backend/app/config.py` (configuração de IA e orçamento validados)
- `backend/app/main.py` (`EXPECTED_ALEMBIC_HEAD = "0002_contextual_ai_conversation"`, router do assistente)
- `backend/app/writings/schemas.py`, `backend/app/writings/service.py` (workspace devolve as mensagens reais)
- `backend/scripts/check_public_schema.py` (campos e schemas privados do assistente)
- `backend/tests/conftest.py` (fixture `api_app` e `settings_overrides`)
- `backend/tests/integration/test_migrations_and_readiness.py`, `test_schema_invariants.py` (novo head e novas tabelas)
- `backend/pyproject.toml`, `backend/uv.lock` (SDK `openai` 3.8.0)
- `.env.example`, `compose.yaml` (variáveis de IA, sem valor de chave)
- `ops/dev-stack.md` (runbook do modo falso e do smoke test autorizado)
- Frontend: `services/contracts.ts`, `httpApi.ts`, `httpApi.test.ts`, `mockApi.ts`,
  `mock/fixtures.ts`, `api.test.ts`, `features/chat/*`, `features/workspace/WorkspacePage.tsx`,
  `features/workspace/workspace.test.tsx`
- Frontend removidos: `features/chat/useChatStream.ts`, `multimodal-chat.test.tsx`, `multimodal.css`

### Verificação executada

Banco: PostgreSQL 16 em contêiner local (`entrelinhas-test-db`, porta 5432).

```
cd backend
TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test \
  UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest        -> 289 passed, 1 skipped
uv run ruff format --check .                                  -> 99 files already formatted
uv run ruff check .                                           -> 0 violações
uv run mypy app                                               -> no issues, 58 arquivos
uv run python scripts/check_public_schema.py                  -> sem campos ou referências privadas
```
(Antes desta fase a suíte era 183 passed, 1 skipped.)

```
npm --prefix frontend run test:unit      -> 58 passed, 16 arquivos (antes: 47)
npm --prefix frontend run typecheck      -> limpo
npm --prefix frontend run lint           -> 0 erros, 15 warnings (mesmo baseline anterior)
npm --prefix frontend run test:a11y      -> 2 passed
npm --prefix frontend run build          -> ok
npm --prefix frontend run verify:premium -> 79 arquivos, 0 violações
npm --prefix frontend run verify:bundles -> bundle público sem módulos privados
```

Smoke real de HTTP com `AI_GATEWAY=fake` e `uvicorn` na porta 8077, fora do
transporte ASGI dos testes, para provar streaming incremental de verdade:

- os quadros SSE chegaram um a um, em ordem, com `version`, `attemptId` e `sequence`;
- a conversa sobreviveu à recarga (`GET /conversation` devolveu autor + assistente concluídos);
- repetir a mesma `Idempotency-Key` não chamou o gateway de novo;
- `retry` explícito criou a tentativa 2 sem duplicar a mensagem do autor (3 mensagens no total);
- `POST /memory` devolveu 201;
- reservas de 1737 e 1740 micros foram substituídas por 153 e 156 micros reais;
- `grep` por Markdown, pergunta, resposta e memória nos logos do uvicorn: 0 ocorrências.

### Não executado, deliberadamente

- **Nenhuma chamada real à OpenAI.** `AI_GATEWAY` continua `disabled` por padrão e
  nenhum teste automatizado acessa a rede. O smoke test real da Task 9 exige
  aprovação explícita do autor e ainda não foi pedido nem executado.
- **E2E Playwright/Chromium não executado**: o navegador não está instalado neste
  ambiente. Testes unitários e de integração não substituem essa evidência.
- **Avaliação editorial humana não executada**: os cinco casos e a rubrica estão
  versionados em `ia/evals/`, mas pontuar exige respostas reais do modelo.

### Pendência de configuração

O `.env` local tem `CHAT_GPT_KEY`. O backend lê `OPENAI_API_KEY`. Renomear antes
de qualquer smoke test real.
