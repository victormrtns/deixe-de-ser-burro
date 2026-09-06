import { createContext, use, useEffect, type ReactNode } from 'react'
import useSWR, { useSWRConfig } from 'swr'
import { useApi } from '@/services/api'

export type SessionState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'author'; email: string }

export interface SessionActions {
  signIn(email: string, password: string): Promise<void>
  signOut(): Promise<void>
}

interface SessionContextValue {
  state: SessionState
  actions: SessionActions
}

const SESSION_KEY = 'auth/session'
const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const api = useApi()
  const { mutate: mutateCache } = useSWRConfig()
  const { data, isLoading, mutate } = useSWR(SESSION_KEY, () => api.auth.getSession())

  useEffect(() => {
    const expireSession = () => { void mutate({ state: 'anonymous' }, { revalidate: false }) }
    window.addEventListener('entrelinhas:session-expired', expireSession)
    return () => window.removeEventListener('entrelinhas:session-expired', expireSession)
  }, [mutate])

  const state: SessionState = isLoading || !data
    ? { status: 'loading' }
    : data.state === 'author'
      ? { status: 'author', email: data.author.email }
      : { status: 'anonymous' }

  async function signIn(email: string, password: string) {
    const session = await api.auth.signIn(email, password)
    await mutate(session, { revalidate: false })
  }

  async function signOut() {
    await api.auth.signOut()
    await mutateCache(() => true, undefined, { revalidate: false })
    await mutate({ state: 'anonymous' }, { revalidate: false })
  }

  return <SessionContext value={{ state, actions: { signIn, signOut } }}>{children}</SessionContext>
}

export function useSession() {
  const session = use(SessionContext)
  if (!session) throw new Error('useSession deve ser usado dentro de SessionProvider.')
  return session
}
