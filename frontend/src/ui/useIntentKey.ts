import { useRef } from 'react'

// Uma chave de idempotência por abertura do diálogo: reenvios do mesmo formulário
// reaproveitam a chave, e fechar e reabrir declara uma intenção nova.
export function useIntentKey(open: boolean) {
  const key = useRef('')
  const wasOpen = useRef(false)
  if (open && !wasOpen.current) key.current = crypto.randomUUID()
  wasOpen.current = open
  return key
}
