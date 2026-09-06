import type { ReactNode } from 'react'
import { SWRConfig } from 'swr'
import { ApiContext } from '@/services/api'
import type { AppApi } from '@/services/contracts'
import { SessionProvider } from '@/features/auth/SessionProvider'

export function AppProviders({ api, children }: { api: AppApi; children: ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map(), revalidateOnFocus: false }}><ApiContext value={api}><SessionProvider>{children}</SessionProvider></ApiContext></SWRConfig>
}
