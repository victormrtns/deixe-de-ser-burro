import type { ApiErrorShape, AppApi, ChatStreamEvent, ChatStreamListener, Message } from '@/services/contracts'
import { createMockApi } from '@/services/mockApi'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: Record<string, unknown>
  readonly requestId: string

  constructor(status: number, shape: ApiErrorShape) {
    super(shape.message)
    this.name = 'ApiError'
    this.status = status
    this.code = shape.code
    if (shape.details !== undefined) this.details = shape.details
    this.requestId = shape.requestId
  }
}

type RequestOptions = { method?: string; body?: unknown; idempotencyKey?: string }

const FALLBACK_ERROR: ApiErrorShape = {
  code: 'internal_error',
  message: 'Falha na requisição.',
  requestId: '',
}

function absoluteUrl(path: string): string {
  return typeof window === 'undefined' ? path : new URL(path, window.location.origin).toString()
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['content-type'] = 'application/json'
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey

  const response = await fetch(absoluteUrl(path), {
    method: options.method ?? 'GET',
    credentials: 'include',
    headers,
    ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
  })
  if (response.status === 204) return undefined as T

  if (!response.ok) throw await apiErrorFrom(response)
  return (await response.json().catch(() => null)) as T
}

async function apiErrorFrom(response: Response): Promise<ApiError> {
  const payload: unknown = await response.json().catch(() => null)
  const shape = (payload as { error?: ApiErrorShape } | null)?.error ?? FALLBACK_ERROR
  if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new Event('entrelinhas:session-expired'))
  return new ApiError(response.status, shape)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

// Valida o payload de eventos conhecidos na versão 1; nomes ou versões
// desconhecidas devolvem null e são ignorados sem corromper a conversa.
function toStreamEvent(name: string, raw: string): ChatStreamEvent | null {
  let payload: unknown
  try { payload = JSON.parse(raw) } catch { return null }
  if (!isRecord(payload) || payload.version !== 1) return null
  const { attemptId, sequence } = payload
  if (typeof attemptId !== 'string' || typeof sequence !== 'number') return null
  const head = { version: 1, attemptId, sequence } as const
  switch (name) {
    case 'generation.started':
      return typeof payload.messageId === 'string' && typeof payload.attemptNumber === 'number' ? { type: name, ...head, messageId: payload.messageId, attemptNumber: payload.attemptNumber } : null
    case 'response.delta':
      return typeof payload.delta === 'string' ? { type: name, ...head, delta: payload.delta } : null
    case 'response.completed': {
      const usage = payload.usage
      if (!isRecord(usage) || typeof usage.totalTokens !== 'number' || typeof usage.estimatedCostUsdMicros !== 'number') return null
      return { type: name, ...head, usage: { inputTokens: Number(usage.inputTokens ?? 0), outputTokens: Number(usage.outputTokens ?? 0), totalTokens: usage.totalTokens, estimatedCostUsdMicros: usage.estimatedCostUsdMicros, budgetState: usage.budgetState === 'near_limit' || usage.budgetState === 'blocked' ? usage.budgetState : 'normal' } }
    }
    case 'response.interrupted':
      return { type: name, ...head }
    case 'response.failed': {
      const error = payload.error
      if (!isRecord(error) || typeof error.code !== 'string' || typeof error.message !== 'string') return null
      return { type: name, ...head, error: { code: error.code, message: error.message, requestId: typeof error.requestId === 'string' ? error.requestId : '' } }
    }
    default:
      return null
  }
}

function parseFrame(frame: string): ChatStreamEvent | null {
  let name = ''
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator < 0 ? line : line.slice(0, separator)
    const value = separator < 0 ? '' : line.slice(separator + 1).replace(/^ /, '')
    if (field === 'event') name = value
    else if (field === 'data') data.push(value)
  }
  return name && data.length > 0 ? toStreamEvent(name, data.join('\n')) : null
}

// Lê o corpo incrementalmente: decodifica UTF-8 em fluxo e só entrega quadros
// completos. Nada do conteúdo é registrado em log.
async function streamEvents(path: string, options: { body?: unknown; idempotencyKey: string; signal: AbortSignal }, onEvent: ChatStreamListener): Promise<void> {
  const headers: Record<string, string> = { accept: 'text/event-stream', 'Idempotency-Key': options.idempotencyKey }
  if (options.body !== undefined) headers['content-type'] = 'application/json'
  const response = await fetch(absoluteUrl(path), { method: 'POST', credentials: 'include', headers, signal: options.signal, ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}) })
  if (!response.ok) throw await apiErrorFrom(response)
  const body = response.body
  if (!body) throw new ApiError(response.status, { code: 'ai_unavailable', message: 'A resposta do assistente não pôde ser lida.', requestId: '' })

  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    buffer += done ? decoder.decode() : decoder.decode(value, { stream: true }).replace(/\r/g, '')
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const event = parseFrame(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      if (event) onEvent(event)
      boundary = buffer.indexOf('\n\n')
    }
    if (done) break
  }
}

// Audio and suggestions have no backend yet: they stay on the mock adapter
// explicitly instead of hitting endpoints that do not exist.
const deferredToMock = createMockApi()

export const httpApi: AppApi = {
  auth: {
    getSession: () => request('/api/auth/session'),
    signIn: (email, password) =>
      request('/api/auth/session', { method: 'POST', body: { email, password } }),
    signOut: () => request('/api/auth/session', { method: 'DELETE' }),
  },
  books: {
    list: () => request('/api/books'),
    create: (input, idempotencyKey) =>
      request('/api/books', { method: 'POST', body: input, ...(idempotencyKey ? { idempotencyKey } : {}) }),
    get: (id) => request(`/api/books/${id}`),
    update: (id, input) => request(`/api/books/${id}`, { method: 'PATCH', body: input }),
    remove: (id) => request(`/api/books/${id}`, { method: 'DELETE' }),
  },
  writings: {
    create: (bookId, input, idempotencyKey) =>
      request(`/api/books/${bookId}/writings`, {
        method: 'POST',
        body: input,
        ...(idempotencyKey ? { idempotencyKey } : {}),
      }),
    listByBook: (bookId) => request(`/api/books/${bookId}/writings`),
    get: (id) => request(`/api/writings/${id}`),
    getWorkspace: (id) => request(`/api/writings/${id}/workspace`),
    save: ({ id, markdown, expectedVersion }) =>
      request(`/api/writings/${id}`, { method: 'PUT', body: { markdown, expectedVersion } }),
    updateMetadata: ({ id, ...changes }) =>
      request(`/api/writings/${id}`, { method: 'PATCH', body: changes }),
    remove: (id) => request(`/api/writings/${id}`, { method: 'DELETE' }),
    listVersions: (id, cursor) =>
      request(`/api/writings/${id}/versions${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`),
    restoreVersion: ({ id, versionNumber, expectedVersion }) =>
      request(`/api/writings/${id}/versions/${versionNumber}/restore`, {
        method: 'POST',
        body: { expectedVersion },
      }),
  },
  publishing: {
    publish: (writingId, idempotencyKey) =>
      request(`/api/writings/${writingId}/publication`, {
        method: 'POST',
        ...(idempotencyKey ? { idempotencyKey } : {}),
      }),
    getStatus: (writingId) => request(`/api/writings/${writingId}/publication`),
    cancelCleanup: (writingId) =>
      request(`/api/writings/${writingId}/publication/cancel-cleanup`, { method: 'POST' }),
    unpublish: (writingId) =>
      request(`/api/writings/${writingId}/publication`, { method: 'DELETE' }),
  },
  public: {
    getLanding: () => request('/api/public/landing'),
    listArticles: () => request('/api/public/articles'),
    getArticle: (slug) => request(`/api/public/articles/${slug}`),
    listBooks: () => request('/api/public/books'),
    getBook: (slug) => request(`/api/public/books/${slug}`),
  },
  chat: {
    list: async (writingId) => (await request<{ messages: Message[] }>(`/api/writings/${writingId}/conversation`)).messages,
    streamReply: (writingId, content, idempotencyKey, signal, onEvent) =>
      streamEvents(`/api/writings/${writingId}/conversation/messages`, { body: { content }, idempotencyKey, signal }, onEvent),
    retry: (writingId, messageId, idempotencyKey, signal, onEvent) =>
      streamEvents(`/api/writings/${writingId}/conversation/messages/${messageId}/retry`, { idempotencyKey, signal }, onEvent),
    remember: (writingId, input) => request(`/api/writings/${writingId}/memory`, { method: 'POST', body: input }),
    getUsage: (writingId) => request(`/api/writings/${writingId}/usage`),
  },
  audio: deferredToMock.audio,
  suggestions: deferredToMock.suggestions,
  usage: deferredToMock.usage,
}
