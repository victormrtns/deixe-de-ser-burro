import { expect, it } from 'vitest'
import { createMockApi } from '@/services/mockApi'

it('mantém todos os artefatos de trabalho dentro de uma escrita', async () => {
  const api = createMockApi()
  const result = await api.writings.getWorkspace('writing-deep-work-01')

  expect(result.writing.bookId).toBe('book-deep-work')
  expect(result.messages.every((item) => item.writingId === result.writing.id)).toBe(true)
  expect(result.audio.every((item) => item.writingId === result.writing.id)).toBe(true)
  expect(result.suggestions.every((item) => item.writingId === result.writing.id)).toBe(true)
})

it('expõe estados de orçamento sem bloquear edição manual', async () => {
  const api = createMockApi({ usage: 'blocked' })
  const usage = await api.usage.getSummary()

  expect(usage.limitState).toBe('blocked')
  expect(usage.estimatedAiCostBrl).toBe(70)
  expect(await api.writings.save({ id: 'writing-deep-work-01', markdown: '# Ainda editável', expectedVersion: 4 })).toMatchObject({ markdown: '# Ainda editável' })
})

it('retorna somente projeções públicas na landing', async () => {
  const landing = await createMockApi().public.getLanding()

  expect(landing.featuredArticle?.slug).toBe('ritual-antes-do-foco')
  expect(landing.publishedBooks).toHaveLength(2)
  expect(JSON.stringify(landing)).not.toMatch(/markdown|writingId|messages|audio|suggestions/)
})

it('omite livros que ainda não possuem artigos publicados', async () => {
  const landing = await createMockApi().public.getLanding()

  expect(landing.publishedBooks.map((book) => book.slug)).not.toContain('livro-sem-publicacao')
  expect(landing.publishedBooks.every((book) => book.publishedArticleCount > 0)).toBe(true)
})
