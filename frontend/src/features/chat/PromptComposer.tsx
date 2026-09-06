import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { RotateCcw, Send, Square } from 'lucide-react'
import { useChat } from './ChatProvider'

export function PromptComposer() {
  const [draft, setDraft] = useState('')
  const composing = useRef(false)
  const { send, stop, status } = useChat()
  // O rascunho só é limpo quando a geração começa: falhas antes do primeiro
  // evento (sessão expirada, contexto ou orçamento) preservam o que foi digitado.
  const submit = async (event?: FormEvent) => { event?.preventDefault(); if (composing.current || !draft.trim()) return; if (await send(draft)) setDraft('') }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit() } }
  return <form className="chat-composer" noValidate onSubmit={(event) => void submit(event)}>
    <label htmlFor="chat-message">Mensagem</label>
    <textarea id="chat-message" className="resize-none" rows={3} style={{ resize: 'none' }} value={draft} disabled={status === 'streaming'} onChange={(event) => setDraft(event.target.value)} onKeyDown={onKeyDown} onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }} placeholder="Peça uma estrutura, contraponto ou conexão…" />
    {status === 'streaming' ? <button type="button" className="chat-stop" onClick={stop}><Square size={14} /> Parar geração</button> : <button type="submit" disabled={!draft.trim()}>{status === 'failed' && draft.trim() ? <><RotateCcw size={15} /> Reenviar mensagem</> : <><Send size={15} /> Enviar</>}</button>}
  </form>
}
