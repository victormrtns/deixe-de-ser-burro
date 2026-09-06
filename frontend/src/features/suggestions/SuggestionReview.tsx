import type { Suggestion } from '@/services/contracts'
import { SuggestionProvider } from './SuggestionProvider'
import { SuggestionDiff } from './SuggestionDiff'
import { SuggestionActions } from './SuggestionActions'
import { ConflictDialog } from './ConflictDialog'
import './suggestions.css'

export function SuggestionReview({ suggestion, accept }: { suggestion: Suggestion; accept: (suggestion: Suggestion) => Promise<void> }) {
  return (
    <SuggestionProvider suggestion={suggestion} accept={accept}>
      <article className="suggestion-review">
        <span className="eyebrow">Sugestão de estrutura</span>
        <h2>{suggestion.summary}</h2>
        <SuggestionDiff />
        <SuggestionActions />
      </article>
      <ConflictDialog />
    </SuggestionProvider>
  )
}
