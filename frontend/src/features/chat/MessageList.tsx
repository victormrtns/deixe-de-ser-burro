import { useChat } from './ChatProvider'

export function MessageList() {
  const { messages, error } = useChat()
  return <div className="chat-messages" role="log" aria-label="Conversa sobre a escrita" aria-live="polite">
    {messages.length === 0 && <p className="chat-empty">Pergunte, organize ou confronte uma ideia sem alterar o seu texto.</p>}
    {messages.map((message) => <article className={`chat-message chat-message--${message.role}`} key={message.id}>
      <span>{message.role === 'author' ? 'Você' : message.role === 'audio' ? 'Áudio' : 'Assistente'}</span>
      <p>{message.content || 'Pensando…'}</p>
      {message.interrupted && <small>Geração interrompida</small>}
    </article>)}
    {error && <p role="alert" className="chat-error">{error}</p>}
  </div>
}
