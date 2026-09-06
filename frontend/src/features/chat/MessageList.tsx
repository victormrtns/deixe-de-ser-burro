import { useState, type FormEvent } from 'react'
import { useChat } from './ChatProvider'
import type { MemoryKind, Message } from '@/services/contracts'

const KINDS: { value: MemoryKind; label: string }[] = [{ value: 'preference', label: 'Preferência editorial' }, { value: 'decision', label: 'Decisão confirmada' }, { value: 'open_question', label: 'Pergunta em aberto' }]

function MemoryAction({ message }: { message: Message }) {
  const { remember } = useChat()
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<MemoryKind>('preference')
  const [content, setContent] = useState('')
  const [saved, setSaved] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!content.trim()) return
    try { await remember({ kind, content: content.trim(), sourceMessageId: message.id }); setSaved(true); setOpen(false); setContent('') } catch (cause) { setFailure(cause instanceof Error ? cause.message : 'Não foi possível lembrar isto.') }
  }
  if (!open) return <div className="chat-memory">{saved ? <small>Guardado na memória desta escrita</small> : null}<button type="button" className="text-action" onClick={() => { setOpen(true); setSaved(false) }}>Lembrar nesta escrita</button></div>
  return <form className="chat-memory" onSubmit={(event) => void submit(event)}>
    <label htmlFor={`memory-kind-${message.id}`}>Tipo de memória</label>
    <select id={`memory-kind-${message.id}`} value={kind} onChange={(event) => setKind(event.target.value as MemoryKind)}>{KINDS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
    <label htmlFor={`memory-content-${message.id}`}>O que lembrar</label>
    <textarea id={`memory-content-${message.id}`} rows={2} value={content} onChange={(event) => setContent(event.target.value)} />
    {failure ? <p role="alert">{failure}</p> : null}
    <div className="chat-memory-actions"><button type="button" className="text-action" onClick={() => setOpen(false)}>Cancelar</button><button type="submit" disabled={!content.trim()}>Guardar memória</button></div>
  </form>
}

export function MessageList() {
  const { messages, error, retry } = useChat()
  return <div className="chat-messages" role="log" aria-label="Conversa sobre a escrita" aria-live="polite">
    {messages.length === 0 && <p className="chat-empty">Pergunte, organize ou confronte uma ideia sem alterar o seu texto.</p>}
    {messages.map((message) => <article className={`chat-message chat-message--${message.role} chat-message--${message.state}`} key={message.id}>
      <span>{message.role === 'author' ? 'Você' : 'Assistente'}</span>
      <p>{message.content || (message.state === 'streaming' ? 'Pensando…' : 'Sem conteúdo recebido')}</p>
      {message.state === 'interrupted' && <small>Geração interrompida</small>}
      {message.state === 'failed' && <><small>Resposta não concluída</small><button type="button" className="text-action" onClick={() => void retry(message.id)}>Tentar novamente</button></>}
      {message.role === 'assistant' && message.state === 'completed' && <MemoryAction message={message} />}
    </article>)}
    {error && <p role="alert" className="chat-error">{error}</p>}
  </div>
}
