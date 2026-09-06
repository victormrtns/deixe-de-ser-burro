import { useState } from 'react'
import { BookOpen, Focus, MessageCircle, PanelLeft, PanelRight, Sparkles } from 'lucide-react'
import { ChatPanel } from '@/features/chat/Chat'
import { SuggestionReview } from '@/features/suggestions/SuggestionReview'
import { WorkspaceProvider, type SaveMarkdown } from './WorkspaceProvider'
import { Workspace } from './Workspace'
import { useParams } from 'react-router-dom'
import useSWR from 'swr'
import { useApi } from '@/services/api'
import type { HttpAppApi, Message, Writing } from '@/services/contracts'
import { NeutralButton } from '@/ui/Button'
import { PublishDialog, type PublishResult } from '@/features/publishing/PublishDialog'
import { PublicationStatus } from '@/features/publishing/PublicationStatus'
import { VersionHistory } from './VersionHistory'
import { PanelResizer } from './PanelResizer'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { useToast } from '@/ui/ToastProvider'
import './workspace.css'
import './workspace-sovereign.css'

type Panel = 'document' | 'conversation' | 'suggestions'
const suggestion = { id: 'suggestion-01', writingId: 'writing-01', summary: 'Uma explicação mais linear', before: 'O ritual serve para controlar o dia.', after: 'O ritual reduz decisões até que reste apenas o trabalho.', status: 'pending' as const }

const demoWriting: Writing = { id: 'writing-demo', bookId: 'book-demo', title: 'Ritual antes do foco', markdown: '# Ritual antes do foco\n\nA concentração começa antes do trabalho.', sourceRange: 'Capítulos 3–4', status: 'draft', version: 1, updatedAt: new Date().toISOString() }

export function WorkspacePage({ save: injectedSave }: { save?: SaveMarkdown }) {
  const { id } = useParams()
  const api = useApi() as HttpAppApi
  const { data, error, mutate } = useSWR(id ? `writings/${id}/workspace` : null, () => api.writings.getWorkspace(id!))
  useDocumentTitle(`${data?.writing.title ?? 'Escrita'} — deixedeserburro`)
  if (id && error) return <main className="route-error" aria-label="deixedeserburro"><h1>Não foi possível abrir esta escrita</h1><p>O estúdio não conseguiu carregar o texto e a conversa. Nada foi perdido.</p><NeutralButton onClick={() => void mutate()}>Tentar novamente</NeutralButton></main>
  if (id && !data) return <main aria-label="Carregando escrita">Abrindo escrita…</main>
  const writing = data?.writing ?? demoWriting
  const save: SaveMarkdown = injectedSave ?? ((markdown, expectedVersion) => api.writings.save({ id: writing.id, markdown, expectedVersion }))
  const reload = id ? async () => (await mutate())!.writing : undefined
  const restore = id ? (versionNumber: number, expectedVersion: number) => api.writings.restoreVersion({ id, versionNumber, expectedVersion }) : undefined
  return <WorkspaceLoaded writing={writing} save={save} messages={data?.messages ?? []} {...(reload ? { reload } : {})} {...(restore ? { restore } : {})} />
}

function WorkspaceLoaded({ writing, save, messages, reload, restore }: { writing: Writing; save: SaveMarkdown; messages: Message[]; reload?: () => Promise<Writing>; restore?: (versionNumber: number, expectedVersion: number) => Promise<Writing> }) {
  const api = useApi() as HttpAppApi
  const { notify } = useToast()
  const [panel, setPanel] = useState<Panel>('document')
  const [bookContextOpen, setBookContextOpen] = useState(true)
  const [assistantOpen, setAssistantOpen] = useState(true)
  const [publishOpen, setPublishOpen] = useState(false)
  const [publication, setPublication] = useState<PublishResult>()
  const focusDocument = () => { setBookContextOpen(false); setAssistantOpen(false); setPanel('document') }
  const layout = `workspace-feature-main${bookContextOpen ? '' : ' without-book'}${assistantOpen ? '' : ' without-assistant'}`

  return <WorkspaceProvider save={save} initialMarkdown={writing.markdown} initialVersion={writing.version} {...(reload ? { reload } : {})} {...(restore ? { restore } : {})}><Workspace.Frame>
    <header className="workspace-feature-header">
      <div><span className="eyebrow">Escrita em andamento</span><h1>{writing.title}</h1></div>
      <div className="workspace-header-actions">
        <button type="button" aria-label={bookContextOpen ? 'Ocultar contexto do livro' : 'Mostrar contexto do livro'} aria-expanded={bookContextOpen} onClick={() => setBookContextOpen((open) => !open)}><PanelLeft size={16} /></button>
        <button type="button" aria-label="Focar no documento" onClick={focusDocument}><Focus size={16} /></button>
        <button type="button" aria-label={assistantOpen ? 'Ocultar assistente' : 'Mostrar assistente'} aria-expanded={assistantOpen} onClick={() => setAssistantOpen((open) => !open)}><PanelRight size={16} /></button>
        <Workspace.SaveStatus />
        <NeutralButton onClick={() => setPublishOpen(true)}>Publicar</NeutralButton>
      </div>
    </header>
    <main className={layout}>
      {bookContextOpen ? <><nav aria-label="Contexto da escrita">
        <div className="workspace-book"><BookOpen size={18} /><span>Livro ativo</span><strong>Trabalho focado</strong><small>Cal Newport</small></div>
        <button className={panel === 'conversation' ? 'is-active' : ''} onClick={() => { setPanel('conversation'); setAssistantOpen(true) }}><MessageCircle size={16} /> Conversa</button>
        <button className={panel === 'suggestions' ? 'is-active' : ''} onClick={() => { setPanel('suggestions'); setAssistantOpen(true) }}><Sparkles size={16} /> Sugestões</button>
        {writing.id !== 'writing-demo' ? <VersionHistory writingId={writing.id} /> : null}
      </nav><PanelResizer panel="nav" /></> : null}
      <Workspace.Panel title="Documento"><Workspace.Tabs /><Workspace.Canvas /></Workspace.Panel>
      {assistantOpen ? <><PanelResizer panel="aside" /><aside aria-label="Assistente">
        {panel === 'document' ? <div className="assistant-empty"><span className="eyebrow">Assistente de margem</span><h2>Pense junto com suas notas</h2><p>A conversa lê o Markdown atual e nunca altera o seu texto sozinha. Notas de áudio ainda não estão disponíveis nesta fase.</p><button type="button" onClick={() => setPanel('conversation')}>Abrir conversa</button></div> : null}
        {panel === 'conversation' ? <div className="unified-conversation"><ChatPanel writingId={writing.id} chat={api.chat} messages={messages} /></div> : null}
        {panel === 'suggestions' ? <SuggestionReview suggestion={suggestion} accept={() => Promise.resolve()} /> : null}
      </aside></> : null}
    </main>
    {publication ? <PublicationStatus publication={publication} onCancelCleanup={() => { void api.publishing.cancelCleanup(writing.id).then(() => notify('Limpeza cancelada. O contexto privado fica.', 'success')).catch(() => notify('Não foi possível cancelar a limpeza. A publicação segue como está.', 'error')) }} onUnpublish={() => { void api.publishing.unpublish(writing.id).then(() => { setPublication(undefined); notify('Voltou para rascunho. O artigo saiu do ar.', 'success') }).catch(() => notify('Não foi possível retirar a publicação. O artigo continua no ar.', 'error')) }} /> : null}
    <PublishDialog open={publishOpen} onOpenChange={setPublishOpen} articleTitle={writing.title} publish={(key) => api.publishing.publish(writing.id, key)} onPublished={(result) => { setPublication(result); notify('Publicado. A versão congelada já está no ar.', 'success') }} />
  </Workspace.Frame></WorkspaceProvider>
}
