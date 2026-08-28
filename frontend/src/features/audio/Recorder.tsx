import { Mic, Square, Upload } from 'lucide-react'
import { RecorderProvider, useRecorder } from './RecorderProvider'
import './audio.css'

function RecorderControls() {
  const { state, error, request, stop, select, retry } = useRecorder()
  return <section className="recorder" aria-label="Notas de áudio">
    <header><span className="eyebrow">Voz na margem</span><h2>Capture antes que a ideia escape</h2></header>
    {error && <p role="alert">{error}</p>}
    {state === 'recording' ? <button type="button" onClick={stop}><Square size={15} /> Parar gravação</button> : <button type="button" disabled={state === 'requesting_permission'} onClick={() => void request()}><Mic size={16} /> {state === 'requesting_permission' ? 'Solicitando…' : 'Gravar áudio'}</button>}
    <label className="audio-upload"><Upload size={16} /> Enviar arquivo de áudio<input type="file" accept="audio/*" onChange={(event) => { const file = event.target.files?.[0]; if (file) select(file) }} /></label>
    {state === 'preview' && <div className="audio-preview"><strong>Áudio pronto</strong><span>Revise antes de enviar para transcrição.</span></div>}
    {state === 'failed' && <button type="button" className="text-action" onClick={retry}>Tentar novamente</button>}
  </section>
}

export function Recorder(props: { getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream>; onReady?: () => void }) { return <RecorderProvider {...props}><RecorderControls /></RecorderProvider> }
