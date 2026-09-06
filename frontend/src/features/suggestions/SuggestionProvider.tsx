import { createContext, use, useState, type ReactNode } from 'react'
import type { Suggestion } from '@/services/contracts'

type Accept = (suggestion: Suggestion) => Promise<void>
type SuggestionState = 'pending' | 'applying' | 'accepted' | 'rejected' | 'conflict'
type SuggestionContract = {
  suggestion: Suggestion
  state: SuggestionState
  accept(): Promise<void>
  reject(): void
  resetConflict(): void
}

const SuggestionContext = createContext<SuggestionContract | null>(null)

export function SuggestionProvider({ suggestion, accept, children }: { suggestion: Suggestion; accept: Accept; children: ReactNode }) {
  const [state, setState] = useState<SuggestionState>('pending')

  const apply = async () => {
    if (state !== 'pending') return
    setState('applying')
    try {
      await accept(suggestion)
      setState('accepted')
    } catch (error) {
      setState(error instanceof Error && error.message === 'conflict' ? 'conflict' : 'pending')
    }
  }

  const value: SuggestionContract = {
    suggestion,
    state,
    accept: apply,
    reject: () => setState('rejected'),
    resetConflict: () => setState('pending'),
  }
  return <SuggestionContext value={value}>{children}</SuggestionContext>
}

export function useSuggestion() {
  const value = use(SuggestionContext)
  if (!value) throw new Error('Sugestão fora do provider.')
  return value
}
