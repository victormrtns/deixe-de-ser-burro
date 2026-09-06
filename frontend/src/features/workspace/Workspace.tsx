import type { HTMLAttributes, KeyboardEvent, ReactNode } from 'react'
import { useWorkspace } from '@/features/workspace/WorkspaceProvider'
import { MarkdownPreview } from './MarkdownPreview'

function Frame({ children, ...props }: HTMLAttributes<HTMLDivElement>) { return <div {...props} className={`workspace-feature ${props.className ?? ''}`}>{children}</div> }
function Editor() { const { state, actions } = useWorkspace(); return <textarea className="markdown-editor resize-none" style={{ resize: 'none' }} aria-label="Conteúdo Markdown" value={state.markdown} onChange={(event) => actions.updateMarkdown(event.target.value)} /> }
function Preview() { const { state } = useWorkspace(); return <MarkdownPreview markdown={state.markdown} /> }
function SaveStatus() { const { state, actions } = useWorkspace(); const labels = { idle: 'Sem alterações', dirty: 'Alterado', saving: 'Salvando…', saved: 'Salvo', failed: 'Não foi possível salvar.', conflict: 'Seu texto foi preservado. Há uma versão mais recente.' }; return <div className={`workspace-save workspace-save--${state.saveState}`} role="status"><span>{labels[state.saveState]}</span>{state.saveState === 'failed' ? <button type="button" className="text-action" onClick={() => void actions.retrySave()}>Tentar novamente</button> : null}{state.saveState === 'conflict' ? <button type="button" className="text-action" onClick={() => void actions.reloadCanonical()}>Recarregar versão atual</button> : null}</div> }
const MODES = [{ id: 'edit', label: 'Escrever' }, { id: 'preview', label: 'Visualizar' }, { id: 'split', label: 'Lado a lado' }] as const

// Padrão WAI-ARIA de abas: as setas trocam de aba, só a aba ativa entra na ordem
// de tabulação, e cada aba aponta para o painel que ela controla. Antes eram três
// botões com role="tab" que não controlavam nada.
function Tabs() {
  const { state, actions } = useWorkspace()
  const move = (event: KeyboardEvent<HTMLDivElement>) => {
    const delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!delta) return
    event.preventDefault()
    const next = MODES[(MODES.findIndex((mode) => mode.id === state.editorMode) + delta + MODES.length) % MODES.length]!
    actions.changeMode(next.id)
    document.getElementById(`workspace-tab-${next.id}`)?.focus()
  }
  return <div className="workspace-tabs" role="tablist" aria-label="Modo do documento" onKeyDown={move}>
    {MODES.map((mode) => <button key={mode.id} id={`workspace-tab-${mode.id}`} type="button" role="tab" aria-selected={state.editorMode === mode.id} aria-controls="workspace-canvas" tabIndex={state.editorMode === mode.id ? 0 : -1} onClick={() => actions.changeMode(mode.id)}>{mode.label}</button>)}
  </div>
}

function Canvas() { const { state } = useWorkspace(); return <div id="workspace-canvas" role="tabpanel" aria-labelledby={`workspace-tab-${state.editorMode}`} className={`workspace-canvas workspace-canvas--${state.editorMode}`}>{state.editorMode !== 'preview' ? <Editor /> : null}{state.editorMode !== 'edit' ? <Preview /> : null}</div> }

function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="workspace-feature-panel" aria-label={title}>{children}</section> }

export const Workspace = { Frame, Editor, Preview, SaveStatus, Tabs, Canvas, Panel }
