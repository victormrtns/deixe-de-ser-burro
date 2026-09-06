import type { AppApi, AudioClip, Book, LimitState, Message, PublicationStatus, Suggestion, UsageSummary, Writing, WritingVersion } from '@/services/contracts'
import { publicArticleFixtures, publicBookFixtures, publicLandingFixture } from '@/services/mock/fixtures'

const writing: Writing = { id: 'writing-deep-work-01', bookId: 'book-deep-work', title: 'Ritual antes do foco', markdown: '# Ritual antes do foco', sourceRange: 'Capítulos 3–4', status: 'draft', version: 4, updatedAt: '2026-08-28T10:21:00-03:00' }
const messages: Message[] = [{ id: 'message-01', writingId: writing.id, role: 'author', content: 'Organize esta ideia.', state: 'completed', createdAt: writing.updatedAt }, { id: 'message-02', writingId: writing.id, role: 'assistant', content: 'Preparei uma sugestão.', state: 'completed', createdAt: writing.updatedAt }]
const audio: AudioClip[] = [{ id: 'audio-01', writingId: writing.id, title: 'Ideia sobre o ritual', status: 'ready', durationSeconds: 214 }]
const suggestions: Suggestion[] = [{ id: 'suggestion-01', writingId: writing.id, summary: 'Uma explicação mais linear', before: 'O foco começa.', after: 'O foco começa antes do trabalho.', status: 'pending' }]
const books: Book[] = [{ id: 'book-deep-work', title: 'Trabalho focado', author: 'Cal Newport', writingCount: 3 }]

const usageValues: Record<LimitState, UsageSummary> = {
  normal: { period: '2026-08', spentUsdMicros: 120_000, reservedUsdMicros: 0, limitUsdMicros: 2_000_000, limitState: 'normal' },
  near_limit: { period: '2026-08', spentUsdMicros: 1_700_000, reservedUsdMicros: 40_000, limitUsdMicros: 2_000_000, limitState: 'near_limit' },
  blocked: { period: '2026-08', spentUsdMicros: 2_000_000, reservedUsdMicros: 0, limitUsdMicros: 2_000_000, limitState: 'blocked' },
}

const publicationStatus: PublicationStatus = {
  slug: 'ritual-antes-do-foco',
  state: 'published',
  publishedAt: '2026-08-28T10:21:00-03:00',
  cleanupAt: '2026-08-31T10:21:00-03:00',
  cleanupCancelledAt: null,
  cleanupCompletedAt: null,
}

export function createMockApi(options: { usage?: LimitState; session?: 'anonymous' | 'author' } = {}): AppApi {
  let currentWriting = { ...writing }
  const currentWritings = [currentWriting]
  let currentSession: 'anonymous' | 'author' = options.session ?? 'author'
  const currentBooks = books.map((book) => ({ ...book }))
  return {
    auth: {
      async getSession() { return currentSession === 'author' ? { state: 'author', author: { email: 'autor@example.com' } } : { state: 'anonymous' } },
      async signIn() { currentSession = 'author'; return { state: 'author', author: { email: 'autor@example.com' } } },
      async signOut() { currentSession = 'anonymous' },
    },
    books: {
      async list() { return currentBooks.map((book) => ({ ...book })) },
      async create(input) { const book = { id: `book-${currentBooks.length + 1}`, ...input, writingCount: 0 }; currentBooks.push(book); return { ...book } },
      async get(id) { const book = currentBooks.find((item) => item.id === id); if (!book) throw new Error('Livro não encontrado.'); return { ...book } },
      async update(id, input) { const index = currentBooks.findIndex((item) => item.id === id); if (index < 0) throw new Error('Livro não encontrado.'); currentBooks[index] = { ...currentBooks[index]!, ...input }; return { ...currentBooks[index]! } },
      async remove(id) { const index = currentBooks.findIndex((item) => item.id === id); if (index >= 0) currentBooks.splice(index, 1) },
    },
    writings: {
      async create(bookId, input) { const created: Writing = { id: `writing-${currentWritings.length + 1}`, bookId, title: input.title, sourceRange: input.sourceRange, markdown: input.markdown ?? `# ${input.title}`, status: 'draft', version: 1, updatedAt: new Date().toISOString() }; currentWritings.push(created); currentWriting = created; return { ...created } },
      async listByBook(bookId) { return currentWritings.filter((item) => item.bookId === bookId).map((item) => ({ ...item })) },
      async get(id) { const found = currentWritings.find((item) => item.id === id); if (!found) throw new Error('Escrita não encontrada.'); return { ...found } },
      async getWorkspace(id) { const found = currentWritings.find((item) => item.id === id); if (!found) throw new Error('Escrita não encontrada.'); currentWriting = found; return { writing: { ...found }, messages: messages.map((item) => ({ ...item })), audio: audio.map((item) => ({ ...item })), suggestions: suggestions.map((item) => ({ ...item })) } },
      async save(input) { if (input.id !== currentWriting.id) throw new Error('Escrita não encontrada.'); if (input.expectedVersion !== currentWriting.version) throw new Error('Conflito de versão.'); currentWriting = { ...currentWriting, markdown: input.markdown, version: currentWriting.version + 1 }; const index = currentWritings.findIndex((item) => item.id === input.id); if (index >= 0) currentWritings[index] = currentWriting; return { ...currentWriting } },
      async updateMetadata(input) { const found = currentWritings.find((item) => item.id === input.id); if (!found) throw new Error('Escrita não encontrada.'); Object.assign(found, input, { version: found.version + 1 }); return { ...found } },
      async remove(id) { const index = currentWritings.findIndex((item) => item.id === id); if (index >= 0) currentWritings.splice(index, 1) },
      async listVersions(id) { const found = currentWritings.find((item) => item.id === id); const item: WritingVersion = { version: found?.version ?? 1, title: found?.title ?? '', sourceRange: found?.sourceRange ?? '', markdown: found?.markdown ?? '', reason: 'manual_save', createdAt: found?.updatedAt ?? new Date().toISOString() }; return { items: [item], nextCursor: null } },
      async restoreVersion({ id }) { const found = currentWritings.find((item) => item.id === id); if (!found) throw new Error('Escrita não encontrada.'); found.version += 1; return { ...found } },
    },
    chat: {
      async list(writingId) { return messages.filter((item) => item.writingId === writingId).map((item) => ({ ...item })) },
      async streamReply() { throw new Error('O assistente não está disponível no adaptador de demonstração.') },
      async retry() { throw new Error('O assistente não está disponível no adaptador de demonstração.') },
      async remember(_writingId, input) { return { id: `memory-${Date.now()}`, kind: input.kind, content: input.content, createdAt: new Date().toISOString() } },
      async getUsage() { return { ...usageValues[options.usage ?? 'normal'] } },
    },
    audio: { async list(writingId) { return audio.filter((item) => item.writingId === writingId).map((item) => ({ ...item })) } },
    suggestions: { async list(writingId) { return suggestions.filter((item) => item.writingId === writingId).map((item) => ({ ...item })) } },
    publishing: {
      async publish() { return { slug: publicationStatus.slug, publishedAt: publicationStatus.publishedAt, cleanupAt: publicationStatus.cleanupAt } },
      async getStatus() { return { ...publicationStatus } },
      async cancelCleanup() { return { ...publicationStatus, cleanupCancelledAt: '2026-08-28T11:00:00-03:00' } },
      async unpublish() { return { ...publicationStatus, state: 'withdrawn' as const } },
    },
    usage: { async getSummary() { return { ...usageValues[options.usage ?? 'normal'] } } },
    public: {
      async getLanding() { return structuredClone(publicLandingFixture) },
      async listArticles() { return structuredClone(publicArticleFixtures) },
      async listBooks() { return structuredClone(publicBookFixtures) },
      async getArticle(slug) { const found = publicArticleFixtures.find((item) => item.slug === slug); if (!found) throw new Error('Artigo não encontrado.'); return { ...structuredClone(found), markdown: `# ${found.title}\n\n${found.excerpt}` } },
      async getBook(slug) { const found = publicBookFixtures.find((item) => item.slug === slug); if (!found) throw new Error('Livro não encontrado.'); return { ...structuredClone(found), articles: publicArticleFixtures.filter((item) => item.sourceBook.slug === slug) } },
    },
  }
}
