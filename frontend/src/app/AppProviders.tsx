import type { ReactNode } from 'react'
import { SWRConfig } from 'swr'
import { ApiContext } from '@/services/api'
import type { AppApi } from '@/services/contracts'

export function AppProviders({ api, children }: { api: AppApi; children: ReactNode }) {
  return <SWRConfig value={{ revalidateOnFocus: false }}><ApiContext value={api}>{children}</ApiContext></SWRConfig>
}
