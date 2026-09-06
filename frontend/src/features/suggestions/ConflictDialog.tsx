import { Dialog } from '@/ui/Dialog'
import { GhostButton, NeutralButton } from '@/ui/Button'
import { useSuggestion } from './SuggestionProvider'

export function ConflictDialog() {
  const { state, resetConflict } = useSuggestion()

  return (
    <Dialog
      open={state === 'conflict'}
      onOpenChange={(open) => { if (!open) resetConflict() }}
      title="O texto mudou em outro lugar"
      description="Recarregue a versão atual antes de aplicar esta sugestão."
    >
      <GhostButton type="button" autoFocus onClick={resetConflict}>Cancelar</GhostButton>
      <NeutralButton type="button" onClick={resetConflict}>Recarregar versão atual</NeutralButton>
    </Dialog>
  )
}
