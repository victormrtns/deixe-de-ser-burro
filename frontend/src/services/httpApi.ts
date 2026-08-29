import type { ApiErrorShape, HttpAppApi } from '@/services/contracts'
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

  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const shape = (payload as { error?: ApiErrorShape } | null)?.error ?? FALLBACK_ERROR
    throw new ApiError(response.status, shape)
  }
  return payload as T
}

// Chat, audio, suggestions, and usage have no backend yet: they stay on the
// mock adapter explicitly instead of hitting endpoints that do not exist.
const deferredToMock = createMockApi()

export const httpApi: HttpAppApi = {
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
  chat: deferredToMock.chat,
  audio: deferredToMock.audio,
  suggestions: deferredToMock.suggestions,
  usage: deferredToMock.usage,
}
