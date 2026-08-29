import type { AppApi, AudioClip, Book, LimitState, Message, PublicationStatus, Suggestion, UsageSummary, Writing } from '@/services/contracts'
import { publicArticleFixtures, publicBookFixtures, publicLandingFixture } from '@/services/mock/fixtures'

const writing: Writing = { id: 'writing-deep-work-01', bookId: 'book-deep-work', title: 'Ritual antes do foco', markdown: '# Ritual antes do foco', sourceRange: 'Capítulos 3–4', status: 'draft', version: 4, updatedAt: '2026-08-28T10:21:00-03:00' }
const messages: Message[] = [{ id: 'message-01', writingId: writing.id, role: 'author', content: 'Organize esta ideia.', createdAt: writing.updatedAt }, { id: 'message-02', writingId: writing.id, role: 'assistant', content: 'Preparei uma sugestão.', createdAt: writing.updatedAt }]
const audio: AudioClip[] = [{ id: 'audio-01', writingId: writing.id, title: 'Ideia sobre o ritual', status: 'ready', durationSeconds: 214 }]
const suggestions: Suggestion[] = [{ id: 'suggestion-01', writingId: writing.id, summary: 'Uma explicação mais linear', before: 'O foco começa.', after: 'O foco começa antes do trabalho.', status: 'pending' }]
const books: Book[] = [{ id: 'book-deep-work', title: 'Trabalho focado', author: 'Cal Newport', writingCount: 3 }]

const usageValues: Record<LimitState, UsageSummary> = {
  normal: { period: '2026-08', audioMinutes: 42, estimatedAiCostBrl: 12.4, monthlyLimitBrl: 70, limitState: 'normal' },
  near_limit: { period: '2026-08', audioMinutes: 188, estimatedAiCostBrl: 58, monthlyLimitBrl: 70, limitState: 'near_limit' },
  blocked: { period: '2026-08', audioMinutes: 240, estimatedAiCostBrl: 70, monthlyLimitBrl: 70, limitState: 'blocked' },
}

const publicationStatus: PublicationStatus = {
  slug: 'ritual-antes-do-foco',
  state: 'published',
  publishedAt: '2026-08-28T10:21:00-03:00',
  cleanupAt: '2026-08-31T10:21:00-03:00',
  cleanupCancelledAt: null,
  cleanupCompletedAt: null,
}

export function createMockApi(options: { usage?: LimitState } = {}): AppApi {
  let currentWriting = { ...writing }
  const currentBooks = books.map((book) => ({ ...book }))
  return {
    auth: {
      async getSession() { return { state: 'author', author: { email: 'autor@example.com' } } },
      async signIn() { return { state: 'author', author: { email: 'autor@example.com' } } },
      async signOut() { return undefined },
    },
    books: {
      async list() { return currentBooks.map((book) => ({ ...book })) },
      async create(input) { const book = { id: `book-${currentBooks.length + 1}`, ...input, writingCount: 0 }; currentBooks.push(book); return { ...book } },
    },
    writings: {
      async getWorkspace(id) { if (id !== currentWriting.id) throw new Error('Escrita não encontrada.'); return { writing: { ...currentWriting }, messages: messages.map((item) => ({ ...item })), audio: audio.map((item) => ({ ...item })), suggestions: suggestions.map((item) => ({ ...item })) } },
      async save(input) { if (input.id !== currentWriting.id) throw new Error('Escrita não encontrada.'); if (input.expectedVersion !== currentWriting.version) throw new Error('Conflito de versão.'); currentWriting = { ...currentWriting, markdown: input.markdown, version: currentWriting.version + 1 }; return { ...currentWriting } },
    },
    chat: { async list(writingId) { return messages.filter((item) => item.writingId === writingId).map((item) => ({ ...item })) } },
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
    },
  }
}
