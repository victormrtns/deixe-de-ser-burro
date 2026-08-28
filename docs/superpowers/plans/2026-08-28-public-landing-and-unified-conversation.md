# Public Landing and Unified Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved “Estante em movimento” public landing and make text, links, audio, transcriptions, assistant replies, and suggestions share one chronological writing conversation.

**Architecture:** Extend the existing typed service boundary with public projections and a discriminated conversation-event model, keeping mocks as the current adapter until FastAPI exists. Public routes consume only public types; the private workspace composes one conversation timeline and one multimodal composer beside the canonical Markdown document.

**Tech Stack:** React 19, TypeScript 5.9, React Router 7, SWR 2, MSW 2, Vite 7, Vitest, Testing Library, Playwright, axe-core, existing Entrelinhas CSS tokens and shared UI primitives.

**Spec:** `docs/superpowers/specs/2026-08-28-public-landing-and-unified-conversation-design.md`

**Required React Patterns:**
- `docs/patterns/vercel-composition-patterns/AGENTS.md`
- `docs/patterns/vercel-react-best-practices/AGENTS.md`

## Global Constraints

- Public copy is Brazilian Portuguese and locale formatting is `pt-BR`.
- WCAG 2.2 AA remains the accessibility target.
- A book is public only when it has at least one published article.
- Public responses and bundles never expose drafts, internal IDs, prompts, chat, audio, transcriptions, suggestions, or private reading progress.
- The featured article is selected manually, with the newest published article as backend/mock fallback.
- The landing does not sell AI, present SaaS metrics, or expose an author login CTA in its main hierarchy.
- Text, links, audio, transcriptions, assistant replies, and suggestions belong to one chronological conversation per writing.
- Audio or AI failures never block manual Markdown editing or unrelated conversation actions.
- AI output never mutates Markdown before explicit suggestion acceptance.
- Existing `DESIGN.md`, `UX-CONTRACT.md`, tokens, focus behavior, scrollbar baseline, reduced-motion behavior, and public/private bundle separation remain canonical.
- The private workspace follows the approved “Documento soberano” direction: each writing is isolated, the document owns 60–65% of usable desktop width with the assistant open, and both context rails are collapsible.
- Read and apply both required React pattern documents before implementation and again during final review.
- Complex workspace and composer APIs use compound components, focused providers, generic `state/actions/meta` context interfaces, composed children, and explicit business variants instead of boolean-prop mode matrices.
- Providers own state implementation; presentational components consume injected interfaces and do not couple themselves to SWR, recorder, streaming, or storage internals.
- Independent requests start in parallel, SWR deduplicates client reads, and public/private resource boundaries do not introduce request waterfalls.
- Imports remain direct and statically analyzable; CodeMirror, Markdown preview, Mermaid, KaTeX, diff, recorder-only code, and other heavy modules load only when the active route or mode needs them.
- Derived state is calculated during render, interaction logic stays in event handlers, effect dependencies remain primitive and narrow, and transient high-frequency values use refs instead of render state where appropriate.
- Long conversation and archive lists use rendering containment or virtualization only after measurement justifies it; no speculative memoization or optimization is added.

---

### Task 1: Add public projections and landing service contracts

**Files:**
- Modify: `frontend/src/services/contracts.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/services/mockApi.ts`
- Modify: `frontend/src/services/mock/fixtures.ts`
- Modify: `frontend/src/services/mock/handlers.ts`
- Test: `frontend/src/services/api.test.ts`

**Interfaces:**
- Consumes: existing `AppApi` adapter composition and MSW request conventions.
- Produces: `PublicArticleSummary`, `PublicBookSummary`, `PublicLanding`, `PublicApi.getLanding()`, `PublicApi.listArticles()`, and `PublicApi.listBooks()`.

- [ ] **Step 1: Write failing public-projection tests**

Add tests that require a featured article, published book filtering, and a public payload without private keys:

```ts
it('returns only public landing projections', async () => {
  const api = createMockApi()
  const landing = await api.public.getLanding()

  expect(landing.featuredArticle?.slug).toBe('ritual-antes-do-foco')
  expect(landing.publishedBooks).toHaveLength(2)
  expect(JSON.stringify(landing)).not.toMatch(/markdown|writingId|messages|audio|suggestions/)
})

it('omits books without published articles', async () => {
  const landing = await createMockApi().public.getLanding()
  expect(landing.publishedBooks.map((book) => book.slug)).not.toContain('livro-sem-publicacao')
})
```

- [ ] **Step 2: Run the contract tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/services/api.test.ts`

Expected: FAIL because `AppApi` has no `public` service and the projection types do not exist.

- [ ] **Step 3: Define exact public types and service interface**

Add to `contracts.ts`:

```ts
export interface PublicArticleSummary {
  slug: string
  title: string
  excerpt: string
  publishedAt: string
  readingMinutes: number
  coverImageUrl?: string
  sourceBook: { slug: string; title: string; author: string }
}

export interface PublicBookSummary {
  slug: string
  title: string
  author: string
  coverImageUrl?: string
  publishedArticleCount: number
  latestArticle: Pick<PublicArticleSummary, 'slug' | 'title' | 'publishedAt'>
  publicTopics: string[]
}

export interface PublicLanding {
  featuredArticle: PublicArticleSummary | null
  recentArticles: PublicArticleSummary[]
  publishedBooks: PublicBookSummary[]
}

export interface PublicApi {
  getLanding(): Promise<PublicLanding>
  listArticles(): Promise<PublicArticleSummary[]>
  listBooks(): Promise<PublicBookSummary[]>
}
```

Extend `AppApi` with `public: PublicApi`.

- [ ] **Step 4: Implement deterministic public mock projections**

Create at least six published article summaries across two public books plus one private-only book fixture. Implement `public.getLanding()` with a manually featured slug and newest-publication fallback:

```ts
const featuredSlug = 'ritual-antes-do-foco'

function createPublicLanding(): PublicLanding {
  const featuredArticle = publicArticles.find((article) => article.slug === featuredSlug)
    ?? [...publicArticles].sort(byNewestPublication)[0]
    ?? null

  return {
    featuredArticle,
    recentArticles: [...publicArticles].sort(byNewestPublication).slice(0, 5),
    publishedBooks: publicBooks.filter((book) => book.publishedArticleCount > 0),
  }
}
```

Mirror the same JSON shapes in MSW handlers at `/api/public/landing`, `/api/public/articles`, and `/api/public/books`.

- [ ] **Step 5: Run service tests and typecheck**

Run: `npm --prefix frontend run test:unit -- src/services/api.test.ts && npm --prefix frontend run typecheck`

Expected: all service tests pass and TypeScript exits 0.

- [ ] **Step 6: Commit the public contract boundary**

```bash
git add frontend/src/services
git commit -m "feat: add public editorial projections"
```

### Task 2: Build public data resources and route boundaries

**Files:**
- Create: `frontend/src/public-site/usePublicContent.ts`
- Create: `frontend/src/public-site/PublicArticlesPage.tsx`
- Create: `frontend/src/public-site/PublicBooksPage.tsx`
- Create: `frontend/src/public-site/PublicAboutPage.tsx`
- Modify: `frontend/src/public-site/PublicBookPage.tsx`
- Modify: `frontend/src/public-site/PublicReadingShell.tsx`
- Modify: `frontend/src/app/router.tsx`
- Test: `frontend/src/app/router.test.tsx`

**Interfaces:**
- Consumes: `PublicApi` from Task 1 and the existing app provider/API access pattern.
- Produces: `usePublicLanding()`, `usePublicArticles()`, `usePublicBooks()` and working `/artigos`, `/livros`, `/livros/:slug`, and `/sobre` routes.

- [ ] **Step 1: Write failing route and title tests**

```tsx
it.each([
  ['/artigos', /Artigos — Entrelinhas/],
  ['/livros', /Livros — Entrelinhas/],
  ['/livros/trabalho-focado', /Trabalho focado — Entrelinhas/],
  ['/sobre', /Sobre — Entrelinhas/],
])('renders the public route %s', async (path, title) => {
  render(<RouterProvider router={createAppRouter([path])} />)
  expect(await screen.findByRole('main')).toBeInTheDocument()
  await waitFor(() => expect(document.title).toMatch(title))
})
```

- [ ] **Step 2: Run route tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/app/router.test.tsx`

Expected: FAIL because three routes and their pages do not exist.

- [ ] **Step 3: Add SWR-backed public resource hooks**

Implement focused hooks with stable cache keys:

```ts
export function usePublicLanding() {
  return useSWR('public/landing', () => getApi().public.getLanding())
}

export function usePublicArticles() {
  return useSWR('public/articles', () => getApi().public.listArticles())
}

export function usePublicBooks() {
  return useSWR('public/books', () => getApi().public.listBooks())
}
```

Use the repository’s actual provider/API accessor; do not create a second global API instance.

- [ ] **Step 4: Add real public routes and honest page titles**

Register `/artigos`, `/livros`, `/livros/:slug`, and `/sobre` as public routes. Each page must render loading, error, empty, and success states through `PublicReadingShell` and `useDocumentTitle`.

- [ ] **Step 5: Update the public header navigation**

Render only working semantic links:

```tsx
<nav aria-label="Navegação pública">
  <Link to="/artigos">Artigos</Link>
  <Link to="/livros">Livros</Link>
  <Link to="/sobre">Sobre</Link>
</nav>
```

Do not add search or a visible author-login action in this task.

- [ ] **Step 6: Verify routes, titles, and public bundle imports**

Run: `npm --prefix frontend run test:unit -- src/app/router.test.tsx && npm --prefix frontend run verify:bundles`

Expected: route tests pass and the public initial bundle contains no private heavy modules.

- [ ] **Step 7: Commit the public route group**

```bash
git add frontend/src/app/router.tsx frontend/src/public-site
git commit -m "feat: add public editorial routes"
```

### Task 3: Implement the “Estante em movimento” landing modules

**Files:**
- Create: `frontend/src/public-site/FeaturedArticle.tsx`
- Create: `frontend/src/public-site/RecentArticles.tsx`
- Create: `frontend/src/public-site/PublishedBookCard.tsx`
- Create: `frontend/src/public-site/PublishedBooks.tsx`
- Create: `frontend/src/public-site/PublicArchive.tsx`
- Modify: `frontend/src/public-site/PublicLibraryPage.tsx`
- Create: `frontend/src/public-site/public-site.css`
- Test: `frontend/src/public-site/public-landing.test.tsx`

**Interfaces:**
- Consumes: `PublicLanding`, `PublicArticleSummary`, and `PublicBookSummary` from Task 1; hooks from Task 2.
- Produces: composable editorial modules and the complete `/` landing.

- [ ] **Step 1: Write failing landing-state and privacy tests**

```tsx
it('renders the featured article, recent articles and only published books', async () => {
  renderPublicRoute('/')
  expect(await screen.findByRole('heading', { name: 'O custo humano da eficiência' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Artigos recentes' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Estante publicada' })).toBeInTheDocument()
  expect(screen.queryByText('Livro sem publicação')).not.toBeInTheDocument()
})

it('renders a useful empty publication state', async () => {
  renderPublicRoute('/', { publicLanding: { featuredArticle: null, recentArticles: [], publishedBooks: [] } })
  expect(await screen.findByText('Os primeiros ensaios ainda estão sendo preparados.')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run landing tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/public-site/public-landing.test.tsx`

Expected: FAIL because the modules and public landing resource rendering do not exist.

- [ ] **Step 3: Implement focused landing components**

Keep each whole card/link semantic and avoid nested interactive controls:

```tsx
export function PublishedBookCard({ book }: { book: PublicBookSummary }) {
  return (
    <article className="published-book">
      <Link to={`/livros/${book.slug}`} aria-label={`Explorar artigos de ${book.title}`}>
        <BookCover book={book} />
        <div>
          <p>{book.author}</p>
          <h3>{book.title}</h3>
          <span>{book.publishedArticleCount} artigos publicados</span>
          <strong>{book.latestArticle.title}</strong>
        </div>
      </Link>
    </article>
  )
}
```

Use a typographic fallback when `coverImageUrl` is absent; do not create generic image placeholders.

- [ ] **Step 4: Compose loading, empty, error, partial, and success states**

`PublicLibraryPage` must keep its header and identity for every state. A failed image remains local to its card. A failed landing request provides `Tentar novamente` through SWR `mutate()`.

- [ ] **Step 5: Implement the approved editorial layout**

Map only existing CSS tokens. Desktop order is featured article → recent articles → published books → archive/about. Mobile uses one document scroll and full-width list cards. Ensure 320 px reflow, 200% zoom resilience, visible focus, and no hover-only content.

- [ ] **Step 6: Run landing tests and accessibility check**

Run: `npm --prefix frontend run test:unit -- src/public-site/public-landing.test.tsx src/test/accessibility.test.tsx`

Expected: landing and accessibility tests pass.

- [ ] **Step 7: Commit the landing experience**

```bash
git add frontend/src/public-site frontend/src/test/accessibility.test.tsx
git commit -m "feat: build public editorial landing"
```

### Task 4: Complete public book and article discovery flows

**Files:**
- Modify: `frontend/src/public-site/PublicArticlesPage.tsx`
- Modify: `frontend/src/public-site/PublicBooksPage.tsx`
- Modify: `frontend/src/public-site/PublicBookPage.tsx`
- Modify: `frontend/src/public-site/PublicArticlePage.tsx`
- Modify: `frontend/src/styles/prose.css`
- Test: `frontend/src/public-site/public-discovery.test.tsx`
- Modify: `frontend/tests/e2e/publish-flow.spec.ts`

**Interfaces:**
- Consumes: public resource hooks, public projections, and landing modules.
- Produces: complete landing → book → article and landing → archive → article navigation.

- [ ] **Step 1: Write failing public navigation tests**

```tsx
it('navigates from a published book to one of its articles', async () => {
  const user = userEvent.setup()
  renderPublicRoute('/livros/trabalho-focado')
  await user.click(await screen.findByRole('link', { name: 'Ritual antes do foco' }))
  expect(await screen.findByRole('heading', { name: 'Ritual antes do foco' })).toBeInTheDocument()
})
```

Also assert every book shown has `publishedArticleCount > 0` and every article exposes only public metadata.

- [ ] **Step 2: Run discovery tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/public-site/public-discovery.test.tsx`

Expected: FAIL because list/detail data is still hard-coded or incomplete.

- [ ] **Step 3: Implement public list and detail projections**

Render books and articles from public services. Use slug-based public navigation exclusively; never leak `writingId` into links, DOM attributes, page source, or serialized state.

- [ ] **Step 4: Harden long-form reading presentation**

Keep article measure at or below `68ch`, preserve Markdown sanitization, and support long headings, quotes, code, Mermaid, and KaTeX without horizontal page overflow.

- [ ] **Step 5: Extend the privacy E2E workflow**

Add browser assertions:

```ts
await page.goto('/')
await page.getByRole('link', { name: /Explorar artigos de Trabalho focado/ }).click()
await page.getByRole('link', { name: 'Ritual antes do foco' }).click()
await expect(page.getByRole('heading', { name: 'Ritual antes do foco' })).toBeVisible()
await expect(page.locator('body')).not.toContainText(/prompt|transcrição|writing-/i)
```

- [ ] **Step 6: Verify public discovery unit tests**

Run: `npm --prefix frontend run test:unit -- src/public-site/public-discovery.test.tsx`

Expected: all public navigation and privacy tests pass.

- [ ] **Step 7: Commit public discovery flows**

```bash
git add frontend/src/public-site frontend/src/styles/prose.css frontend/tests/e2e/publish-flow.spec.ts
git commit -m "feat: complete public article discovery"
```

### Task 5: Replace separate message/audio types with a unified conversation model

**Files:**
- Modify: `frontend/src/services/contracts.ts`
- Modify: `frontend/src/services/mockApi.ts`
- Modify: `frontend/src/services/mock/fixtures.ts`
- Modify: `frontend/src/services/mock/handlers.ts`
- Create: `frontend/src/features/chat/conversationEvents.ts`
- Test: `frontend/src/features/chat/conversationEvents.test.ts`

**Interfaces:**
- Consumes: existing writing, audio, suggestion, and message contracts.
- Produces: discriminated `ConversationEvent`, `ConversationApi.list()`, `ConversationApi.sendText()`, `ConversationApi.sendLink()`, `ConversationApi.sendAudio()`, and stable chronological ordering.

- [ ] **Step 1: Write failing ordering, privacy, and idempotency tests**

```ts
it('orders text, audio, transcript and assistant events in one timeline', () => {
  expect(sortConversationEvents(events).map((event) => event.id)).toEqual([
    'text-01', 'audio-01', 'transcript-01', 'assistant-01',
  ])
})

it('deduplicates retried events by idempotency key', () => {
  expect(mergeConversationEvents(existing, retried)).toHaveLength(existing.length)
})
```

- [ ] **Step 2: Run conversation model tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/features/chat/conversationEvents.test.ts`

Expected: FAIL because the event union and merge functions do not exist.

- [ ] **Step 3: Define the discriminated event model**

```ts
interface EventBase { id: string; writingId: string; createdAt: string; status: 'pending' | 'ready' | 'failed' }

export type ConversationEvent =
  | (EventBase & { type: 'author_text'; content: string })
  | (EventBase & { type: 'author_link'; url: string; title?: string; summary?: string })
  | (EventBase & { type: 'author_audio'; title: string; durationSeconds?: number; localPreviewUrl?: string })
  | (EventBase & { type: 'transcript'; audioEventId: string; content: string })
  | (EventBase & { type: 'assistant_text'; content: string; partial: boolean })
  | (EventBase & { type: 'suggestion'; suggestionId: string; summary: string })
```

Use `exactOptionalPropertyTypes` correctly: omit absent optional keys instead of assigning `undefined`.

- [ ] **Step 4: Implement stable sort and deduplicating merge**

Sort by ISO timestamp, then event ID for deterministic ties. Merge by `id`, preferring the newest server representation while retaining a local audio preview only until the server provides a durable equivalent.

- [ ] **Step 5: Extend service contracts and mocks**

Replace workspace-level parallel `messages` and `audio` payload consumption with `conversation: ConversationEvent[]`. Keep old API members temporarily only if another tested route still consumes them; remove them in Task 6 after migration.

- [ ] **Step 6: Run model tests and typecheck**

Run: `npm --prefix frontend run test:unit -- src/features/chat/conversationEvents.test.ts src/services/api.test.ts && npm --prefix frontend run typecheck`

Expected: ordering, idempotency, API, and type checks pass.

- [ ] **Step 7: Commit the unified conversation contract**

```bash
git add frontend/src/services frontend/src/features/chat/conversationEvents.ts frontend/src/features/chat/conversationEvents.test.ts
git commit -m "refactor: unify writing conversation events"
```

### Task 6: Build the multimodal composer and chronological timeline

**Files:**
- Create: `frontend/src/features/chat/ConversationTimeline.tsx`
- Create: `frontend/src/features/chat/ConversationEventView.tsx`
- Create: `frontend/src/features/chat/MultimodalComposer.tsx`
- Create: `frontend/src/features/chat/AudioComposer.tsx`
- Create: `frontend/src/features/chat/LinkComposer.tsx`
- Modify: `frontend/src/features/chat/Chat.tsx`
- Modify: `frontend/src/features/chat/ChatProvider.tsx`
- Modify: `frontend/src/features/chat/chat.css`
- Modify: `frontend/src/features/audio/RecorderProvider.tsx`
- Test: `frontend/src/features/chat/multimodal-chat.test.tsx`

**Interfaces:**
- Consumes: `ConversationEvent` and conversation API from Task 5; existing recorder and streaming state machines.
- Produces: one `ConversationTimeline` and one `MultimodalComposer` supporting text, link, record, upload, retry, transcription state, and stop generation.

- [ ] **Step 1: Write failing multimodal workflow tests**

```tsx
it('adds text and audio to the same chronological conversation', async () => {
  const user = userEvent.setup()
  render(<ChatPanel stream={createDemoChatStream()} />)

  await user.type(screen.getByLabelText('Mensagem'), 'Conecte esta ideia ao capítulo.')
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
  await user.click(screen.getByRole('button', { name: 'Gravar áudio' }))

  const timeline = screen.getByRole('log', { name: 'Conversa sobre a escrita' })
  expect(within(timeline).getByText('Conecte esta ideia ao capítulo.')).toBeInTheDocument()
  expect(within(timeline).getByText(/Áudio/)).toBeInTheDocument()
})
```

Add tests for permission denial → upload fallback, failed upload → retry, transcription failure → reprocess, IME-safe Enter, duplicate-submit prevention, partial stream retention, and link validation.

- [ ] **Step 2: Run multimodal tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/features/chat/multimodal-chat.test.tsx`

Expected: FAIL because audio and text are still separate panels.

- [ ] **Step 3: Implement semantic event renderers**

Use a total switch over `event.type`. Audio, transcript, link, assistant, and suggestion renderers must have visible text labels, status text, accessible retry controls, and no color-only state.

- [ ] **Step 4: Compose one multimodal input surface**

`MultimodalComposer` owns the text field and toggles inline link/audio sub-composers. It exposes one stable footer; opening audio does not mount a new workspace panel. Keep `textarea` dimensions stable, `resize: none`, IME composition guards, and the existing stop-stream action.

- [ ] **Step 5: Adapt recorder behavior without duplicating state**

Reuse the recorder state machine through `AudioComposer`. Permission denial exposes the file input in the same composer. Create/revoke local object URLs in an effect cleanup; do not store blobs or object URLs in persistent storage.

- [ ] **Step 6: Implement independent pending operations**

Uploading/transcribing audio must not disable Markdown editing or text submission. Disable only the exact action that would duplicate the pending operation. Preserve failed local audio while the page remains open and expose `Tentar enviar novamente`.

- [ ] **Step 7: Run chat, audio, and multimodal tests**

Run: `npm --prefix frontend run test:unit -- src/features/chat/chat.test.tsx src/features/audio/audio.test.tsx src/features/chat/multimodal-chat.test.tsx`

Expected: all stream, recorder, and combined conversation tests pass.

- [ ] **Step 8: Commit the unified chat experience**

```bash
git add frontend/src/features/chat frontend/src/features/audio/RecorderProvider.tsx
git commit -m "feat: unify text links and audio in conversation"
```

### Task 7: Integrate the conversation into the writing workspace

**Files:**
- Modify: `frontend/src/features/workspace/WorkspacePage.tsx`
- Modify: `frontend/src/features/workspace/workspace.css`
- Modify: `frontend/src/features/workspace/workspace.test.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/tests/e2e/workspace-flow.spec.ts`
- Modify: `frontend/tests/e2e/workspace-failures.spec.ts`

**Interfaces:**
- Consumes: unified `ChatPanel`, existing `Workspace` compound components, editor/preview provider, and suggestion review.
- Produces: a workspace where the document remains primary and one contextual conversation contains every input modality.
- Visual target: `Documento soberano`, approved from the refined workspace exploration on 2026-08-28.

- [ ] **Step 1: Rewrite failing workspace composition tests**

```tsx
it('shows one conversation surface without a separate audio destination', async () => {
  renderWorkspace()
  expect(screen.getByRole('button', { name: 'Conversa' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Áudios' })).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Conversa' }))
  expect(screen.getByRole('button', { name: 'Gravar áudio' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run workspace tests to verify failure**

Run: `npm --prefix frontend run test:unit -- src/features/workspace/workspace.test.tsx src/app/App.test.tsx`

Expected: FAIL because the separate `Áudios` panel still exists.

- [ ] **Step 3: Remove the separate audio workspace destination**

Change `Panel` to `'document' | 'conversation' | 'suggestions'`. Render `ChatPanel` for conversation and keep suggestion review linked from its originating timeline event as well as the explicit review destination until the full suggestion flow is migrated.

- [ ] **Step 4: Implement collapsible contextual rails and focus mode**

Add independent `bookContextOpen` and `assistantOpen` state plus a `focusDocument()` action that closes both rails. With the assistant open, the document column owns 60–65% of usable width; when either rail closes, the document expands without remounting the editor or losing selection, scroll, Markdown, or autosave state. Controls expose `aria-expanded`, visible focus, localized accessible names, and restore focus when a temporary mobile surface closes.

- [ ] **Step 5: Preserve document-first responsive behavior**

Desktop keeps the sovereign document between a narrow active-book rail and the unified assistant. Mobile opens on the document, uses an accessible document/conversation switch, and exposes book context through a temporary app-owned surface. Do not hide private navigation without an accessible replacement below 780 px. Audio remains inside the conversation composer at every viewport.

- [ ] **Step 6: Update E2E success and recovery workflows**

The success flow must submit text, add audio, observe both in one timeline, collapse and reopen the assistant without losing document state, enter focus mode, open a suggestion, accept it once, and confirm a new document version. The failure flow must stop an assistant response and retry audio without disabling the editor.

- [ ] **Step 7: Run workspace and application tests**

Run: `npm --prefix frontend run test:unit -- src/features/workspace/workspace.test.tsx src/app/App.test.tsx src/features/chat/multimodal-chat.test.tsx`

Expected: all workspace composition tests pass.

- [ ] **Step 8: Commit workspace integration**

```bash
git add frontend/src/features/workspace frontend/src/app/App.test.tsx frontend/tests/e2e
git commit -m "feat: integrate multimodal writing workspace"
```

### Task 8: Enforce visual, accessibility, privacy, and performance gates

**Files:**
- Modify: `UX-CONTRACT.md`
- Modify: `premium-ui.json`
- Modify: `frontend/src/test/accessibility.test.tsx`
- Modify: `frontend/tests/e2e/accessibility.spec.ts`
- Modify: `frontend/tests/e2e/visual.spec.ts`
- Modify: `frontend/scripts/check-anti-patterns.mjs`
- Modify: `frontend/scripts/check-bundles.mjs`

**Interfaces:**
- Consumes: every completed public and workspace flow from Tasks 1–7.
- Produces: updated behavioral contract and release evidence for the approved feature set.

- [ ] **Step 1: Update the canonical behavior ledger**

Record public featured-article fallback, public-book eligibility, landing failure recovery, multimodal message operations, audio retry, and unified conversation scroll ownership in `UX-CONTRACT.md`. Reference the approved spec rather than duplicating business policy.

- [ ] **Step 2: Extend automated accessibility coverage**

Cover `/`, `/artigos`, `/livros`, one public book, one article, and the workspace conversation open state at desktop and mobile. Assert landmarks, heading hierarchy, accessible names, dialog focus, live statuses, and no serious axe violations.

- [ ] **Step 3: Add visual baselines for approved representative states**

Capture landing desktop/mobile, landing without covers, published-book detail, workspace with mixed conversation events, permission-denied audio fallback, and reduced-motion mode. Store baselines through Playwright’s snapshot mechanism.

- [ ] **Step 4: Strengthen static privacy and composition gates**

Fail when public-site files import private chat/audio/suggestion modules, when native dialogs appear, when separate workspace audio navigation returns, or when public links contain internal writing IDs.

- [ ] **Step 5: Run the complete verification matrix**

Run:

```bash
python3 /home/victormrtns/.codex/plugins/cache/openai-curated-remote/frontend-design-premium/1.4.0/skills/frontend-design-premium/scripts/audit_project.py /home/victormrtns/books-blog-ai --mode strict
npx -p @google/design.md designmd lint DESIGN.md
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test:unit
npm --prefix frontend run test:a11y
npm --prefix frontend run build
npm --prefix frontend run verify:premium
npm --prefix frontend run verify:bundles
npm --prefix frontend run test:e2e
```

Expected: every command exits 0; ESLint has no errors; Vitest has zero failures; Playwright passes desktop and mobile. If Chromium system libraries remain absent, report the environmental block without claiming E2E completion.

- [ ] **Step 6: Manually inspect production behavior**

Verify loading, empty, partial error, total error, long content, missing covers, keyboard, 320 px, 200% zoom, reduced motion, audio permission denial, upload retry, transcription retry, interrupted streaming, and public privacy in a real browser.

- [ ] **Step 7: Commit the release gates**

```bash
git add UX-CONTRACT.md premium-ui.json frontend/src/test frontend/tests/e2e frontend/scripts
git commit -m "test: enforce public and multimodal experience gates"
```
