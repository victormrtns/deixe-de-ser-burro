# Visual Identity and Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, responsive React frontend for the private writing studio and public reading experience, beginning with a durable visual identity and running against typed mock contracts until the FastAPI backend exists.

**Architecture:** Create a React 19 + TypeScript SPA organized by product feature, with shared visual primitives and compound components for the writing workspace. Server data is accessed only through typed service interfaces backed first by MSW; SWR owns request deduplication and revalidation, while transient editor, recorder, and streaming state stays inside focused providers.

**Tech Stack:** React 19, TypeScript 5.9, Vite 7, React Router 7, Tailwind CSS 4, SWR 2, CodeMirror 6, react-markdown, Mermaid, KaTeX, Radix UI primitives, Vitest, Testing Library, MSW, Playwright, axe-core.

**Spec:** `docs/superpowers/specs/2026-08-28-ai-books-learning-blog-design.md`

## Global Constraints

- The frontend language is Brazilian Portuguese and the locale is `pt-BR`.
- The accessibility target is WCAG 2.2 AA.
- Markdown is the canonical article format; preview supports GFM, Mermaid, code blocks, and embedded LaTeX.
- AI output never mutates Markdown directly; only an accepted suggestion creates a new visible version.
- Every audio, conversation, transcript, link, suggestion, and version belongs to exactly one writing.
- One author uses the private studio; published articles are readable without authentication.
- Publishing creates a frozen public version and exposes a three-day recovery period before private work context is deleted.
- API keys and secrets never enter the frontend bundle, URL, analytics, logs, toast text, or local storage.
- Local storage is versioned and limited to non-sensitive UI preferences; server content remains authoritative.
- React components use composition, explicit business variants, and focused providers instead of boolean-prop mode matrices.
- Independent requests run in parallel; heavy editor, Mermaid, diff, and math modules load only on routes or modes that need them.
- Imports are direct and statically analyzable; feature folders do not expose broad barrel files.
- Every async surface covers idle, pending, success, empty, error, cancellation, and retry where the operation supports retry.
- Interactive elements use native semantics, visible focus, stable busy geometry, pointer affordance, and reduced-motion support.
- Product dialogs are app-owned; browser `alert`, `confirm`, and `prompt` are prohibited.
- The application uses one global, visible, tokenized scrollbar baseline and stable scroll ownership per panel.

## Planned File Structure

```text
DESIGN.md                              durable visual identity and token rationale
UX-CONTRACT.md                         navigation, feedback, draft and async behavior
premium-ui.json                        machine-readable UI verification contract
frontend/
├── package.json                       scripts and pinned frontend dependencies
├── vite.config.ts                     Vite, React, aliases and test configuration
├── playwright.config.ts               browser and screenshot projects
├── index.html                         SPA entry document
├── src/
│   ├── app/
│   │   ├── App.tsx                    providers and router boundary
│   │   ├── router.tsx                 public/private/error route definitions
│   │   └── providers.tsx              SWR, toast and session composition
│   ├── styles/
│   │   ├── tokens.css                 DESIGN.md token implementation
│   │   ├── globals.css                reset, typography, focus and scrollbar
│   │   └── prose.css                  public article and preview typography
│   ├── ui/                             reusable behavior and visual primitives
│   ├── features/
│   │   ├── auth/                       single-author sign-in UI
│   │   ├── library/                    books and writing collections
│   │   ├── workspace/                  editor, preview and responsive shell
│   │   ├── chat/                       streaming messages and composer
│   │   ├── audio/                      recorder and transcription cards
│   │   ├── suggestions/                diff and approval flow
│   │   └── publishing/                 publish and retention UI
│   ├── public-site/                    public library and article reading routes
│   ├── services/                       typed ports, HTTP adapter and mock handlers
│   ├── test/                           test setup, fixtures and render helpers
│   └── main.tsx                        application bootstrap
└── tests/e2e/                          Playwright workflows and visual baselines
```

---

### Task 1: Establish the durable identity and UX contract

**Files:**
- Create: `DESIGN.md`
- Create: `UX-CONTRACT.md`
- Create: `premium-ui.json`
- Reference: `design.md`
- Reference: `tailwind.css`

**Interfaces:**
- Consumes: the approved product spec and the existing cream-paper style reference.
- Produces: exact token names consumed by `frontend/src/styles/tokens.css` and behavioral rules consumed by every later task.

- [ ] **Step 1: Write the identity brief into `DESIGN.md`**

Use `deixedeserburro` as the working product name and define the North Star as “a living reading notebook: calm paper surfaces, visible marginalia, and one strong ink action.” Preserve the useful reference tokens while removing crypto-specific roles. Record these exact core tokens:

```yaml
---
version: alpha
colors:
  canvas: "#fbfaf9"
  surface: "#ffffff"
  surfaceMuted: "#f2f0ed"
  ink: "#121212"
  text: "#343433"
  textMuted: "#6f6d69"
  border: "#e5d5c3"
  link: "#0086fc"
  annotation: "#ff3e00"
  pending: "#d48f00"
  success: "#007a4d"
  danger: "#c91d2e"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Inter, sans-serif"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
  code:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
rounded:
  small: "6px"
  card: "10px"
  control: "12px"
  pill: "9999px"
spacing:
  unit: "4px"
components:
  surface:
    border: "inset 0 0 0 1px #f2f0ed"
  focusRing:
    color: "#0086fc"
---
```

Describe the signature element as a margin rail: audio, prompt, source, and accepted suggestion events appear as small colored marks aligned with the document, linking the act of thinking to the written page. Limit expressive illustrations to empty states and public covers; keep the writing studio quiet and utilitarian.

- [ ] **Step 2: Record product behavior in `UX-CONTRACT.md`**

Define the route map and the behavior ledger:

```markdown
| Operation | Trigger | Pending | Success | Failure recovery |
|---|---|---|---|---|
| Save draft | editor change, 800 ms debounce | “Salvando…” | “Salvo” inline | preserve text, retry |
| Send prompt | “Enviar” | streaming message + Stop | persisted response | retry last prompt |
| Record audio | “Gravar” | elapsed time + Stop | processing card | retain local blob, retry upload |
| Accept suggestion | “Aceitar alteração” | locked diff actions | new document version | refetch canonical version |
| Publish | confirmation dialog | stable busy button | public URL + 3-day notice | keep draft and explain failure |
```

Specify route titles, focus restoration, panel scroll ownership, mobile navigation, session expiry, unsaved-draft recovery, toast semantics, dialog semantics, and public/private route separation.

- [ ] **Step 3: Create `premium-ui.json` with executable gates**

```json
{
  "profile": "product-admin",
  "sourceRoots": ["frontend/src"],
  "locale": "pt-BR",
  "canonicalMap": "UX-CONTRACT.md",
  "requiredCapabilities": ["Form", "Scrollbar", "Toast", "CRUD"],
  "requiredCommands": ["unit", "e2e", "accessibility", "premium"],
  "commands": {
    "unit": "npm --prefix frontend run test:unit",
    "e2e": "npm --prefix frontend run test:e2e",
    "accessibility": "npm --prefix frontend run test:a11y",
    "premium": "npm --prefix frontend run verify:premium"
  },
  "evidence": {
    "crudFullFlow": "frontend/tests/e2e/library-flow.spec.ts",
    "failurePaths": "frontend/tests/e2e/workspace-failures.spec.ts"
  }
}
```

- [ ] **Step 4: Validate the design document**

Run: `npx -p @google/design.md designmd lint DESIGN.md`

Expected: exit code 0 and zero lint errors.

- [ ] **Step 5: Commit the contracts**

```bash
git add DESIGN.md UX-CONTRACT.md premium-ui.json
git commit -m "docs: define visual identity and frontend UX contract"
```

### Task 2: Scaffold the typed React application and quality gates

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/smoke.test.tsx`

**Interfaces:**
- Consumes: Node.js 22+, the root contracts, and React 19 APIs.
- Produces: `App(): JSX.Element`, test commands, `@/` path alias, and a browser-test server at `http://127.0.0.1:4173`.

- [ ] **Step 1: Create the failing smoke test**

```tsx
import { render, screen } from '@testing-library/react'
import { App } from '@/app/App'

it('renders the product landmark', () => {
  render(<App />)
  expect(screen.getByRole('main')).toBeInTheDocument()
})
```

- [ ] **Step 2: Create package scripts and install the pinned toolchain**

Define `dev`, `build`, `typecheck`, `lint`, `test:unit`, `test:e2e`, `test:a11y`, and `verify:premium` scripts. Add React, React DOM, React Router, SWR, Tailwind, Radix primitives, `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/inter`, `@fontsource/ibm-plex-mono`, Vitest, Testing Library, MSW, Playwright, axe-core, ESLint and Prettier. Configure TypeScript with `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes`.

- [ ] **Step 3: Run the test to verify the missing app fails**

Run: `npm --prefix frontend run test:unit -- smoke.test.tsx`

Expected: FAIL because `@/app/App` does not exist.

- [ ] **Step 4: Add the minimal application boundary**

```tsx
export function App() {
  return <main aria-label="deixedeserburro">deixedeserburro</main>
}
```

- [ ] **Step 5: Verify the scaffold**

Run: `npm --prefix frontend run typecheck && npm --prefix frontend run test:unit -- smoke.test.tsx && npm --prefix frontend run build`

Expected: all three commands exit 0.

- [ ] **Step 6: Commit the scaffold**

```bash
git add frontend
git commit -m "build: scaffold typed React frontend"
```

### Task 3: Map identity tokens to runtime and create shared primitives

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/styles/prose.css`
- Create: `frontend/src/ui/Button.tsx`
- Create: `frontend/src/ui/Surface.tsx`
- Create: `frontend/src/ui/Field.tsx`
- Create: `frontend/src/ui/Dialog.tsx`
- Create: `frontend/src/ui/ToastProvider.tsx`
- Test: `frontend/src/ui/primitives.test.tsx`

**Interfaces:**
- Consumes: exact tokens from `DESIGN.md`.
- Produces: `Button` explicit variants (`PrimaryButton`, `NeutralButton`, `DangerButton`), `Surface`, `Field`, `Dialog`, and `useToast(): ToastActions`.

- [ ] **Step 1: Write failing semantic and accessibility tests**

```tsx
it('keeps intent explicit and restores dialog focus', async () => {
  const user = userEvent.setup()
  render(<PrimitiveHarness />)
  await user.click(screen.getByRole('button', { name: 'Excluir escrita' }))
  expect(screen.getByRole('alertdialog')).toHaveAccessibleName('Excluir escrita')
  await user.keyboard('{Escape}')
  expect(screen.getByRole('button', { name: 'Excluir escrita' })).toHaveFocus()
})
```

- [ ] **Step 2: Implement the runtime token mapping**

Map every `DESIGN.md` color, type, radius, spacing, shadow, focus, scrollbar, and reduced-motion value once in `tokens.css`. Import the three font packages and the token sheet from `globals.css`; do not duplicate raw values inside components.

- [ ] **Step 3: Implement explicit primitives without boolean modes**

```tsx
type ButtonProps = React.ComponentProps<'button'>

export function PrimaryButton(props: ButtonProps) {
  return <button {...props} className={buttonClass('solid', 'brand', props.className)} />
}

export function DangerButton(props: ButtonProps) {
  return <button {...props} className={buttonClass('solid', 'danger', props.className)} />
}
```

Use Radix only for focus-management-heavy primitives and import from direct package paths. Keep button dimensions stable while busy and expose status through an accessible live region.

- [ ] **Step 4: Run primitive tests and design lint**

Run: `npm --prefix frontend run test:unit -- primitives.test.tsx && npx -p @google/design.md designmd lint DESIGN.md`

Expected: PASS and zero design errors.

- [ ] **Step 5: Commit the visual foundation**

```bash
git add DESIGN.md frontend/src/styles frontend/src/ui
git commit -m "feat: add visual tokens and accessible UI primitives"
```

### Task 4: Define typed frontend contracts and MSW scenarios

**Files:**
- Create: `frontend/src/services/contracts.ts`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/httpApi.ts`
- Create: `frontend/src/services/mock/fixtures.ts`
- Create: `frontend/src/services/mock/handlers.ts`
- Create: `frontend/src/services/mock/browser.ts`
- Create: `frontend/src/services/mock/server.ts`
- Test: `frontend/src/services/api.test.ts`

**Interfaces:**
- Consumes: the product hierarchy and state transitions from the spec.
- Produces: `BooksApi`, `WritingsApi`, `ChatApi`, `AudioApi`, `SuggestionsApi`, `PublishingApi`, `UsageApi`, and `AppApi`.

- [ ] **Step 1: Write a failing contract test**

```ts
it('keeps work artifacts scoped to one writing', async () => {
  const result = await api.writings.getWorkspace('writing-deep-work-01')
  expect(result.writing.bookId).toBe('book-deep-work')
  expect(result.messages.every(item => item.writingId === result.writing.id)).toBe(true)
  expect(result.audio.every(item => item.writingId === result.writing.id)).toBe(true)
})
```

- [ ] **Step 2: Define exact domain types**

```ts
export type WritingStatus = 'draft' | 'published' | 'cleanup_scheduled'
export type JobStatus = 'queued' | 'uploading' | 'transcribing' | 'analyzing' | 'ready' | 'failed'
export type SuggestionStatus = 'pending' | 'accepted' | 'rejected'

export interface Writing {
  id: string
  bookId: string
  title: string
  markdown: string
  sourceRange: string
  status: WritingStatus
  version: number
  updatedAt: string
}

export interface AppApi {
  books: BooksApi
  writings: WritingsApi
  chat: ChatApi
  audio: AudioApi
  suggestions: SuggestionsApi
  publishing: PublishingApi
  usage: UsageApi
}
```

Define `UsageSummary` with `period`, `audioMinutes`, `estimatedAiCostBrl`, `monthlyLimitBrl`, and `limitState: 'normal' | 'near_limit' | 'blocked'`. Mock the normal, near-limit, and blocked states so cost behavior can be tested before backend integration.

- [ ] **Step 3: Implement realistic mock scenarios**

Create success, empty, slow, validation-error, network-error, conflict, and session-expired handlers. Use deterministic IDs and Brazilian Portuguese content from real-looking book notes rather than lorem ipsum.

- [ ] **Step 4: Verify contracts and request deduplication**

Run: `npm --prefix frontend run test:unit -- api.test.ts`

Expected: PASS, including a test proving two SWR consumers issue one GET request.

- [ ] **Step 5: Commit the mock contract boundary**

```bash
git add frontend/src/services
git commit -m "feat: define frontend API contracts and mock scenarios"
```

### Task 5: Build routing, session boundary, and responsive application shell

**Files:**
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/features/auth/SessionProvider.tsx`
- Create: `frontend/src/features/auth/RequireAuthor.tsx`
- Create: `frontend/src/features/auth/SignInPage.tsx`
- Create: `frontend/src/ui/AppShell.tsx`
- Create: `frontend/src/ui/RouteErrorPage.tsx`
- Create: `frontend/src/ui/useDocumentTitle.ts`
- Create: `frontend/src/features/usage/UsageBudgetIndicator.tsx`
- Test: `frontend/src/app/router.test.tsx`
- Test: `frontend/src/features/usage/usage.test.tsx`

**Interfaces:**
- Consumes: `AppApi`, `UsageApi.getCurrent()`, `ToastProvider`, route rules from `UX-CONTRACT.md`.
- Produces: public routes `/`, `/livros/:bookSlug/:articleSlug`; private routes `/studio`, `/studio/livros/:bookId`, `/studio/escritas/:writingId`; explicit `/entrar`, 403, 404 and route-error surfaces; and a persistent monthly usage indicator in the private shell.

- [ ] **Step 1: Write route protection and title tests**

```tsx
it('returns an unauthenticated author to the requested route after sign-in', async () => {
  renderAppAt('/studio/escritas/writing-01', { session: null })
  expect(await screen.findByRole('heading', { name: 'Entrar no estúdio' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
})
```

- [ ] **Step 2: Implement providers and route boundaries**

Keep the session contract injectable. Use a database-backed session later; the frontend mock exposes `SessionState = 'loading' | 'anonymous' | 'author' | 'expired'`. Preserve the requested URL through sign-in without putting secrets in query parameters.

- [ ] **Step 3: Implement the responsive shell**

Use a persistent desktop sidebar and an accessible mobile drawer. The public routes use a quiet reading header instead of product navigation. Assign scroll ownership to the workspace panels, not the global page shell.

- [ ] **Step 4: Implement visible budget states**

Render “R$ 12,40 de R$ 70,00” in the private shell. At 80% show a warning treatment with text and icon; at 100% explain that AI actions are paused while editing and publishing remain available. Do not infer client-side authorization from this badge: the backend remains responsible for enforcing the limit.

- [ ] **Step 5: Verify navigation, budget, keyboard, and narrow viewport behavior**

Run: `npm --prefix frontend run test:unit -- router.test.tsx usage.test.tsx`

Expected: PASS for public access, protected access, 403, 404, title updates, normal/warning/blocked budget states, Escape-close, and trigger focus restoration.

- [ ] **Step 6: Commit the application shell**

```bash
git add frontend/src/app frontend/src/features/auth frontend/src/features/usage frontend/src/ui/AppShell.tsx frontend/src/ui/RouteErrorPage.tsx frontend/src/ui/useDocumentTitle.ts
git commit -m "feat: add responsive shell and private route boundary"
```

### Task 6: Implement the library and book-writing flows

**Files:**
- Create: `frontend/src/features/library/LibraryPage.tsx`
- Create: `frontend/src/features/library/BookCard.tsx`
- Create: `frontend/src/features/library/BookDetailPage.tsx`
- Create: `frontend/src/features/library/BookFormDialog.tsx`
- Create: `frontend/src/features/library/WritingCard.tsx`
- Create: `frontend/src/features/library/LibraryEmptyState.tsx`
- Test: `frontend/src/features/library/library.test.tsx`
- Test: `frontend/tests/e2e/library-flow.spec.ts`

**Interfaces:**
- Consumes: `BooksApi`, `WritingsApi`, shared dialogs, fields, buttons and surfaces.
- Produces: book list/detail/create/edit/delete and writing create/open flows.

- [ ] **Step 1: Write failing CRUD and recovery tests**

```tsx
it('creates a writing inside the selected book', async () => {
  const user = userEvent.setup()
  renderLibraryWithMocks()
  await user.click(await screen.findByRole('link', { name: /Trabalho focado/i }))
  await user.click(screen.getByRole('button', { name: 'Nova escrita' }))
  await user.type(screen.getByLabelText('Título'), 'Ritual antes do foco')
  await user.click(screen.getByRole('button', { name: 'Criar escrita' }))
  expect(await screen.findByRole('heading', { name: 'Ritual antes do foco' })).toBeVisible()
})
```

- [ ] **Step 2: Implement SWR resources and explicit card variants**

Use `BookCard`, `DraftWritingCard`, and `PublishedWritingCard` as explicit compositions. Do not add `isDraft`, `isPublished`, or `showCleanup` flags to one generic card.

- [ ] **Step 3: Implement complete list and form states**

Cover loading with reserved geometry, empty library, empty book, validation failure, request failure with retry, deletion confirmation, and successful navigation. Forms use `noValidate`, inline errors, first-invalid-field focus, and duplicate-submit prevention.

- [ ] **Step 4: Run unit and browser tests**

Run: `npm --prefix frontend run test:unit -- library.test.tsx && npm --prefix frontend run test:e2e -- library-flow.spec.ts`

Expected: PASS for desktop and mobile projects.

- [ ] **Step 5: Commit the library flow**

```bash
git add frontend/src/features/library frontend/tests/e2e/library-flow.spec.ts
git commit -m "feat: add book and writing library flows"
```

### Task 7: Build the compound writing workspace and lazy editor preview

**Files:**
- Create: `frontend/src/features/workspace/WorkspacePage.tsx`
- Create: `frontend/src/features/workspace/WorkspaceProvider.tsx`
- Create: `frontend/src/features/workspace/Workspace.tsx`
- Create: `frontend/src/features/workspace/MarkdownEditor.tsx`
- Create: `frontend/src/features/workspace/MarkdownPreview.tsx`
- Create: `frontend/src/features/workspace/MarginRail.tsx`
- Create: `frontend/src/features/workspace/useAutosave.ts`
- Create: `frontend/src/features/workspace/workspace.css`
- Test: `frontend/src/features/workspace/workspace.test.tsx`

**Interfaces:**
- Consumes: `WritingsApi.getWorkspace(id)`, `WritingsApi.save({ id, markdown, expectedVersion })`, and `Writing`.
- Produces: `Workspace.Provider`, `Workspace.Frame`, `Workspace.Navigation`, `Workspace.Editor`, `Workspace.Preview`, `Workspace.Assistant`, and `Workspace.MarginRail`.

- [ ] **Step 1: Write failing autosave and composition tests**

```tsx
it('saves after 800 ms and preserves text when the request fails', async () => {
  vi.useFakeTimers()
  renderWorkspace({ saveScenario: 'network-error' })
  await userEvent.type(await screen.findByRole('textbox', { name: 'Conteúdo Markdown' }), 'Uma nova ideia')
  await vi.advanceTimersByTimeAsync(800)
  expect(screen.getByText('Não foi possível salvar. Tentar novamente')).toBeVisible()
  expect(screen.getByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue(expect.stringContaining('Uma nova ideia'))
})
```

- [ ] **Step 2: Implement the generic workspace context**

```ts
export interface WorkspaceState {
  writing: Writing
  editorMode: 'edit' | 'preview' | 'split'
  saveState: 'idle' | 'dirty' | 'saving' | 'saved' | 'failed' | 'conflict'
}

export interface WorkspaceActions {
  updateMarkdown(markdown: string): void
  changeMode(mode: WorkspaceState['editorMode']): void
  retrySave(): Promise<void>
  reloadCanonical(): Promise<void>
}
```

The provider owns state and actions; visual children consume this interface with React 19 `use()`. Derive status labels during render rather than mirroring them through effects.

- [ ] **Step 3: Lazy-load expensive editing and rendering modules**

Load CodeMirror only on the private workspace route. Load Mermaid and KaTeX only when preview is first opened, using statically analyzable `import()` calls and a stable fallback. Use `useDeferredValue(markdown)` so typing remains responsive while preview catches up.

- [ ] **Step 4: Implement the responsive three-region workspace**

Desktop uses navigation, editor/preview and assistant regions. Tablet collapses navigation. Mobile switches between “Escrever”, “Visualizar” and “Assistente” as route-preserving tabs. The margin rail maps source events to document time without becoming the only way to access them.

- [ ] **Step 5: Run workspace tests and measure the initial bundle**

Run: `npm --prefix frontend run test:unit -- workspace.test.tsx && npm --prefix frontend run build`

Expected: PASS; the initial public chunk does not contain CodeMirror, Mermaid or KaTeX.

- [ ] **Step 6: Commit the writing workspace**

```bash
git add frontend/src/features/workspace
git commit -m "feat: add autosaving Markdown workspace"
```

### Task 8: Implement streaming chat as a compound composer

**Files:**
- Create: `frontend/src/features/chat/ChatProvider.tsx`
- Create: `frontend/src/features/chat/Chat.tsx`
- Create: `frontend/src/features/chat/MessageList.tsx`
- Create: `frontend/src/features/chat/PromptComposer.tsx`
- Create: `frontend/src/features/chat/useChatStream.ts`
- Test: `frontend/src/features/chat/chat.test.tsx`

**Interfaces:**
- Consumes: `ChatApi.list(writingId)`, `ChatApi.stream({ writingId, content, requestId, signal })`.
- Produces: `Chat.Provider`, `Chat.Frame`, `Chat.Messages`, `Chat.Composer`, `Chat.Send`, `Chat.Stop`, and a stream state machine.

- [ ] **Step 1: Write failing stream lifecycle tests**

```tsx
it('keeps partial output when the author stops generation', async () => {
  const user = userEvent.setup()
  renderChat({ stream: ['Primeiro ', 'parágrafo'] })
  await user.type(screen.getByLabelText('Mensagem'), 'Organize esta explicação')
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('Primeiro')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Parar geração' }))
  expect(screen.getByText('Geração interrompida')).toBeVisible()
})
```

- [ ] **Step 2: Implement stream parsing and cancellation**

Use a single `AbortController` stored in a ref. Parse complete SSE events across chunk boundaries, append through functional state updates, ignore late events after cancellation, and persist the final or interrupted message through the API port.

- [ ] **Step 3: Compose the chat UI without mode flags**

Create `IdlePromptComposer` and `StreamingPromptComposer` from shared `Chat` parts. The textarea auto-grows, uses `resize: none`, respects IME composition, and never sends on the Enter used to confirm composition.

- [ ] **Step 4: Implement long-history rendering behavior**

Apply `content-visibility: auto` and an intrinsic size to message cards. Auto-scroll only when the author is already near the bottom; otherwise show a “Nova resposta” control. Announce completion without stealing focus.

- [ ] **Step 5: Run chat tests**

Run: `npm --prefix frontend run test:unit -- chat.test.tsx`

Expected: PASS for streaming, stop, retry, malformed event, network failure, IME-safe send and scroll ownership.

- [ ] **Step 6: Commit the chat loop**

```bash
git add frontend/src/features/chat
git commit -m "feat: add cancellable contextual chat"
```

### Task 9: Add microphone recording and transcription job cards

**Files:**
- Create: `frontend/src/features/audio/RecorderProvider.tsx`
- Create: `frontend/src/features/audio/Recorder.tsx`
- Create: `frontend/src/features/audio/AudioJobCard.tsx`
- Create: `frontend/src/features/audio/useMediaRecorder.ts`
- Test: `frontend/src/features/audio/audio.test.tsx`

**Interfaces:**
- Consumes: browser `MediaRecorder`, `AudioApi.upload`, `AudioApi.getJob`, writing ID.
- Produces: recorder states `idle | requesting_permission | recording | preview | uploading | processing | failed` and accessible job cards.

- [ ] **Step 1: Write failing permission and retry tests**

```tsx
it('explains denied microphone permission and keeps file upload available', async () => {
  mockGetUserMediaRejected(new DOMException('Denied', 'NotAllowedError'))
  renderRecorder()
  await userEvent.click(screen.getByRole('button', { name: 'Gravar áudio' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Permita o microfone no navegador')
  expect(screen.getByLabelText('Enviar arquivo de áudio')).toBeEnabled()
})
```

- [ ] **Step 2: Implement the recorder state machine**

Keep elapsed time in a ref and update the visible counter at a bounded interval. Stop tracks on completion and unmount. Preserve the local blob after upload failure, allow discard through an app-owned confirmation dialog, and validate supported formats and size before upload.

- [ ] **Step 3: Implement processing cards**

Show named stages rather than fake percentages: “Enviando”, “Na fila”, “Transcrevendo”, “Organizando”, “Sugestão pronta”. Poll with bounded backoff, pause while the page is hidden, and provide explicit retry after terminal failure.

- [ ] **Step 4: Run audio tests**

Run: `npm --prefix frontend run test:unit -- audio.test.tsx`

Expected: PASS for permission denied, record/stop, upload cancellation, failed upload retention, processing recovery and track cleanup.

- [ ] **Step 5: Commit recording UI**

```bash
git add frontend/src/features/audio
git commit -m "feat: add audio capture and transcription states"
```

### Task 10: Add suggestion diff, approval, and conflict recovery

**Files:**
- Create: `frontend/src/features/suggestions/SuggestionProvider.tsx`
- Create: `frontend/src/features/suggestions/SuggestionDiff.tsx`
- Create: `frontend/src/features/suggestions/SuggestionActions.tsx`
- Create: `frontend/src/features/suggestions/ConflictDialog.tsx`
- Test: `frontend/src/features/suggestions/suggestions.test.tsx`

**Interfaces:**
- Consumes: `SuggestionsApi.accept({ writingId, suggestionId, expectedVersion })`, `reject`, and `requestRevision`.
- Produces: side-by-side/inline accessible diff, `PendingSuggestionActions`, `ApplyingSuggestionActions`, and conflict recovery.

- [ ] **Step 1: Write failing approval safety tests**

```tsx
it('does not change Markdown before the suggestion is accepted', async () => {
  renderSuggestionWithWorkspace()
  const editor = await screen.findByRole('textbox', { name: 'Conteúdo Markdown' })
  expect(editor).toHaveValue('# Versão atual')
  expect(screen.getByText('Uma explicação mais linear')).toBeVisible()
  expect(editor).toHaveValue('# Versão atual')
})
```

- [ ] **Step 2: Lazy-load the diff engine and implement accessible output**

Render additions and removals with text labels and semantic markup, not color alone. Preserve whitespace and offer inline mode on narrow screens. Load the diff engine only when a pending suggestion exists.

- [ ] **Step 3: Implement pessimistic acceptance and conflict handling**

Lock only suggestion actions while applying. Send the current writing version. On 409, show a dialog offering “Recarregar versão atual”, “Copiar minhas alterações” and “Cancelar”; never overwrite silently.

- [ ] **Step 4: Run suggestion tests**

Run: `npm --prefix frontend run test:unit -- suggestions.test.tsx`

Expected: PASS for no pre-approval mutation, single acceptance, rejection, revision request, duplicate click prevention and version conflict.

- [ ] **Step 5: Commit suggestion review**

```bash
git add frontend/src/features/suggestions
git commit -m "feat: add reviewed AI suggestion flow"
```

### Task 11: Build publishing and the public reading experience

**Files:**
- Create: `frontend/src/features/publishing/PublishDialog.tsx`
- Create: `frontend/src/features/publishing/PublicationStatus.tsx`
- Create: `frontend/src/public-site/PublicLibraryPage.tsx`
- Create: `frontend/src/public-site/PublicBookPage.tsx`
- Create: `frontend/src/public-site/PublicArticlePage.tsx`
- Create: `frontend/src/public-site/PublicReadingShell.tsx`
- Test: `frontend/src/features/publishing/publishing.test.tsx`
- Test: `frontend/tests/e2e/publish-flow.spec.ts`

**Interfaces:**
- Consumes: `PublishingApi.publish`, `unpublish`, `cancelCleanup`, and public read endpoints.
- Produces: frozen article route, cleanup deadline display, recovery action, and sanitized reading UI.

- [ ] **Step 1: Write failing privacy and lifecycle tests**

```tsx
it('renders public Markdown without private work artifacts', async () => {
  renderPublicArticle('ritual-antes-do-foco')
  expect(await screen.findByRole('article')).toHaveTextContent('Ritual antes do foco')
  expect(screen.queryByText('Transcrição original')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Aceitar alteração' })).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Implement the publish confirmation and three-day notice**

Name the article and consequence in the dialog. Keep the least destructive action initially focused. After success, show the public URL, exact cleanup date in `pt-BR`, “Cancelar limpeza” and “Voltar para rascunho” while allowed.

- [ ] **Step 3: Implement the public editorial surface**

Use restrained book-cover illustration, generous prose measure, accessible heading hierarchy, code overflow, print styles and stable media geometry. Sanitize HTML; do not use unsanitized `dangerouslySetInnerHTML`. Keep public bundles free of editor, recorder, chat and diff modules.

- [ ] **Step 4: Run publishing tests and inspect bundles**

Run: `npm --prefix frontend run test:unit -- publishing.test.tsx && npm --prefix frontend run test:e2e -- publish-flow.spec.ts && npm --prefix frontend run build`

Expected: PASS; public route chunks exclude private workspace dependencies.

- [ ] **Step 5: Commit publishing and reading routes**

```bash
git add frontend/src/features/publishing frontend/src/public-site frontend/tests/e2e/publish-flow.spec.ts
git commit -m "feat: add publishing and public reading experience"
```

### Task 12: Enforce frontend QA, accessibility, visual regression, and performance gates

**Files:**
- Create: `frontend/tests/e2e/workspace-flow.spec.ts`
- Create: `frontend/tests/e2e/workspace-failures.spec.ts`
- Create: `frontend/tests/e2e/accessibility.spec.ts`
- Create: `frontend/tests/e2e/visual.spec.ts`
- Create: `frontend/scripts/check-bundles.mjs`
- Create: `frontend/scripts/check-anti-patterns.mjs`
- Modify: `frontend/package.json`
- Modify: `premium-ui.json`

**Interfaces:**
- Consumes: every route, state and shared primitive from Tasks 1–11.
- Produces: reproducible unit, E2E, accessibility, screenshot, bundle and static-contract gates.

- [ ] **Step 1: Add failing end-to-end state coverage**

Cover the complete flow `book → writing → prompt/audio → suggestion → accept → publish`, plus offline save failure, expired session, upload retry, stream cancellation, version conflict, cleanup cancellation, empty library, 404 and narrow viewport.

```ts
test('keeps the draft editable when AI is unavailable', async ({ page }) => {
  await page.goto('/studio/escritas/writing-deep-work-01?scenario=ai-error')
  await page.getByLabel('Mensagem').fill('Organize este trecho')
  await page.getByRole('button', { name: 'Enviar' }).click()
  await expect(page.getByRole('alert')).toContainText('Não foi possível gerar a resposta')
  await expect(page.getByLabel('Conteúdo Markdown')).toBeEditable()
})
```

- [ ] **Step 2: Add accessibility and visual baselines**

Run axe on sign-in, library, book detail, workspace, publish dialog and public article. Capture desktop `1440×1000` and mobile `390×844` screenshots for library, workspace idle, workspace suggestion, and public article. Test keyboard-only operation and 200% zoom for the workspace.

- [ ] **Step 3: Add deterministic static gates**

The anti-pattern script fails on browser dialogs, clickable non-semantic elements, unguarded local storage, non-sanitized HTML, missing route titles, broad feature barrel imports, and product textareas without the canonical component. The bundle script fails if CodeMirror, Mermaid, KaTeX or diff code enters the initial public chunk.

- [ ] **Step 4: Run the complete verification matrix**

Run:

```bash
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test:unit
npm --prefix frontend run build
npm --prefix frontend run test:a11y
npm --prefix frontend run test:e2e
npm --prefix frontend run verify:premium
npx -p @google/design.md designmd lint DESIGN.md
python /home/victormrtns/.codex/plugins/cache/openai-curated-remote/frontend-design-premium/1.4.0/skills/frontend-design-premium/scripts/audit_project.py . --mode strict
```

Expected: every command exits 0; no blocking premium audit findings; visual snapshots match approved baselines.

- [ ] **Step 5: Manually verify production behavior**

In a real browser, exercise success, loading, empty, failure and retry states; microphone denied; stopped stream; open dialogs; keyboard focus; reduced motion; one narrow viewport; one desktop viewport; 200% zoom; long Markdown; long chat; and a public article. Compare the library, book detail and workspace for consistent actions, feedback and visual language.

- [ ] **Step 6: Commit the gates**

```bash
git add frontend/tests frontend/scripts frontend/package.json premium-ui.json
git commit -m "test: enforce frontend quality and visual gates"
```

## Plan Self-Review Notes

- The plan intentionally implements only the frontend subsystem and typed mock boundary; FastAPI, PostgreSQL, background jobs and provider integration require separate plans.
- Every P0 frontend requirement in the product spec maps to a task: library (Task 6), editor (Task 7), chat (Task 8), audio (Task 9), suggestions (Task 10), auth shell (Task 5), publication (Task 11), and quality/cost-facing states through the typed contracts and Task 12.
- P1 chats auxiliares, link ingestion, export and search remain outside this frontend plan so the first executable slice stays focused.
- Composition rules shape the workspace and chat APIs; performance rules shape request deduplication, direct imports, deferred preview work, and route-level code splitting.
