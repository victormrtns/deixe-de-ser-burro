import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useSession } from './SessionProvider'

export function RequireAuthor({ children }: { children: ReactNode }) {
  const { state } = useSession()
  const location = useLocation()

  if (state.status === 'loading') {
    return <main aria-label="Carregando sessão" className="session-placeholder"><p role="status">Abrindo seu caderno…</p></main>
  }
  if (state.status === 'anonymous') {
    return <Navigate to="/entrar" replace state={{ from: location }} />
  }
  return children
}
