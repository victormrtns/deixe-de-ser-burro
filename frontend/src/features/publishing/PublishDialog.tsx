import { useRef, useState } from 'react'
import { Dialog } from '@/ui/Dialog'

export type PublishResult = { slug: string; cleanupAt: string }
export function PublishDialog({ open, onOpenChange, articleTitle, publish, onPublished }: { open: boolean; onOpenChange(open: boolean): void; articleTitle: string; publish(idempotencyKey: string): Promise<PublishResult>; onPublished(result: PublishResult): void }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const key = useRef('')
  const wasOpen = useRef(false)
  if (open && !wasOpen.current) key.current = crypto.randomUUID()
  wasOpen.current = open
  const performPublish = async () => { setPending(true); setError(null); try { const result = await publish(key.current); onPublished(result); onOpenChange(false) } catch { setError('Não foi possível publicar. Seu rascunho continua salvo.'); setPending(false) } }
  return <Dialog open={open} onOpenChange={onOpenChange} title={`Publicar “${articleTitle}”?`} description="Uma versão congelada ficará pública. O contexto privado será agendado para limpeza em três dias."><button type="button" autoFocus onClick={() => onOpenChange(false)}>Continuar editando</button><button type="button" disabled={pending} onClick={() => void performPublish()}>{pending ? 'Publicando…' : 'Publicar versão'}</button>{error && <p role="alert">{error}</p>}</Dialog>
}
