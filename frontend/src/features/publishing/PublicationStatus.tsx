import { CalendarClock, ExternalLink } from 'lucide-react'
import type { PublishResult } from './PublishDialog'
import './publishing.css'

export function PublicationStatus({ publication, onCancelCleanup, onUnpublish }: { publication: PublishResult; onCancelCleanup(): void; onUnpublish(): void }) {
  const date = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(publication.cleanupAt))
  return <aside className="publication-status" aria-label="Status da publicação"><CalendarClock size={18} /><div><strong>Publicado com limpeza agendada</strong><p>O contexto privado será removido em {date}.</p><a href={`/artigos/${publication.slug}`}>Abrir artigo público <ExternalLink size={14} /></a><div className="publication-actions"><button type="button" className="text-action" onClick={onCancelCleanup}>Cancelar limpeza</button><button type="button" className="text-action" onClick={onUnpublish}>Voltar para rascunho</button></div></div></aside>
}
