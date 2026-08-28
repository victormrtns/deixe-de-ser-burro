import { useState } from 'react'
import { BookOpen, Focus, MessageCircle, PanelLeft, PanelRight, Sparkles } from 'lucide-react'
import { ChatPanel } from '@/features/chat/Chat'
import { createDemoChatStream } from '@/features/chat/useChatStream'
import { SuggestionReview } from '@/features/suggestions/SuggestionReview'
import { WorkspaceProvider, type SaveMarkdown } from './WorkspaceProvider'
import { Workspace } from './Workspace'
import './workspace.css'
import './workspace-sovereign.css'

type Panel = 'document' | 'conversation' | 'suggestions'
const suggestion = { id: 'suggestion-01', writingId: 'writing-01', summary: 'Uma explicação mais linear', before: 'O ritual serve para controlar o dia.', after: 'O ritual reduz decisões até que reste apenas o trabalho.', status: 'pending' as const }

export function WorkspacePage({ save }: { save: SaveMarkdown }) {
  const [panel, setPanel] = useState<Panel>('document')
  const [bookContextOpen, setBookContextOpen] = useState(true)
  const [assistantOpen, setAssistantOpen] = useState(true)
  const focusDocument = () => { setBookContextOpen(false); setAssistantOpen(false); setPanel('document') }
  const layout = `workspace-feature-main${bookContextOpen ? '' : ' without-book'}${assistantOpen ? '' : ' without-assistant'}`

  return <WorkspaceProvider save={save}><Workspace.Frame>
    <header className="workspace-feature-header">
      <div><span className="eyebrow">Trabalho focado</span><strong>Ritual antes do foco</strong></div>
      <div className="workspace-header-actions">
        <button type="button" aria-label={bookContextOpen ? 'Ocultar contexto do livro' : 'Mostrar contexto do livro'} aria-expanded={bookContextOpen} onClick={() => setBookContextOpen((open) => !open)}><PanelLeft size={16} /></button>
        <button type="button" aria-label="Focar no documento" onClick={focusDocument}><Focus size={16} /></button>
        <button type="button" aria-label={assistantOpen ? 'Ocultar assistente' : 'Mostrar assistente'} aria-expanded={assistantOpen} onClick={() => setAssistantOpen((open) => !open)}><PanelRight size={16} /></button>
        <Workspace.SaveStatus />
      </div>
    </header>
    <main className={layout}>
      {bookContextOpen ? <nav aria-label="Contexto da escrita">
        <div className="workspace-book"><BookOpen size={18} /><span>Livro ativo</span><strong>Trabalho focado</strong><small>Cal Newport</small></div>
        <button className={panel === 'conversation' ? 'is-active' : ''} onClick={() => { setPanel('conversation'); setAssistantOpen(true) }}><MessageCircle size={16} /> Conversa</button>
        <button className={panel === 'suggestions' ? 'is-active' : ''} onClick={() => { setPanel('suggestions'); setAssistantOpen(true) }}><Sparkles size={16} /> Sugestões</button>
      </nav> : null}
      <Workspace.Panel title="Documento"><Workspace.Tabs /><Workspace.Canvas /></Workspace.Panel>
      {assistantOpen ? <aside aria-label="Assistente">
        {panel === 'document' ? <div className="assistant-empty"><span className="eyebrow">Assistente</span><h2>Pense junto com suas notas</h2><p>Conversa, áudio e sugestões entram aqui sem alterar seu texto diretamente.</p><button type="button" onClick={() => setPanel('conversation')}>Abrir conversa</button></div> : null}
        {panel === 'conversation' ? <div className="unified-conversation"><ChatPanel stream={createDemoChatStream()} /></div> : null}
        {panel === 'suggestions' ? <SuggestionReview suggestion={suggestion} accept={() => Promise.resolve()} /> : null}
      </aside> : null}
    </main>
  </Workspace.Frame></WorkspaceProvider>
}
