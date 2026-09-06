import { createContext, use, useState, type ReactNode } from 'react'

export type RecorderState = 'idle' | 'requesting_permission' | 'recording' | 'preview' | 'uploading' | 'processing' | 'failed'
type RecorderContract = { state: RecorderState; error: string | null; request(): Promise<void>; stop(): void; select(file: File): void; retry(): void }
const RecorderContext = createContext<RecorderContract | null>(null)

export function RecorderProvider({ children, getUserMedia = (constraints) => navigator.mediaDevices.getUserMedia(constraints), onReady }: { children: ReactNode; getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream>; onReady?: () => void }) {
  const [state, setState] = useState<RecorderState>('idle')
  const [error, setError] = useState<string | null>(null)
  const request = async () => {
    setState('requesting_permission'); setError(null)
    try { const stream = await getUserMedia({ audio: true }); stream.getTracks().forEach((track) => track.stop()); setState('recording') }
    catch { setError('Permita o microfone no navegador ou envie um arquivo de áudio.'); setState('failed') }
  }
  const select = (file: File) => { if (!file.type.startsWith('audio/')) { setError('Escolha um arquivo de áudio compatível.'); setState('failed'); return } setError(null); setState('preview') }
  const value: RecorderContract = {
    state,
    error,
    request,
    stop: () => { setState('preview'); onReady?.() },
    select: (file: File) => { select(file); if (file.type.startsWith('audio/')) onReady?.() },
    retry: () => { setError(null); setState('idle') },
  }
  return <RecorderContext value={value}>{children}</RecorderContext>
}

export function useRecorder() { const value = use(RecorderContext); if (!value) throw new Error('Recorder deve estar dentro de RecorderProvider.'); return value }
