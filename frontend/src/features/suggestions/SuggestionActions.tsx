import { useSuggestion } from './SuggestionProvider'
import { GhostButton, PrimaryButton } from '@/ui/Button'

// Aceitar e descartar ja confirmam inline, no lugar onde a acao aconteceu.
// Um toast repetindo a mesma frase seria a segunda copia da mesma informacao.
export function SuggestionActions() {
  const { state, accept, reject } = useSuggestion()

  if (state === 'accepted') return <p role="status">Alteração aceita em uma nova versão.</p>
  if (state === 'rejected') return <p role="status">Sugestão arquivada.</p>

  return (
    <div className="suggestion-actions">
      <PrimaryButton type="button" busy={state === 'applying'} onClick={() => void accept()}>Aceitar alteração</PrimaryButton>
      <GhostButton type="button" disabled={state === 'applying'} onClick={reject}>Descartar</GhostButton>
    </div>
  )
}
