import type { AppApi } from '@/services/contracts'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) throw new Error((await response.json() as { message?: string }).message ?? 'Falha na requisição.')
  return response.json() as Promise<T>
}

export const httpApi: AppApi = {
  books: { list: () => json('/api/books'), create: (input) => json('/api/books', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(input) }) },
  writings: { getWorkspace: (id) => json(`/api/writings/${id}/workspace`), save: (input) => json(`/api/writings/${input.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(input) }) },
  chat: { list: (id) => json(`/api/writings/${id}/messages`) },
  audio: { list: (id) => json(`/api/writings/${id}/audio`) },
  suggestions: { list: (id) => json(`/api/writings/${id}/suggestions`) },
  publishing: { publish: (id) => json(`/api/writings/${id}/publication`, { method: 'POST' }) },
  usage: { getSummary: () => json('/api/usage') },
  public: {
    getLanding: () => json('/api/public/landing'),
    listArticles: () => json('/api/public/articles'),
    listBooks: () => json('/api/public/books'),
  },
}
