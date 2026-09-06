import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { Writing } from '@/services/contracts'
import { ApiError } from '@/services/httpApi'

export type EditorMode = 'edit' | 'preview' | 'split'
export type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'failed' | 'conflict'
export type SaveMarkdown = (markdown: string, expectedVersion: number) => Promise<Writing | void>

type WorkspaceContract = {
  state: { markdown: string; editorMode: EditorMode; saveState: SaveState; expectedVersion: number }
  actions: { updateMarkdown(markdown: string): void; changeMode(mode: EditorMode): void; retrySave(): Promise<void>; reloadCanonical(): Promise<void>; restoreVersion(versionNumber: number): Promise<boolean> }
}

const WorkspaceContext = createContext<WorkspaceContract | null>(null)

export function WorkspaceProvider({ children, save, initialMarkdown = '# Ritual antes do foco\n\nA concentração começa antes do trabalho.', initialVersion = 1, reload, restore }: { children: ReactNode; save: SaveMarkdown; initialMarkdown?: string; initialVersion?: number; reload?: () => Promise<Writing>; restore?: (versionNumber: number, expectedVersion: number) => Promise<Writing> }) {
  const [markdown, setMarkdown] = useState(initialMarkdown)
  const [editorMode, setEditorMode] = useState<EditorMode>('edit')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [expectedVersion, setExpectedVersion] = useState(initialVersion)
  const expectedVersionRef = useRef(initialVersion)
  const skipNextAutosave = useRef(false)
  const initial = useRef(true)
  const saveCurrent = useCallback(async (value: string) => {
    setSaveState('saving')
    try {
      const saved = await save(value, expectedVersionRef.current)
      const nextVersion = saved?.version ?? expectedVersionRef.current + 1
      expectedVersionRef.current = nextVersion
      setExpectedVersion(nextVersion)
      setSaveState('saved')
    }
    catch (error) { setSaveState(error instanceof ApiError && error.code === 'writing_version_conflict' ? 'conflict' : 'failed') }
  }, [save])

  const reloadCanonical = useCallback(async () => {
    if (!reload) return
    const canonical = await reload()
    skipNextAutosave.current = true
    setMarkdown(canonical.markdown)
    expectedVersionRef.current = canonical.version
    setExpectedVersion(canonical.version)
    setSaveState('idle')
  }, [reload])

  const restoreVersion = useCallback(async (versionNumber: number) => {
    if (!restore) return false
    try { const restored = await restore(versionNumber, expectedVersionRef.current); skipNextAutosave.current = true; setMarkdown(restored.markdown); expectedVersionRef.current = restored.version; setExpectedVersion(restored.version); setSaveState('saved'); return true }
    catch (error) { setSaveState(error instanceof ApiError && error.code === 'writing_version_conflict' ? 'conflict' : 'failed'); return false }
  }, [restore])

  useEffect(() => {
    if (initial.current) { initial.current = false; return }
    if (skipNextAutosave.current) { skipNextAutosave.current = false; return }
    setSaveState('dirty')
    const timer = window.setTimeout(() => { void saveCurrent(markdown) }, 800)
    return () => window.clearTimeout(timer)
  }, [markdown, saveCurrent])

  const value = useMemo<WorkspaceContract>(() => ({ state: { markdown, editorMode, saveState, expectedVersion }, actions: { updateMarkdown: setMarkdown, changeMode: setEditorMode, retrySave: () => saveCurrent(markdown), reloadCanonical, restoreVersion } }), [markdown, editorMode, saveState, expectedVersion, saveCurrent, reloadCanonical, restoreVersion])
  return <WorkspaceContext value={value}>{children}</WorkspaceContext>
}

export function useWorkspace() {
  const value = use(WorkspaceContext)
  if (!value) throw new Error('Workspace deve ser usado dentro de WorkspaceProvider.')
  return value
}
