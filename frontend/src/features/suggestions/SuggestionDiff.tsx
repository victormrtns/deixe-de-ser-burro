import { useSuggestion } from './SuggestionProvider'

export function SuggestionDiff() {
  const { suggestion } = useSuggestion()

  return (
    <div className="suggestion-diff" aria-label="Comparação da sugestão">
      <section>
        <span>Trecho removido</span>
        <del>{suggestion.before}</del>
      </section>
      <section>
        <span>Trecho adicionado</span>
        <ins>{suggestion.after}</ins>
      </section>
    </div>
  )
}
