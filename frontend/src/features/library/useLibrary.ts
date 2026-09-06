import useSWR from 'swr'
import { useApi } from '@/services/api'
import type { HttpAppApi } from '@/services/contracts'

function useHttpApi() {
  return useApi() as HttpAppApi
}

export function useBooks() {
  const api = useHttpApi()
  return useSWR('books', () => api.books.list())
}

export function useBook(bookId: string) {
  const api = useHttpApi()
  return useSWR(`books/${bookId}`, () => api.books.get(bookId))
}

export function useBookWritings(bookId: string) {
  const api = useHttpApi()
  return useSWR(`books/${bookId}/writings`, () => api.writings.listByBook(bookId))
}
