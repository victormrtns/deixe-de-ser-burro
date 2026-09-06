import useSWR from 'swr'
import { useApi } from '@/services/api'
import type { HttpAppApi } from '@/services/contracts'

export function usePublicLanding() {
  const api = useApi()
  return useSWR('public/landing', () => api.public.getLanding())
}

export function usePublicArticles() {
  const api = useApi()
  return useSWR('public/articles', () => api.public.listArticles())
}

export function usePublicBooks() {
  const api = useApi()
  return useSWR('public/books', () => api.public.listBooks())
}

export function usePublicArticle(slug: string) {
  const api = useApi() as HttpAppApi
  return useSWR(`public/articles/${slug}`, () => api.public.getArticle(slug))
}
