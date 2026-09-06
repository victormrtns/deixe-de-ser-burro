# Contextual AI Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o chat demonstrativo por uma conversa contextual real, persistida, transmitida progressivamente e protegida por limites de contexto e orçamento.

**Architecture:** Um módulo `assistant` orquestra contexto, persistência, orçamento e um `ModelGateway` independente de provedor. O backend transmite eventos próprios por HTTP `text/event-stream`; testes usam `FakeModelGateway`, e o adaptador OpenAI traduz a Responses API apenas no smoke test autorizado.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, PostgreSQL 16, Alembic, Pydantic, OpenAI Python SDK, React 19, TypeScript, fetch streams, SWR, pytest e Vitest.

**Spec:** `docs/superpowers/specs/2026-09-05-contextual-ai-conversation-design.md`

## Global Constraints

- A Parte 1 não altera o Markdown.
- A chave da OpenAI existe somente no backend e nunca entra em banco, logs ou frontend.
- Testes automatizados usam somente `FakeModelGateway` e custam zero.
- Nenhuma chamada real ocorre sem aviso explícito ao autor.
- O teto de desenvolvimento é US$ 2; smoke tests reais podem usar no máximo US$ 0,25.
- `gpt-5-mini` é candidato inicial e `max_output_tokens` começa em 800.
- O contexto usa o Markdown completo, memória local e no máximo seis pares concluídos.
- Contexto grande demais e orçamento insuficiente bloqueiam antes da chamada.
- Retry é explícito; cada chamada possui uma tentativa auditável separada.
- Editor, histórico, leitura e publicação funcionam sem IA.
- Logs não contêm Markdown, mensagens, respostas ou chave.
- Não executar E2E Chromium sem as dependências do navegador; não substituir essa evidência por testes unitários.
- Não executar `git add` ou `git commit`; o autor informou que não está usando Git nesta fase.

## File map

### Backend — novos arquivos

- `backend/migrations/versions/0002_contextual_ai_conversation.py`: tabelas, índices e invariantes do banco.
- `backend/app/assistant/models.py`: modelos ORM de conversa, mensagem, tentativa, memória e uso.
- `backend/app/assistant/schemas.py`: DTOs de histórico, envio, memória, uso e eventos.
- `backend/app/assistant/gateway.py`: protocolo `ModelGateway` e eventos independentes de provedor.
- `backend/app/assistant/fake_gateway.py`: implementação determinística usada em testes.
- `backend/app/assistant/openai_gateway.py`: adaptador `AsyncOpenAI` para Responses API.
- `backend/app/assistant/context.py`: linha editorial, composição e limite de contexto.
- `backend/app/assistant/budget.py`: reserva, conciliação e estados do orçamento.
- `backend/app/assistant/persistence.py`: consultas e mutações do módulo.
- `backend/app/assistant/service.py`: fluxo transacional e streaming.
- `backend/app/assistant/router.py`: endpoints autenticados e serialização SSE.
- `backend/app/assistant/dependencies.py`: seleção/injeção do gateway.
- `backend/app/assistant/__init__.py`: pacote do módulo.
- `backend/app/assistant/editorial.md`: linha editorial global inicial.
- `backend/tests/unit/test_assistant_context.py`: ordem, delimitação e limites.
- `backend/tests/unit/test_assistant_budget.py`: reserva e conciliação.
- `backend/tests/unit/test_fake_model_gateway.py`: contrato de eventos do fake.
- `backend/tests/integration/test_assistant_schema.py`: invariantes PostgreSQL.
- `backend/tests/integration/test_assistant_conversation.py`: histórico, stream, idempotência, falhas e isolamento.
- `backend/tests/contract/test_assistant_privacy.py`: ausência de artefatos privados em superfícies públicas e logs.

### Backend — arquivos modificados

- `backend/app/config.py`: configuração validada de IA e orçamento.
- `backend/app/main.py`: router e novo head Alembic.
- `backend/pyproject.toml` e `backend/uv.lock`: SDK oficial da OpenAI.
- `backend/app/writings/schemas.py`: DTO real das mensagens no workspace.
- `backend/app/writings/service.py`: carregar histórico real.
- `.env.example` e `compose.yaml`: variáveis seguras sem valor de chave.

### Frontend

- `frontend/src/services/contracts.ts`: mensagens, eventos, memória e API de chat.
- `frontend/src/services/httpApi.ts`: histórico e streaming real.
- `frontend/src/services/httpApi.test.ts`: parser e falhas do stream.
- `frontend/src/features/chat/ChatProvider.tsx`: estado persistido, tentativas e retry.
- `frontend/src/features/chat/useChatStream.ts`: remover demo e adaptar eventos do domínio.
- `frontend/src/features/chat/MessageList.tsx`: estados concluído/interrompido/falho.
- `frontend/src/features/chat/PromptComposer.tsx`: idempotência, parar e retry explícito.
- `frontend/src/features/chat/Chat.tsx`: receber `writingId` e API real.
- `frontend/src/features/chat/chat.test.tsx`: fluxo progressivo e recuperação.
- `frontend/src/features/workspace/WorkspacePage.tsx`: remover rótulo/demo e ligar chat real.
- `frontend/src/features/workspace/workspace.test.tsx`: histórico real e editor independente.

### Avaliação e documentação

- `ia/evals/parte-1-casos.json`: cinco casos editoriais versionados.
- `ia/evals/parte-1-rubrica.md`: método humano de pontuação.
- `ops/dev-stack.md`: configuração, execução falsa e smoke test autorizado.
- `docs/handoffs/current.md`: estado real e limites da fase.

---

### Task 1: Persisted conversation schema

**Files:**
- Create: `backend/migrations/versions/0002_contextual_ai_conversation.py`
- Create: `backend/app/assistant/__init__.py`
- Create: `backend/app/assistant/models.py`
- Create: `backend/app/assistant/persistence.py`
- Test: `backend/tests/integration/test_assistant_schema.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `app.models.Base`, `writings.id`, PostgreSQL naming conventions.
- Produces: `Conversation`, `Message`, `GenerationAttempt`, `WritingMemoryItem`, `AiUsageEntry` and persistence functions used by Tasks 4–6.

- [ ] **Step 1: Write failing catalog and behavioral tests**

```python
async def test_one_primary_conversation_per_writing(session, writing):
    first = await persistence.create_conversation(session, writing.id)
    await session.commit()
    with pytest.raises(IntegrityError):
        await persistence.create_conversation(session, writing.id)
        await session.commit()

async def test_attempt_state_is_checked(session, author_message):
    attempt = GenerationAttempt(author_message_id=author_message.id, state="unknown")
    session.add(attempt)
    with pytest.raises(IntegrityError):
        await session.commit()
```

- [ ] **Step 2: Run the focused test and confirm the migration is missing**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_assistant_schema.py -v`

Expected: FAIL because revision `0002_contextual_ai_conversation` and assistant models do not exist.

- [ ] **Step 3: Add migration and ORM models**

Create tables with explicit constraints:

```python
conversations: id, writing_id UNIQUE, created_at, updated_at
conversation_messages: id, conversation_id, role, content, state, created_at, updated_at
generation_attempts: id, author_message_id, assistant_message_id, attempt_number,
  model, instruction_version, state, provider_response_id, input_tokens,
  output_tokens, total_tokens, estimated_cost_usd_micros, latency_ms,
  safe_error_code, created_at, started_at, finished_at
writing_memory_items: id, writing_id, source_message_id, kind, content,
  active, created_at, superseded_at
ai_usage_entries: id, writing_id, generation_attempt_id UNIQUE, state,
  reserved_usd_micros, actual_usd_micros, created_at, settled_at
```

Use checks for roles, states, nonnegative counters, nonblank content, positive attempt number and `ON DELETE CASCADE`. Add a unique constraint on `(author_message_id, attempt_number)` and indexes for history, active memory and monthly usage.

- [ ] **Step 4: Implement focused persistence primitives**

```python
async def get_or_create_conversation(session: AsyncSession, writing_id: UUID) -> Conversation:
    return await _insert_or_select_conversation(session, writing_id)

async def list_recent_complete_pairs(session: AsyncSession, conversation_id: UUID, limit: int = 6) -> list[Message]:
    return list(await session.scalars(_recent_pairs_query(conversation_id, limit)))

async def list_active_memory(session: AsyncSession, writing_id: UUID) -> list[WritingMemoryItem]:
    return list(await session.scalars(_active_memory_query(writing_id)))

async def create_author_message_and_attempt(
    session: AsyncSession,
    conversation_id: UUID,
    content: str,
    idempotency_key: str,
    model: str,
    instruction_version: str,
) -> GenerationAttempt:
    return await _insert_idempotent_attempt(
        session, conversation_id, content, idempotency_key, model, instruction_version
    )

async def append_assistant_content(session: AsyncSession, message_id: UUID, content: str) -> None:
    await session.execute(_append_content_statement(message_id, content))

async def finish_attempt(
    session: AsyncSession,
    attempt_id: UUID,
    state: AttemptState,
    usage: ModelUsage | None,
) -> None:
    await session.execute(_finish_attempt_statement(attempt_id, state, usage))
```

- [ ] **Step 5: Update the expected Alembic head and run migration tests**

Set `EXPECTED_ALEMBIC_HEAD = "0002_contextual_ai_conversation"` in `app/main.py`.

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_assistant_schema.py tests/integration/test_migrations_and_readiness.py -v`

Expected: PASS, including downgrade to `0001_initial` and upgrade back to head.

- [ ] **Step 6: Record the schema checkpoint**

Append the exact passing commands and counts to `docs/handoffs/current.md`; do not run Git commands.

### Task 2: Configuration, editorial policy and gateway contract

**Files:**
- Create: `backend/app/assistant/gateway.py`
- Create: `backend/app/assistant/fake_gateway.py`
- Create: `backend/app/assistant/editorial.md`
- Create: `backend/tests/unit/test_fake_model_gateway.py`
- Modify: `backend/app/config.py`
- Modify: `.env.example`
- Modify: `compose.yaml`

**Interfaces:**
- Consumes: Pydantic settings and async iteration.
- Produces: `ModelRequest`, `ModelEvent`, `ModelUsage`, `ModelGateway.stream(request, signal)`, `FakeModelGateway`, and exact settings consumed later.

- [ ] **Step 1: Write failing settings and gateway contract tests**

```python
async def test_fake_gateway_emits_provider_neutral_sequence():
    events = [event async for event in FakeModelGateway(["Olá", " mundo"]).stream(request)]
    assert [event.type for event in events] == ["started", "text_delta", "text_delta", "completed"]
    assert events[-1].usage == ModelUsage(input_tokens=10, output_tokens=2, total_tokens=12)

def test_openai_key_is_optional_but_budget_is_bounded(settings_factory):
    settings = settings_factory(openai_api_key=None, ai_development_budget_usd="2.00")
    assert settings.openai_api_key is None
    assert settings.ai_max_output_tokens == 800
```

- [ ] **Step 2: Run tests and verify missing types fail**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_fake_model_gateway.py tests/unit/test_config.py -v`

Expected: FAIL on missing gateway and IA settings.

- [ ] **Step 3: Define provider-neutral types**

```python
@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    input: str
    model: str
    max_output_tokens: int

@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass(frozen=True)
class ModelEvent:
    type: Literal["started", "text_delta", "completed"]
    response_id: str | None = None
    delta: str | None = None
    usage: ModelUsage | None = None

class ModelGateway(Protocol):
    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        raise NotImplementedError

    async def cancel(self, response_id: str) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Add exact settings and environment wiring**

Add `openai_api_key: SecretStr | None = None`, `ai_model="gpt-5-mini"`, `ai_max_output_tokens=800`, `ai_max_context_chars=120_000`, `ai_development_budget_usd=Decimal("2.00")`, `ai_manual_smoke_budget_usd=Decimal("0.25")`, and `ai_gateway: Literal["disabled", "fake", "openai"]="disabled"`. Validate budgets as nonnegative and manual budget not greater than total. Add names, never a secret value, to `.env.example` and Compose.

- [ ] **Step 5: Add versioned editorial Markdown and deterministic fake**

Start `editorial.md` with the approved invariants: respond in the author's language, distinguish source text from inference, admit missing evidence, preserve authorial voice, and never claim to alter Markdown. Prefix it with `instruction-version: parte-1-v1` in front matter.

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_fake_model_gateway.py tests/unit/test_config.py -v`

Expected: PASS.

- [ ] **Step 6: Record the gateway checkpoint**

Append the focused test result and confirmed zero network calls to `docs/handoffs/current.md`; do not run Git commands.

### Task 3: Context composition and local memory rules

**Files:**
- Create: `backend/app/assistant/context.py`
- Create: `backend/app/assistant/schemas.py`
- Test: `backend/tests/unit/test_assistant_context.py`

**Interfaces:**
- Consumes: `Message`, `WritingMemoryItem`, `ModelRequest`, settings and `editorial.md`.
- Produces: `ContextInput`, `ComposedContext`, `compose_context(input, limits)` and `MemoryCreateRequest`.

- [ ] **Step 1: Write failing order, limit and exclusion tests**

```python
def test_context_orders_trusted_layers_before_untrusted_content():
    result = compose_context(sample_input(), limits)
    assert result.instructions.startswith("[REGRAS_FIXAS]")
    assert result.input.index("[MEMORIA_LOCAL]") < result.input.index("[MARKDOWN]")
    assert result.input.index("[MARKDOWN]") < result.input.index("[PEDIDO_ATUAL]")

def test_context_rejects_instead_of_truncating_large_markdown():
    with pytest.raises(AppError, match="context_too_large"):
        compose_context(sample_input(markdown="x" * 120_001), limits)

def test_interrupted_assistant_messages_are_excluded():
    assert "parcial" not in compose_context(input_with_interrupted_message(), limits).input
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_assistant_context.py -v`

Expected: FAIL because `compose_context` does not exist.

- [ ] **Step 3: Implement explicit layer delimiters and conservative character limit**

```python
def compose_context(source: ContextInput, limits: ContextLimits) -> ComposedContext:
    markdown = source.markdown
    if len(markdown) > limits.max_markdown_chars:
        raise AppError("context_too_large", "Esta escrita excede o limite do assistente.", 413)
    recent = source.completed_pairs[-6:]
    instructions = render_rules() + "\n" + source.editorial_policy
    body = render_untrusted_layers(source.memory, markdown, recent, source.current_prompt)
    if len(instructions) + len(body) > limits.max_total_chars:
        raise AppError("context_too_large", "O contexto desta escrita excede o limite.", 413)
    return ComposedContext(instructions=instructions, input=body, instruction_version=source.version)
```

- [ ] **Step 4: Define explicit memory command schema without a model call**

`MemoryCreateRequest` accepts `kind: Literal["preference", "decision", "open_question"]`, nonblank `content` limited to 2,000 characters and `sourceMessageId`. Service validation later confirms the source belongs to the same writing.

- [ ] **Step 5: Run context tests**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_assistant_context.py -v`

Expected: PASS.

- [ ] **Step 6: Record the context checkpoint**

Append the passing context cases and chosen limits to `docs/handoffs/current.md`; do not run Git commands.

### Task 4: Budget reservation and usage settlement

**Files:**
- Create: `backend/app/assistant/budget.py`
- Test: `backend/tests/unit/test_assistant_budget.py`
- Test: `backend/tests/integration/test_assistant_conversation.py`

**Interfaces:**
- Consumes: `AiUsageEntry`, settings and `ModelUsage`.
- Produces: `reserve_budget`, `settle_usage`, `release_reservation`, `UsageSummaryDto` and `BudgetState`.

- [ ] **Step 1: Write failing boundary tests**

```python
async def test_reservation_blocks_before_external_call(session, budget):
    await budget.record_actual(session, micros=1_999_900)
    with pytest.raises(AppError, match="ai_budget_exceeded"):
        await budget.reserve(session, writing_id, attempt_id, worst_case_micros=200)

async def test_settlement_replaces_reservation_once(session, reservation):
    await settle_usage(session, reservation.attempt_id, actual_micros=80)
    await settle_usage(session, reservation.attempt_id, actual_micros=80)
    assert await total_actual(session) == 80
```

- [ ] **Step 2: Run and verify failure**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/unit/test_assistant_budget.py tests/integration/test_assistant_conversation.py -k budget -v`

Expected: FAIL on missing budget service.

- [ ] **Step 3: Implement integer-microdollar accounting**

Use integer USD micro-units in persistence, never binary floats. Price tables are configuration data keyed by model. Worst-case cost is calculated from bounded input estimate plus `max_output_tokens`; reservation and monthly totals are locked in one transaction. Repeated settlement returns the existing row without incrementing totals.

- [ ] **Step 4: Implement states**

```python
def state_for(spent_and_reserved: int, limit: int) -> BudgetState:
    if spent_and_reserved >= limit:
        return "blocked"
    if spent_and_reserved * 100 >= limit * 80:
        return "near_limit"
    return "normal"
```

- [ ] **Step 5: Run budget tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/unit/test_assistant_budget.py tests/integration/test_assistant_conversation.py -k budget -v`

Expected: PASS, including concurrent reservation test.

- [ ] **Step 6: Record the budget checkpoint**

Append the boundary and concurrency results to `docs/handoffs/current.md`; do not run Git commands.

### Task 5: Assistant orchestration with the fake gateway

**Files:**
- Create: `backend/app/assistant/service.py`
- Create: `backend/app/assistant/dependencies.py`
- Modify: `backend/app/assistant/persistence.py`
- Test: `backend/tests/integration/test_assistant_conversation.py`

**Interfaces:**
- Consumes: context builder, budget service, persistence and `ModelGateway`.
- Produces: `stream_reply`, `list_messages`, `retry_attempt`, `create_memory_item`, and domain `StreamEvent` objects.

- [ ] **Step 1: Write failing happy-path integration test**

```python
async def test_stream_persists_before_gateway_and_settles_usage(service, fake_gateway):
    events = [event async for event in service.stream_reply(writing_id, author_id, request)]
    assert [event.type for event in events] == [
        "generation.started", "response.delta", "response.delta", "response.completed"
    ]
    assert await stored_author_message() == request.content
    assert await stored_assistant_message() == "Olá mundo"
    assert await stored_attempt_state() == "completed"
```

- [ ] **Step 2: Add failing cancellation, failed persistence and retry cases**

Assert that failed pre-persistence invokes the gateway zero times; cancellation preserves partial text; retry creates attempt number 2 and no second author message; interrupted output is absent from the next context; memory rejects a source message from another writing.

- [ ] **Step 3: Run focused integration tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_assistant_conversation.py -v`

Expected: FAIL because service orchestration is missing.

- [ ] **Step 4: Implement the transaction boundaries**

Validate context and budget before persisting. Commit author message, attempt and reservation before calling the gateway. Buffer deltas and flush after one second or 4 KiB; force final flush on terminal events. Use a fresh short transaction for each flush and terminal transition.

- [ ] **Step 5: Implement error translation and terminal states**

Map timeout with content to `interrupted`; rate limit or unavailable without useful content to `failed`; invalid event order to `provider_protocol_error`; cancellation to `interrupted`. Never update memory from an incomplete attempt. Release or settle the reservation idempotently.

- [ ] **Step 6: Run all assistant integration tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_assistant_conversation.py -v`

Expected: PASS.

- [ ] **Step 7: Record the orchestration checkpoint**

Append the terminal-state and recovery results to `docs/handoffs/current.md`; do not run Git commands.

### Task 6: Authenticated HTTP and SSE contracts

**Files:**
- Create: `backend/app/assistant/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/writings/schemas.py`
- Modify: `backend/app/writings/service.py`
- Test: `backend/tests/integration/test_assistant_conversation.py`
- Test: `backend/tests/contract/test_assistant_privacy.py`

**Interfaces:**
- Consumes: assistant service and existing auth/origin dependencies.
- Produces: history, memory, usage and `POST /api/writings/{writing_id}/conversation/messages` SSE endpoint.

- [ ] **Step 1: Write failing endpoint tests**

```python
async def test_anonymous_cannot_read_or_send(client, writing):
    assert (await client.get(f"/api/writings/{writing.id}/conversation")).status_code == 401
    assert (await client.post(f"/api/writings/{writing.id}/conversation/messages", json=payload)).status_code == 401

async def test_send_uses_versioned_domain_events(authenticated_client, writing):
    response = await authenticated_client.post(
        f"/api/writings/{writing.id}/conversation/messages",
        headers={"Idempotency-Key": str(uuid4())},
        json={"content": "O que falta nesta ideia?"},
    )
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: response.completed' in response.text
```

- [ ] **Step 2: Define routes and schemas**

Implement:

```text
GET  /api/writings/{id}/conversation
POST /api/writings/{id}/conversation/messages
POST /api/writings/{id}/conversation/messages/{message_id}/retry
POST /api/writings/{id}/memory
GET  /api/writings/{id}/usage
```

All mutations require allowed origin, author session and `Idempotency-Key` where they can create a generation. SSE frames contain `event`, compact JSON `data`, schema version `1`, attempt ID and sequence.

- [ ] **Step 3: Include real messages in workspace payload**

Replace the deferred empty `messages` collection with DTOs from `list_messages`; keep `audio` and `suggestions` empty. Do not expose attempts, provider IDs or private memory in public projections.

- [ ] **Step 4: Add privacy and error contract assertions**

Verify public endpoints and structured request logs contain none of: message content, Markdown, memory content, API key, provider response ID or internal attempt data. Verify `context_too_large`, `ai_budget_exceeded`, `ai_unavailable` and `provider_rate_limited` use stable error envelopes before streaming begins.

- [ ] **Step 5: Run endpoint and contract tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test uv run pytest tests/integration/test_assistant_conversation.py tests/contract/test_assistant_privacy.py tests/contract/test_workspace_contract.py -v`

Expected: PASS.

- [ ] **Step 6: Record the HTTP checkpoint**

Append the route, privacy and workspace-contract results to `docs/handoffs/current.md`; do not run Git commands.

### Task 7: OpenAI Responses API adapter

**Files:**
- Create: `backend/app/assistant/openai_gateway.py`
- Modify: `backend/app/assistant/dependencies.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Test: `backend/tests/unit/test_openai_gateway.py`

**Interfaces:**
- Consumes: `ModelGateway`, `ModelRequest`, `AsyncOpenAI` and IA settings.
- Produces: provider-neutral `started`, `text_delta`, and `completed` events without exposing SDK types.

- [ ] **Step 1: Add the SDK and write a failing adapter test with a fake client**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv add openai`

Test asserts the client receives `model`, `instructions`, `input`, `max_output_tokens=800`, `stream=True`, and `store=False`; SDK events become domain events; usage is captured only once; key and content are absent from raised error strings.

- [ ] **Step 2: Run adapter tests and confirm failure**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_openai_gateway.py -v`

Expected: FAIL because `OpenAIModelGateway` is missing.

- [ ] **Step 3: Implement the minimal adapter**

```python
class OpenAIModelGateway(ModelGateway):
    def __init__(self, client: AsyncOpenAI):
        self._client = client

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        stream = await self._client.responses.create(
            model=request.model,
            instructions=request.instructions,
            input=request.input,
            max_output_tokens=request.max_output_tokens,
            store=False,
            stream=True,
        )
        async for event in stream:
            translated = translate_event(event)
            if translated is not None:
                yield translated
```

- [ ] **Step 4: Select disabled, fake or OpenAI explicitly**

`get_model_gateway(settings)` raises `ai_unavailable` when disabled, returns the deterministic fake only in test/development configuration, and requires `openai_api_key` when `ai_gateway=openai`. Never silently fall back from OpenAI to fake in runtime.

- [ ] **Step 5: Run unit, lint and type gates**

Run: `cd backend && UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest tests/unit/test_openai_gateway.py tests/unit/test_fake_model_gateway.py -v && uv run ruff check app/assistant tests/unit && uv run mypy app`

Expected: PASS with no real network calls.

- [ ] **Step 6: Record the adapter checkpoint**

Append the adapter contract and static-gate results to `docs/handoffs/current.md`; do not run Git commands.

### Task 8: Frontend persistent streaming conversation

**Files:**
- Modify: `frontend/src/services/contracts.ts`
- Modify: `frontend/src/services/httpApi.ts`
- Modify: `frontend/src/services/httpApi.test.ts`
- Modify: `frontend/src/features/chat/ChatProvider.tsx`
- Modify: `frontend/src/features/chat/useChatStream.ts`
- Modify: `frontend/src/features/chat/MessageList.tsx`
- Modify: `frontend/src/features/chat/PromptComposer.tsx`
- Modify: `frontend/src/features/chat/Chat.tsx`
- Modify: `frontend/src/features/chat/chat.test.tsx`
- Modify: `frontend/src/features/workspace/WorkspacePage.tsx`
- Modify: `frontend/src/features/workspace/workspace.test.tsx`

**Interfaces:**
- Consumes: versioned SSE domain events and history DTOs from Task 6.
- Produces: real `ChatApi`, parser, persistent chat state, stop and retry UX.

- [ ] **Step 1: Write failing API parser tests**

Use a `ReadableStream` split across arbitrary byte boundaries. Assert the parser emits ordered domain events, ignores comments, rejects malformed known events, preserves unknown versioned events without corrupting state, propagates pre-stream JSON error envelopes and dispatches session expiry on 401.

- [ ] **Step 2: Define frontend contracts**

```ts
export type MessageState = 'streaming' | 'completed' | 'interrupted' | 'failed'
export interface Message { id: string; writingId: string; role: 'author' | 'assistant'; content: string; state: MessageState; createdAt: string }
export type ChatStreamEvent =
  | { type: 'generation.started'; version: 1; attemptId: string; sequence: number; messageId: string }
  | { type: 'response.delta'; version: 1; attemptId: string; sequence: number; delta: string }
  | { type: 'response.completed'; version: 1; attemptId: string; sequence: number; usage: UsageSummary }
  | { type: 'response.interrupted'; version: 1; attemptId: string; sequence: number }
  | { type: 'response.failed'; version: 1; attemptId: string; sequence: number; error: ApiErrorShape }
```

Extend `ChatApi` with `list`, `streamReply`, `retry`, `remember` and `getUsage`.

- [ ] **Step 3: Implement incremental fetch parser**

`streamReply(writingId, content, idempotencyKey, signal, onEvent)` performs authenticated POST, checks non-stream errors before reading, decodes UTF-8 incrementally, parses complete SSE frames, validates known version-1 payloads and never logs frame data.

- [ ] **Step 4: Rewrite provider state around persisted IDs**

Initialize from workspace messages. Generate one idempotency key per send intention and retain it across a pre-stream retry. Apply deltas only to the server-provided assistant message ID. Stop aborts the request and preserves partial content. Retry calls the retry endpoint and creates no duplicate author message.

- [ ] **Step 5: Remove demo runtime and keep audio out of this phase**

Pass `writing.id` and `api.chat` to `ChatPanel`; remove `createDemoChatStream` from `WorkspacePage`; remove “Assistente demonstrativo”. Do not connect Recorder to the backend and label audio as unavailable in this phase rather than adding fake timeline events.

Add an explicit `Lembrar nesta escrita` action to completed author messages. It opens a small form for `kind` and `content`, calls `remember`, and confirms persistence. A like/dislike control, if retained, records evaluation feedback only and never calls `remember`.

- [ ] **Step 6: Run frontend tests**

Run: `npm --prefix frontend run test:unit && npm --prefix frontend run typecheck`

Expected: 47 existing tests plus new chat/parser cases pass; typecheck passes.

- [ ] **Step 7: Record the frontend checkpoint**

Append unit-test and typecheck counts to `docs/handoffs/current.md`; do not run Git commands.

### Task 9: Editorial eval set, operational docs and full verification

**Files:**
- Create: `ia/evals/parte-1-casos.json`
- Create: `ia/evals/parte-1-rubrica.md`
- Modify: `ops/dev-stack.md`
- Modify: `docs/handoffs/current.md`
- Modify: `backend/scripts/check_public_schema.py`

**Interfaces:**
- Consumes: completed backend/frontend contracts.
- Produces: repeatable human evaluation, safe runbook and truthful handoff.

- [ ] **Step 1: Write five concrete eval cases**

Each JSON case contains `id`, `markdown`, `question`, `required_facts`, `forbidden_claims` and `notes`. Cover explanation, counterpoint, missing evidence, preservation of voice and an instruction embedded in Markdown that must be treated as content.

- [ ] **Step 2: Define the human rubric**

Use 1–4 for fidelity, utility, clarity, voice and uncertainty. Require at least 3 in every dimension; any fidelity score below 3 rejects the configuration. Record model, instruction version, context policy, date, latency, tokens and observed cost.

- [ ] **Step 3: Update runbook without a secret**

Document fake mode first. Document OpenAI mode using `OPENAI_API_KEY` only as an environment variable, `AI_GATEWAY=openai`, explicit budget check, one prompt, usage verification and immediate return to `AI_GATEWAY=disabled`. Never print the environment or key.

- [ ] **Step 4: Verify public schema allowlist**

Extend `check_public_schema.py` assertions so public DTOs/routes cannot contain conversation, message, memory, attempt, provider or usage fields.

- [ ] **Step 5: Run backend gates with PostgreSQL**

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://entrelinhas:entrelinhas@localhost:5432/entrelinhas_test UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run pytest
UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run ruff format --check .
UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run mypy app
UV_CACHE_DIR=/tmp/entrelinhas-uv-cache uv run python scripts/check_public_schema.py
```

Expected: all tests and static gates pass; no test accesses the OpenAI network.

- [ ] **Step 6: Run frontend gates**

```bash
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test:unit
npm --prefix frontend run build
npm --prefix frontend run verify:premium
npm --prefix frontend run verify:bundles
npm --prefix frontend run test:a11y
```

Expected: all non-browser gates pass. Report lint warnings separately if the existing baseline permits them.

- [ ] **Step 7: Stop and request explicit approval for one real call**

Before changing `AI_GATEWAY` to `openai`, report the fake-gateway evidence and estimated maximum cost. Run the documented smoke test only after the author explicitly approves. Verify one completed attempt, returned `usage`, cost below US$ 0.25 and absence of private content in logs.

- [ ] **Step 8: Update truthful handoff**

Record exact commands, pass/fail counts, observed API cost if authorized, and browser limitation. Do not claim real provider or browser validation if skipped.

- [ ] **Step 9: Finish the uncommitted handoff**

Ensure `docs/handoffs/current.md` lists every modified or created path, exact verification evidence, skipped browser/provider checks and the explicit instruction that no Git commands were run.
