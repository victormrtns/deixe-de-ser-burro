import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, it } from 'vitest'
import { ApiError, httpApi } from '@/services/httpApi'
import { workspaceFixture } from '@/services/mock/fixtures'

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

it('envia cookies e somente markdown com expectedVersion no autosave', async () => {
  server.use(
    http.put('/api/writings/w1', async ({ request }) => {
      expect(request.credentials).toBe('include')
      expect(await request.json()).toEqual({ markdown: '# Salvo', expectedVersion: 4 })
      return HttpResponse.json(workspaceFixture.writing)
    }),
  )

  const saved = await httpApi.writings.save({ id: 'w1', markdown: '# Salvo', expectedVersion: 4 })

  expect(saved.id).toBe(workspaceFixture.writing.id)
})

it('converte o envelope de erro do backend em ApiError', async () => {
  server.use(
    http.put('/api/writings/w1', () =>
      HttpResponse.json(
        {
          error: {
            code: 'writing_version_conflict',
            message: 'A escrita foi alterada em outra sessão.',
            details: { currentVersion: 5 },
            requestId: 'req-123',
          },
        },
        { status: 409 },
      ),
    ),
  )

  const failure = await httpApi.writings
    .save({ id: 'w1', markdown: '# Salvo', expectedVersion: 4 })
    .catch((error: unknown) => error)

  expect(failure).toBeInstanceOf(ApiError)
  const apiError = failure as ApiError
  expect(apiError.status).toBe(409)
  expect(apiError.code).toBe('writing_version_conflict')
  expect(apiError.details).toEqual({ currentVersion: 5 })
  expect(apiError.requestId).toBe('req-123')
})

it('publica com o cabeçalho Idempotency-Key', async () => {
  server.use(
    http.post('/api/writings/w1/publication', ({ request }) => {
      expect(request.headers.get('Idempotency-Key')).toBe('publish-1')
      return HttpResponse.json(
        {
          slug: 'ritual-antes-do-foco',
          publishedAt: '2026-08-28T10:21:00-03:00',
          cleanupAt: '2026-08-31T10:21:00-03:00',
        },
        { status: 201 },
      )
    }),
  )

  const published = await httpApi.publishing.publish('w1', 'publish-1')

  expect(published.slug).toBe('ritual-antes-do-foco')
  expect(published.cleanupAt).toBe('2026-08-31T10:21:00-03:00')
})

it('cria livros com chave idempotente e corpo JSON', async () => {
  server.use(
    http.post('/api/books', async ({ request }) => {
      expect(request.headers.get('Idempotency-Key')).toBe('book-1')
      expect(request.headers.get('content-type')).toBe('application/json')
      expect(await request.json()).toEqual({ title: 'Duna', author: 'Frank Herbert' })
      return HttpResponse.json(
        { id: 'b1', title: 'Duna', author: 'Frank Herbert', coverUrl: null, writingCount: 0 },
        { status: 201 },
      )
    }),
  )

  const created = await httpApi.books.create({ title: 'Duna', author: 'Frank Herbert' }, 'book-1')

  expect(created.id).toBe('b1')
})

it('autentica a sessão e encerra com 204 sem corpo', async () => {
  server.use(
    http.post('/api/auth/session', async ({ request }) => {
      expect(await request.json()).toEqual({ email: 'autor@example.com', password: 'segredo' })
      return HttpResponse.json({ state: 'author', author: { email: 'autor@example.com' } })
    }),
    http.delete('/api/auth/session', () => new HttpResponse(null, { status: 204 })),
  )

  const session = await httpApi.auth.signIn('autor@example.com', 'segredo')
  await httpApi.auth.signOut()

  expect(session).toEqual({ state: 'author', author: { email: 'autor@example.com' } })
})

it('lê projeções públicas sem exigir autenticação', async () => {
  server.use(
    http.get('/api/public/articles/ritual-antes-do-foco', () =>
      HttpResponse.json({
        slug: 'ritual-antes-do-foco',
        title: 'Ritual antes do foco',
        excerpt: 'Sobre ambiente e intenção.',
        publishedAt: '2026-08-24T09:00:00-03:00',
        readingMinutes: 8,
        coverImageUrl: null,
        markdown: '# Ritual antes do foco',
        sourceBook: { slug: 'trabalho-focado', title: 'Trabalho focado', author: 'Cal Newport' },
      }),
    ),
  )

  const article = await httpApi.public.getArticle('ritual-antes-do-foco')

  expect(article.markdown).toBe('# Ritual antes do foco')
})
