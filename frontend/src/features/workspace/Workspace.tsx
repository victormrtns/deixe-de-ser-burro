import type { HTMLAttributes, ReactNode } from 'react'
import { useWorkspace } from '@/features/workspace/WorkspaceProvider'
import { MarkdownPreview } from './MarkdownPreview'

function Frame({ children, ...props }: HTMLAttributes<HTMLDivElement>) { return <div {...props} className={`workspace-feature ${props.className ?? ''}`}>{children}</div> }
function Editor() { const { state, actions } = useWorkspace(); return <textarea className="markdown-editor resize-none" style={{ resize: 'none' }} aria-label="Conteúdo Markdown" value={state.markdown} onChange={(event) => actions.updateMarkdown(event.target.value)} /> }
function Preview() { const { state } = useWorkspace(); return <MarkdownPreview markdown={state.markdown} /> }
function SaveStatus() { const { state, actions } = useWorkspace(); const labels = { idle: 'Sem alterações', dirty: 'Alterado', saving: 'Salvando…', saved: 'Salvo', failed: 'Não foi possível salvar.', conflict: 'Seu texto foi preservado. Há uma versão mais recente.' }; return <div className={`workspace-save workspace-save--${state.saveState}`} role="status"><span>{labels[state.saveState]}</span>{state.saveState === 'failed' ? <button type="button" onClick={() => void actions.retrySave()}>Tentar novamente</button> : null}{state.saveState === 'conflict' ? <button type="button" onClick={() => void actions.reloadCanonical()}>Recarregar versão atual</button> : null}</div> }
function Tabs() { const { state, actions } = useWorkspace(); return <div className="workspace-tabs" role="tablist" aria-label="Modo do documento"><button role="tab" aria-selected={state.editorMode === 'edit'} onClick={() => actions.changeMode('edit')}>Escrever</button><button role="tab" aria-selected={state.editorMode === 'preview'} onClick={() => actions.changeMode('preview')}>Visualizar</button><button role="tab" aria-selected={state.editorMode === 'split'} onClick={() => actions.changeMode('split')}>Lado a lado</button></div> }
function Canvas() { const { state } = useWorkspace(); return <div className={`workspace-canvas workspace-canvas--${state.editorMode}`}>{state.editorMode !== 'preview' ? <Editor /> : null}{state.editorMode !== 'edit' ? <Preview /> : null}</div> }
function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="workspace-feature-panel" aria-label={title}>{children}</section> }

export const Workspace = { Frame, Editor, Preview, SaveStatus, Tabs, Canvas, Panel }
