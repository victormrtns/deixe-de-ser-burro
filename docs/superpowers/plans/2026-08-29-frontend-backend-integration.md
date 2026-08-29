# Frontend–Backend Integration and Real Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mocked studio with the real backend: cookie-based sign-in, session-guarded routes, a live library/workspace/publication cycle with optimistic concurrency, real frozen public articles, and E2E tests that start from the login screen against the Compose stack.

**Architecture:** The app mounts `httpApi` at the composition root while tests keep injecting `createMockApi()` through `AppProviders`. A focused `SessionProvider` owns authentication state behind a generic `state/actions` context; routed studio pages (`/studio`, `/studio/livros/:bookId`, `/studio/escritas/:writingId`) replace the `useState`-driven demo shell. All traffic is same-origin `/api` through the Vite proxy (dev/E2E) or the VPS reverse proxy (prod), so the session cookie and the backend `Origin` check work without CORS.

**Tech Stack:** React 19, TypeScript 5.9, React Router 7, SWR 2, existing `httpApi`/`ApiError`, Vitest, Testing Library, MSW (adapter tests only), Playwright against Docker Compose, FastAPI backend already in `backend/`.

**Spec:** `docs/superpowers/specs/2026-08-29-frontend-backend-integration-design.md`

**Required Patterns (read before implementing and again at final review):**
- `docs/patterns/vercel-composition-patterns/AGENTS.md`
- `docs/patterns/vercel-react-best-practices/AGENTS.md`
- `docs/patterns/clean-code/SKILL.md`

## Global Constraints

- UI copy is Brazilian Portuguese; locale formatting is `pt-BR`; WCAG 2.2 AA.
- `main.tsx` mounts `httpApi` only; `createMockApi()` becomes test infrastructure injected via providers — never a runtime fallback.
- All API traffic is same-origin `/api`; no absolute backend URLs, no secrets in URLs, no tokens in local storage; the session lives in the HttpOnly cookie.
- Providers own state (session, workspace, dialogs); presentational components consume the generic `state/actions` context interface and never import SWR/fetch internals (composition patterns 2.1–2.3).
- Explicit variants over boolean-prop matrices; derived state computed during render; interaction logic in event handlers; functional `setState` updates (best-practices 5.x).
- Every mutation that can duplicate a resource carries an `Idempotency-Key` from `crypto.randomUUID()`, created per form submission intent and reused across retries of that intent.
- Optimistic-concurrency failures (`writing_version_conflict`) surface as explicit conflict states that preserve local text; the client never merges silently.
- Public routes and the initial public bundle keep excluding CodeMirror, Mermaid, KaTeX, and private feature modules (`verify:bundles` stays green).
- Async surfaces cover loading (reserved geometry), empty, error + retry, success; validation errors render inline; a toast never carries the only explanation of a recoverable error.
- The budget indicator, chat, audio, and suggestions have no backend: the shell hides the budget, and the workspace conversation is visibly labeled as demonstrative — no fake data presented as real.
- Test-first throughout (clean-code rule 11): each task writes its failing test before the implementation and ends with the focused suite green plus lint/typecheck.

## Planned File Structure

```text
frontend/src/
├── main.tsx                              mounts httpApi (modify)
├── app/
│   ├── router.tsx                        session-guarded route tree (modify)
│   └── AppProviders.tsx                  + SessionProvider composition (modify)
├── features/auth/
│   ├── SessionProvider.tsx               session state/actions context (create)
│   ├── RequireAuthor.tsx                 route guard (create)
│   └── SignInPage.tsx                    wired form (modify)
├── features/library/
│   ├── LibraryPage.tsx                   real routed library (create)
│   ├── BookDetailPage.tsx                real writings list (rewrite)
│   ├── LibraryFormDialog.tsx             idempotent create flows (modify)
│   └── useLibrary.ts                     SWR resources (create)
├── features/workspace/
│   ├── WorkspacePage.tsx                 loads real workspace (modify)
│   ├── WorkspaceProvider.tsx             expectedVersion + conflict (modify)
│   ├── VersionHistory.tsx                list + restore (create)
│   └── ConflictNotice.tsx                reload-canonical surface (create)
├── features/publishing/
│   ├── PublishDialog.tsx                 idempotent publish (modify)
│   └── PublicationStatus.tsx             cancel/withdraw wired (modify)
├── public-site/PublicArticlePage.tsx     frozen markdown rendering (modify)
└── app/App.tsx                           demo shell removed (delete)
frontend/tests/e2e/                       login + full-journey specs (modify/create)
ops/dev-stack.md                          stack-for-tests instructions (create)
```

---

### Task 1: Real session provider, sign-in, and route guard

**Files:**
- Create: `frontend/src/features/auth/SessionProvider.tsx`
- Create: `frontend/src/features/auth/RequireAuthor.tsx`
- Modify: `frontend/src/features/auth/SignInPage.tsx`
- Modify: `frontend/src/app/AppProviders.tsx`
- Modify: `frontend/src/app/router.tsx`
- Test: `frontend/src/features/auth/session.test.tsx`
- Modify: `frontend/src/app/router.test.tsx`

**Interfaces:**
- Consumes: `AuthApi` (`getSession`, `signIn`, `signOut`) from `contracts.ts`, `ApiError`.
- Produces: `SessionProvider`, `useSession(): { state: SessionState; actions: SessionActions }`, `RequireAuthor`, and a router built on real session state instead of the `authenticated` boolean.

- [ ] **Step 1: Write failing session tests**

```tsx
it('redireciona rota privada anônima para /entrar e volta após o login', async () => {
  const user = userEvent.setup()
  renderAppAt('/studio', { api: mockApiSignedOut() })
  await user.type(await screen.findByLabelText('E-mail'), 'author@example.com')
  await user.type(screen.getByLabelText('Senha'), 'correct horse')
  await user.click(screen.getByRole('button', { name: 'Entrar no estúdio' }))
  expect(await screen.findByRole('heading', { name: /biblioteca/i })).toBeVisible()
})

it('mostra credencial inválida inline sem limpar o e-mail digitado', async () => { /* signIn rejects with ApiError invalid_credentials */ })
```

Also assert: `loading` renders a stable placeholder (no flash of the sign-in form), and sign-out returns to `/` as anonymous.

- [ ] **Step 2: Run the tests and verify RED**

Run: `npm --prefix frontend run test:unit -- src/features/auth/session.test.tsx src/app/router.test.tsx`
Expected: FAIL — `SessionProvider` does not exist and the router ignores session state.

- [ ] **Step 3: Implement the provider and guard**

`SessionProvider` resolves `useSWR('auth/session', api.auth.getSession)` into
`{ status: 'loading' | 'anonymous' | 'author'; email? }`; `signIn`/`signOut`
call the API and mutate the SWR key (derive state during render — no effect
mirroring). `RequireAuthor` reads the context: loading → `<main>` placeholder,
anonymous → `<Navigate to="/entrar" state={{ from: location }} />`, author →
children. `SignInPage` becomes a real form: `noValidate`, inline `ApiError`
message for `invalid_credentials`, busy-stable submit button, redirect to
`state.from ?? '/studio'` on success.

- [ ] **Step 4: Rebuild the route tree on the session**

`appRoutes()` loses the `authenticated` parameter; `/studio/**` wraps in
`RequireAuthor`. `createAppRouter(initialEntries)` keeps working for tests —
session now comes from the injected API, not a flag. Update `router.test.tsx`
accordingly (signed-out mock ⇒ redirect; signed-in mock ⇒ studio renders).

- [ ] **Step 5: Verify GREEN and gates**

Run: `npm --prefix frontend run test:unit -- src/features/auth src/app && npm --prefix frontend run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: guard the studio behind the real session"
```

### Task 2: Mount httpApi at the composition root

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/services/mockApi.ts` (session-aware auth mock for tests)
- Test: `frontend/src/app/App.test.tsx`, `frontend/src/test/smoke.test.tsx` (update to routed app)

**Interfaces:**
- Consumes: `httpApi` from Task 9 of the backend plan; `SessionProvider` from Task 1.
- Produces: a production entry that talks only to `/api`; mock auth helpers for tests (`createMockApi({ session: 'anonymous' | 'author' })`).

- [ ] **Step 1: Write the failing entry test** — smoke test renders the routed app with an injected mock and asserts no module imports `createMockApi` from `main.tsx` (static assertion via reading the file in a unit test or via the anti-pattern script in Task 7).
- [ ] **Step 2: RED** — `npm --prefix frontend run test:unit -- src/test/smoke.test.tsx`
- [ ] **Step 3: Implement** — `main.tsx` builds `httpApi`, wraps `AppProviders` + `SessionProvider` + `RouterProvider`. `createMockApi` gains an options flag to start anonymous or authored so session tests are deterministic.
- [ ] **Step 4: GREEN + typecheck + build** — `npm --prefix frontend run test:unit && npm --prefix frontend run build`
- [ ] **Step 5: Commit** — `git commit -m "feat: mount the real API at the app root"`

### Task 3: Routed real library and book detail

**Files:**
- Create: `frontend/src/features/library/LibraryPage.tsx`
- Create: `frontend/src/features/library/useLibrary.ts`
- Rewrite: `frontend/src/features/library/BookDetailPage.tsx`
- Modify: `frontend/src/features/library/LibraryFormDialog.tsx`
- Modify: `frontend/src/app/router.tsx`
- Delete: `frontend/src/app/App.tsx` demo screens (and `app.css` selectors that die with them)
- Test: `frontend/src/features/library/library.test.tsx` (rewrite on real flows)

**Interfaces:**
- Consumes: `BooksAdminApi`, `WritingsAdminApi` via SWR hooks (`useBooks`, `useBookWritings`).
- Produces: `/studio` (library) and `/studio/livros/:bookId` (detail) pages with create-book and create-writing flows that navigate to the workspace.

- [ ] **Step 1: Failing tests** — list renders books from the injected API with `writingCount`; empty library shows the empty state with a working “Adicionar livro”; create book submits once with a stable `Idempotency-Key` across a retry (spy on `books.create`); create writing navigates to `/studio/escritas/:id`; API failure shows retry that refetches.
- [ ] **Step 2: RED** — `npm --prefix frontend run test:unit -- src/features/library`
- [ ] **Step 3: Implement** — SWR hooks with stable keys (`books`, `books/:id/writings`); dialogs generate their idempotency key on open (`useRef` + `crypto.randomUUID()`), reuse it on retry, regenerate on reopen; `mutate` after create; keep the existing visual components (cards, dialogs, empty state) and the pt-BR copy. Remove the demo `App.tsx` and update every test that imported it.
- [ ] **Step 4: GREEN + a11y** — `npm --prefix frontend run test:unit -- src/features/library src/test/accessibility.test.tsx`
- [ ] **Step 5: Commit** — `git commit -m "feat: drive the library from the real API"`

### Task 4: Workspace on real data with version concurrency and history

**Files:**
- Modify: `frontend/src/features/workspace/WorkspacePage.tsx`
- Modify: `frontend/src/features/workspace/WorkspaceProvider.tsx`
- Create: `frontend/src/features/workspace/VersionHistory.tsx`
- Create: `frontend/src/features/workspace/ConflictNotice.tsx`
- Test: `frontend/src/features/workspace/workspace.test.tsx` (extend)

**Interfaces:**
- Consumes: `writings.getWorkspace`, `writings.save({ id, markdown, expectedVersion })`, `writings.listVersions`, `writings.restoreVersion`, `ApiError`.
- Produces: `WorkspaceProvider` tracking `{ writing, expectedVersion, saveState: … | 'conflict' }` and actions `{ updateMarkdown, retrySave, reloadCanonical, restoreVersion }`.

- [ ] **Step 1: Failing tests**

```tsx
it('salva com a versão esperada e a incrementa após o sucesso', async () => { /* save called with expectedVersion 4 then 5 */ })
it('conflito preserva o texto local e recarregar traz o canônico', async () => {
  /* save rejects ApiError writing_version_conflict {currentVersion: 6} →
     saveState 'conflict', editor keeps local text, 'Recarregar versão atual'
     refetches and updates expectedVersion */
})
it('restaura uma versão anterior criando uma nova versão', async () => { /* listVersions + restoreVersion */ })
```

- [ ] **Step 2: RED** — `npm --prefix frontend run test:unit -- src/features/workspace`
- [ ] **Step 3: Implement** — `WorkspacePage` loads `getWorkspace(:writingId)` (route param, SWR) with loading/error/retry surfaces; provider receives the loaded writing, saves through the injected port, maps `ApiError.code === 'writing_version_conflict'` to the existing `conflict` state, and exposes `reloadCanonical`. `ConflictNotice` renders inside the save-status area with the reload action; `VersionHistory` is a collapsible list (cursor pagination, “Restaurar” per row) reachable from the book-context rail. Breadcrumb/title come from the real writing.
- [ ] **Step 4: GREEN** — focused workspace suite plus `src/app` tests.
- [ ] **Step 5: Commit** — `git commit -m "feat: run the workspace on versioned real saves"`

### Task 5: Publication lifecycle in the workspace

**Files:**
- Modify: `frontend/src/features/publishing/PublishDialog.tsx`
- Modify: `frontend/src/features/publishing/PublicationStatus.tsx`
- Modify: `frontend/src/features/workspace/WorkspacePage.tsx`
- Test: `frontend/src/features/publishing/publishing.test.tsx` (extend)

**Interfaces:**
- Consumes: `publishing.publish(writingId, key)`, `getStatus`, `cancelCleanup`, `unpublish`.
- Produces: a “Publicar” action in the workspace header, a status panel with the exact `pt-BR` cleanup date, and recovery actions.

- [ ] **Step 1: Failing tests** — publish sends one idempotency key and shows slug + formatted cleanup date; `publication_already_active` renders as an explanatory state; “Cancelar limpeza” and “Voltar para rascunho” call the API and update the panel; failure keeps the draft and explains.
- [ ] **Step 2: RED** — `npm --prefix frontend run test:unit -- src/features/publishing`
- [ ] **Step 3: Implement** — wire the dialog to the injected port (key per dialog opening), render `PublicationStatus` from `getStatus` when the writing is published/cleanup_scheduled, link to `/artigos/:slug`.
- [ ] **Step 4: GREEN** and commit — `git commit -m "feat: publish through the real lifecycle"`

### Task 6: Real frozen public article

**Files:**
- Modify: `frontend/src/public-site/PublicArticlePage.tsx`
- Modify: `frontend/src/public-site/usePublicContent.ts`
- Test: `frontend/src/public-site/public-discovery.test.tsx` (extend)

**Interfaces:**
- Consumes: `public.getArticle(slug)` (`PublicArticleDetail.markdown`).
- Produces: the article page rendering the frozen Markdown through the sanitized renderer, loaded lazily on the article route.

- [ ] **Step 1: Failing test** — article page renders heading/paragraphs from the fixture’s `markdown` (not hardcoded prose); a missing slug shows the existing not-found state; `verify:bundles` still excludes heavy modules from the initial public chunk.
- [ ] **Step 2: RED** — `npm --prefix frontend run test:unit -- src/public-site`
- [ ] **Step 3: Implement** — `usePublicArticle(slug)` hook; lazy-load the sanitized Markdown renderer (`React.lazy` + Suspense) on this route only; keep `prose` measure and meta. Update mock fixtures/handlers with `markdown` on the detail shape.
- [ ] **Step 4: GREEN + bundle gate** — `npm --prefix frontend run test:unit -- src/public-site && npm --prefix frontend run build && npm --prefix frontend run verify:bundles`
- [ ] **Step 5: Commit** — `git commit -m "feat: render frozen public articles"`

### Task 7: Honest shell and static gates

**Files:**
- Modify: studio header/shell components (budget removal, session menu with “Sair”)
- Modify: `frontend/scripts/check-anti-patterns.mjs`
- Modify: `UX-CONTRACT.md`, `premium-ui.json`

- [ ] **Step 1: Failing static gate** — extend the anti-pattern script to fail when `main.tsx` imports `createMockApi`, when any `src/features/**` file calls `fetch(` directly (must go through the port), or when the literal budget string reappears.
- [ ] **Step 2: Implement** — remove the fake budget from the shell (until UsageApi exists), add the authenticated header (author e-mail + “Sair” calling `signOut`), label the assistant panel as demonstrative. Update `UX-CONTRACT.md` (session ledger rows: entrar, sair, sessão expirada, conflito de versão, publicar/retirar) and `premium-ui.json` evidence pointers.
- [ ] **Step 3: Verify** — `npm --prefix frontend run verify:premium && npm --prefix frontend run test:unit`
- [ ] **Step 4: Commit** — `git commit -m "chore: honest shell and integration gates"`

### Task 8: E2E from the login screen against the real stack

**Files:**
- Modify: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/auth-flow.spec.ts`
- Rewrite: `frontend/tests/e2e/library-flow.spec.ts`, `workspace-flow.spec.ts`, `workspace-failures.spec.ts`, `publish-flow.spec.ts`
- Create: `ops/dev-stack.md` (how to run the stack for tests)
- Modify: `docs/handoffs/current.md`

**Interfaces:**
- Consumes: Compose stack (`db`, `backend` with `PUBLIC_ORIGIN=http://127.0.0.1:4173`), seeded author via `docker compose run --rm bootstrap-author` (`AUTHOR_EMAIL=e2e@example.com`, password from `.env`), Vite dev server on 4173 proxying `/api`.
- Produces: a login helper (`signIn(page)`), specs that begin authenticated through the real cookie, and a documented one-command stack bring-up.

- [ ] **Step 1: Stack plumbing** — document and script the sequence: `docker compose up -d db backend` (test env file with `PUBLIC_ORIGIN=http://127.0.0.1:4173`), migrate, bootstrap the E2E author idempotently, then `npm run test:e2e`. Playwright keeps `reuseExistingServer` and gains a `globalSetup` that fails fast with a clear message when `/api/health/ready` is unreachable (environmental block reported, never faked).
- [ ] **Step 2: Auth spec (failing first against unwired UI)** — invalid credentials show the inline error; valid credentials land on the library; direct `/studio` access when anonymous redirects to `/entrar` and returns after login; “Sair” ends the session.
- [ ] **Step 3: Full journey spec** — login → create book → create writing → type and observe “Salvo” → publish (capture slug) → anonymous context reads `/artigos/:slug` with the frozen content and no private markers (`/writing-|prompt|transcrição/i`) → withdraw → article 404s publicly.
- [ ] **Step 4: Concurrency spec** — two browser contexts on the same writing; the stale one sees the conflict notice and recovers via “Recarregar versão atual” without losing its local text into silence.
- [ ] **Step 5: Run the whole matrix**

```bash
npm --prefix frontend run lint && npm --prefix frontend run typecheck \
  && npm --prefix frontend run test:unit && npm --prefix frontend run build \
  && npm --prefix frontend run verify:premium && npm --prefix frontend run verify:bundles \
  && npm --prefix frontend run test:a11y && npm --prefix frontend run test:e2e
```

Expected: all green with the stack up. Known machine limitation: Playwright needs Chromium system libraries (`sudo npx playwright install-deps`); if absent, record the block in the handoff instead of claiming browser verification.

- [ ] **Step 6: Update the handoff and commit**

```bash
git add frontend ops docs
git commit -m "test: verify the integrated studio end to end"
```

## Plan Self-Review Notes

- Task order is dependency-driven: session (1) unblocks the root swap (2); library (3) and workspace (4) need both; publication (5) needs the workspace; the public article (6) is independent after 2; gates (7) and E2E (8) close the phase.
- The demo `App.tsx` deletion lands with Task 3, when its last consumer (the studio placeholder) is replaced — no dead code lingers between commits.
- Chat/audio/suggestions/usage remain explicitly mocked and labeled; no task adds AI scope.
- Backend changes are expected to be zero; if a contract gap appears (e.g., a missing field), it must go through a focused backend commit with its own test, not a frontend workaround.
- Every task keeps the composition rules: pages own routing/data wiring, providers own state, visual components stay port-agnostic and reusable.
