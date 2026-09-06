import useSWR from 'swr'
import { useApi } from '@/services/api'

export function useBooks() {
  const api = useApi()
  return useSWR('books', () => api.books.list())
}

export function useBook(bookId: string) {
  const api = useApi()
  return useSWR(`books/${bookId}`, () => api.books.get(bookId))
}

export function useBookWritings(bookId: string) {
  const api = useApi()
  return useSWR(`books/${bookId}/writings`, () => api.writings.listByBook(bookId))
}
