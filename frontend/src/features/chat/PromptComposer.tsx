import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { RotateCcw, Send, Square } from 'lucide-react'
import { useChat } from './ChatProvider'
import { NeutralButton, PrimaryButton } from '@/ui/Button'

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
    {status === 'streaming' ? <NeutralButton type="button" className="chat-stop" icon={<Square size={14} />} onClick={stop}>Parar geração</NeutralButton> : <PrimaryButton type="submit" disabled={!draft.trim()} icon={status === 'failed' && draft.trim() ? <RotateCcw size={15} /> : <Send size={15} />}>{status === 'failed' && draft.trim() ? 'Reenviar mensagem' : 'Enviar'}</PrimaryButton>}
  </form>
}
