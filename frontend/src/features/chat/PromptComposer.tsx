import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Send, Square } from 'lucide-react'
import { useChat } from './ChatProvider'

export function PromptComposer() {
  const [prompt, setPrompt] = useState('')
  const composing = useRef(false)
  const { send, stop, status } = useChat()
  const submit = (event?: FormEvent) => { event?.preventDefault(); if (!composing.current && prompt.trim()) { void send(prompt); setPrompt('') } }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit() } }
  return <form className="chat-composer" noValidate onSubmit={submit}>
    <label htmlFor="chat-message">Mensagem</label>
    <textarea id="chat-message" className="resize-none" rows={3} style={{ resize: 'none' }} value={prompt} disabled={status === 'streaming'} onChange={(event) => setPrompt(event.target.value)} onKeyDown={onKeyDown} onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }} placeholder="Peça uma estrutura, contraponto ou conexão…" />
    {status === 'streaming' ? <button type="button" className="chat-stop" onClick={stop}><Square size={14} /> Parar geração</button> : <button type="submit" disabled={!prompt.trim()}><Send size={15} /> Enviar</button>}
  </form>
}
