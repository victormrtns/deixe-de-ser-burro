import { createContext, use } from 'react'
import type { AppApi } from '@/services/contracts'

export const ApiContext = createContext<AppApi | null>(null)

export function useApi() {
  const api = use(ApiContext)
  if (!api) throw new Error('useApi deve ser usado dentro do provider da aplicação.')
  return api
}
