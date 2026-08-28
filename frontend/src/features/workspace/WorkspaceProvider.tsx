import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

export type EditorMode = 'edit' | 'preview' | 'split'
export type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'failed' | 'conflict'
export type SaveMarkdown = (markdown: string) => Promise<void>

type WorkspaceContract = {
  state: { markdown: string; editorMode: EditorMode; saveState: SaveState }
  actions: { updateMarkdown(markdown: string): void; changeMode(mode: EditorMode): void; retrySave(): Promise<void> }
}

const WorkspaceContext = createContext<WorkspaceContract | null>(null)

export function WorkspaceProvider({ children, save, initialMarkdown = '# Ritual antes do foco\n\nA concentração começa antes do trabalho.' }: { children: ReactNode; save: SaveMarkdown; initialMarkdown?: string }) {
  const [markdown, setMarkdown] = useState(initialMarkdown)
  const [editorMode, setEditorMode] = useState<EditorMode>('edit')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const initial = useRef(true)
  const saveCurrent = useCallback(async (value: string) => {
    setSaveState('saving')
    try { await save(value); setSaveState('saved') } catch { setSaveState('failed') }
  }, [save])

  useEffect(() => {
    if (initial.current) { initial.current = false; return }
    setSaveState('dirty')
    const timer = window.setTimeout(() => { void saveCurrent(markdown) }, 800)
    return () => window.clearTimeout(timer)
  }, [markdown, saveCurrent])

  const value = useMemo<WorkspaceContract>(() => ({ state: { markdown, editorMode, saveState }, actions: { updateMarkdown: setMarkdown, changeMode: setEditorMode, retrySave: () => saveCurrent(markdown) } }), [markdown, editorMode, saveState, saveCurrent])
  return <WorkspaceContext value={value}>{children}</WorkspaceContext>
}

export function useWorkspace() {
  const value = use(WorkspaceContext)
  if (!value) throw new Error('Workspace deve ser usado dentro de WorkspaceProvider.')
  return value
}
