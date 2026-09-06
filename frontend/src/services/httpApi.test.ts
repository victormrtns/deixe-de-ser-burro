import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, it, vi } from 'vitest'
import { ApiError, httpApi } from '@/services/httpApi'
import type { ChatStreamEvent } from '@/services/contracts'
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

const encoder = new TextEncoder()

// Fatia o corpo em pedaços de tamanho arbitrário: quebra quadros ao meio e
// também caracteres UTF-8 de vários bytes.
function sseStream(body: string, chunkSize: number) {
  const bytes = encoder.encode(body)
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (let offset = 0; offset < bytes.length; offset += chunkSize) controller.enqueue(bytes.slice(offset, offset + chunkSize))
      controller.close()
    },
  })
}

const streamBody = [
  ': keep-alive\n\n',
  'event: generation.started\ndata: {"version":1,"attemptId":"a1","sequence":0,"messageId":"assistant-1","attemptNumber":1}\n\n',
  'event: response.delta\ndata: {"version":1,"attemptId":"a1","sequence":1,"delta":"A atenção começa "}\n\n',
  'event: response.delta\ndata: {"version":2,"attemptId":"a1","sequence":2,"delta":"versão desconhecida"}\n\n',
  'event: response.branched\ndata: {"version":1,"attemptId":"a1","sequence":3}\n\n',
  'event: response.delta\ndata: {"version":1,"attemptId":"a1","sequence":4}\n\n',
  'event: response.delta\ndata: {"version":1,"attemptId":"a1","sequence":5,"delta":"antes do trabalho 🌱"}\n\n',
  'event: response.completed\ndata: {"version":1,"attemptId":"a1","sequence":6,"usage":{"inputTokens":120,"outputTokens":80,"totalTokens":200,"estimatedCostUsdMicros":1400,"budgetState":"near_limit"}}\n\n',
].join('')

it('lê o streaming em quadros completos ignorando comentários, versões e eventos desconhecidos', async () => {
  server.use(
    http.post('/api/writings/w1/conversation/messages', async ({ request }) => {
      expect(request.headers.get('Idempotency-Key')).toBe('intent-1')
      expect(await request.json()).toEqual({ content: 'Organize esta ideia.' })
      return new HttpResponse(sseStream(streamBody, 5), { headers: { 'content-type': 'text/event-stream' } })
    }),
  )

  const events: ChatStreamEvent[] = []
  await httpApi.chat.streamReply('w1', 'Organize esta ideia.', 'intent-1', new AbortController().signal, (event) => events.push(event))

  expect(events.map((event) => event.type)).toEqual(['generation.started', 'response.delta', 'response.delta', 'response.completed'])
  expect(events.filter((event) => event.type === 'response.delta').map((event) => event.delta).join('')).toBe('A atenção começa antes do trabalho 🌱')
  expect(events[0]).toMatchObject({ messageId: 'assistant-1', attemptNumber: 1 })
  expect(events[3]).toMatchObject({ usage: { totalTokens: 200, estimatedCostUsdMicros: 1400, budgetState: 'near_limit' } })
})

it('entrega o retry manual no endpoint da mensagem sem corpo e com nova chave', async () => {
  server.use(
    http.post('/api/writings/w1/conversation/messages/author-1/retry', ({ request }) => {
      expect(request.headers.get('Idempotency-Key')).toBe('retry-1')
      return new HttpResponse(sseStream('event: response.interrupted\ndata: {"version":1,"attemptId":"a2","sequence":9}\n\n', 3), { headers: { 'content-type': 'text/event-stream' } })
    }),
  )

  const events: ChatStreamEvent[] = []
  await httpApi.chat.retry('w1', 'author-1', 'retry-1', new AbortController().signal, (event) => events.push(event))

  expect(events).toEqual([{ type: 'response.interrupted', version: 1, attemptId: 'a2', sequence: 9 }])
})

it('propaga o envelope de erro anterior ao streaming como ApiError', async () => {
  server.use(
    http.post('/api/writings/w1/conversation/messages', () =>
      HttpResponse.json({ error: { code: 'context_too_large', message: 'O texto atual excede o limite de contexto.', requestId: 'req-7' } }, { status: 422 }),
    ),
  )

  const failure = await httpApi.chat
    .streamReply('w1', 'Organize esta ideia.', 'intent-2', new AbortController().signal, () => {})
    .catch((error: unknown) => error)

  expect(failure).toBeInstanceOf(ApiError)
  expect((failure as ApiError).code).toBe('context_too_large')
  expect((failure as ApiError).status).toBe(422)
})

it('avisa a expiração de sessão quando o streaming responde 401', async () => {
  server.use(
    http.post('/api/writings/w1/conversation/messages', () =>
      HttpResponse.json({ error: { code: 'authentication_required', message: 'Sua sessão expirou.', requestId: 'req-8' } }, { status: 401 }),
    ),
  )
  const expired = vi.fn()
  window.addEventListener('entrelinhas:session-expired', expired)

  await httpApi.chat.streamReply('w1', 'Organize esta ideia.', 'intent-3', new AbortController().signal, () => {}).catch(() => undefined)
  window.removeEventListener('entrelinhas:session-expired', expired)

  expect(expired).toHaveBeenCalledTimes(1)
})

it('lê a conversa persistida e registra memória explícita', async () => {
  server.use(
    http.get('/api/writings/w1/conversation', () => HttpResponse.json({ messages: [{ id: 'author-1', writingId: 'w1', role: 'author', content: 'Organize esta ideia.', state: 'completed', createdAt: '2026-09-05T10:00:00-03:00' }] })),
    http.post('/api/writings/w1/memory', async ({ request }) => {
      expect(await request.json()).toEqual({ kind: 'decision', content: 'Manter o tom seco.', sourceMessageId: 'assistant-1' })
      return HttpResponse.json({ id: 'memory-1', kind: 'decision', content: 'Manter o tom seco.', createdAt: '2026-09-05T10:02:00-03:00' }, { status: 201 })
    }),
  )

  expect(await httpApi.chat.list('w1')).toHaveLength(1)
  expect(await httpApi.chat.remember('w1', { kind: 'decision', content: 'Manter o tom seco.', sourceMessageId: 'assistant-1' })).toMatchObject({ id: 'memory-1' })
})
