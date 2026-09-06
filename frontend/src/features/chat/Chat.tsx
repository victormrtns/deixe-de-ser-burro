import { ChatProvider } from './ChatProvider'
import { MessageList } from './MessageList'
import { PromptComposer } from './PromptComposer'
import type { ChatApi, Message } from '@/services/contracts'
import './chat.css'

export function ChatPanel({ writingId, chat, messages }: { writingId: string; chat: ChatApi; messages?: Message[] }) {
  return <ChatProvider writingId={writingId} chat={chat} {...(messages ? { initialMessages: messages } : {})}>
    <section className="chat-frame" aria-label="Conversa sobre a escrita">
      <header><span className="eyebrow">Assistente de margem</span><h2>Pense junto com suas notas</h2></header>
      <MessageList />
      <PromptComposer />
    </section>
  </ChatProvider>
}
