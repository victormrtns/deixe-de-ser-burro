import { createContext, use, useMemo, useState, type ReactNode } from 'react'
import type { Suggestion } from '@/services/contracts'

type Accept = (suggestion: Suggestion) => Promise<void>
type SuggestionContract = { suggestion: Suggestion; state: 'pending' | 'applying' | 'accepted' | 'rejected' | 'conflict'; accept(): Promise<void>; reject(): void; resetConflict(): void }
const SuggestionContext = createContext<SuggestionContract | null>(null)

export function SuggestionProvider({ suggestion, accept, children }: { suggestion: Suggestion; accept: Accept; children: ReactNode }) {
  const [state, setState] = useState<SuggestionContract['state']>('pending')
  const apply = async () => { if (state !== 'pending') return; setState('applying'); try { await accept(suggestion); setState('accepted') } catch (error) { setState(error instanceof Error && error.message === 'conflict' ? 'conflict' : 'pending') } }
  const value = useMemo(() => ({ suggestion, state, accept: apply, reject: () => setState('rejected'), resetConflict: () => setState('pending') }), [suggestion, state])
  return <SuggestionContext value={value}>{children}</SuggestionContext>
}
export function useSuggestion() { const value = use(SuggestionContext); if (!value) throw new Error('Sugestão fora do provider.'); return value }
