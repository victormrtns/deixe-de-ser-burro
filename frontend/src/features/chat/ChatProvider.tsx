import { createContext, use, useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import type { ChatApi, ChatStreamEvent, MemoryKind, Message } from '@/services/contracts'

type ChatStatus = 'idle' | 'streaming' | 'failed'

type ChatContract = {
  messages: Message[]
  status: ChatStatus
  error: string | null
  send(content: string): Promise<boolean>
  retry(messageId: string): Promise<void>
  remember(input: { kind: MemoryKind; content: string; sourceMessageId: string }): Promise<void>
  stop(): void
}

const ChatContext = createContext<ChatContract | null>(null)
const FAILURE = 'Não foi possível gerar a resposta.'

export function ChatProvider({ children, writingId, chat, initialMessages = [] }: { children: ReactNode; writingId: string; chat: ChatApi; initialMessages?: Message[] }) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)
  const generation = useRef(0)
  // Uma chave por intenção de envio, mantida enquanto a mesma intenção não
  // chegar a iniciar uma geração no servidor.
  const intent = useRef<{ content: string; key: string } | null>(null)

  const patch = useCallback((id: string, changes: Partial<Message>) => setMessages((current) => current.map((message) => message.id === id ? { ...message, ...changes } : message)), [])

  const run = useCallback(async (start: (signal: AbortSignal, onEvent: (event: ChatStreamEvent) => void) => Promise<void>) => {
    if (controller.current) return false
    const request = new AbortController()
    const mark = ++generation.current
    controller.current = request
    setError(null)
    setStatus('streaming')
    let assistantId = ''
    try {
      await start(request.signal, (event) => {
        if (event.type === 'generation.started') {
          assistantId = event.messageId
          setMessages((current) => [...current.filter((message) => message.id !== event.messageId), { id: event.messageId, writingId, role: 'assistant', content: '', state: 'streaming', createdAt: new Date().toISOString() }])
          return
        }
        if (!assistantId) return
        if (event.type === 'response.delta') setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + event.delta } : message))
        if (event.type === 'response.completed') patch(assistantId, { state: 'completed' })
        if (event.type === 'response.interrupted') patch(assistantId, { state: 'interrupted' })
        if (event.type === 'response.failed') { patch(assistantId, { state: 'failed' }); setError(event.error.message) }
      })
      setStatus((current) => current === 'failed' ? current : 'idle')
    } catch (cause) {
      if (request.signal.aborted) {
        if (assistantId) patch(assistantId, { state: 'interrupted' })
        setStatus('idle')
      } else {
        if (assistantId) patch(assistantId, { state: 'failed' })
        setError(cause instanceof Error ? cause.message : FAILURE)
        setStatus('failed')
      }
    } finally {
      controller.current = null
    }
    // Só o servidor conhece os identificadores persistidos: reconciliamos o
    // histórico ao fim de cada geração, sem derrubar o estado local se falhar.
    const persisted = await chat.list(writingId).catch(() => null)
    if (persisted && generation.current === mark) setMessages(persisted)
    return assistantId !== ''
  }, [chat, patch, writingId])

  const send = useCallback(async (raw: string) => {
    const content = raw.trim()
    if (!content || controller.current) return false
    const key = intent.current?.content === content ? intent.current.key : crypto.randomUUID()
    intent.current = { content, key }
    const localId = `local:${crypto.randomUUID()}`
    setMessages((current) => [...current, { id: localId, writingId, role: 'author', content, state: 'completed', createdAt: new Date().toISOString() }])
    const started = await run((signal, onEvent) => chat.streamReply(writingId, content, key, signal, onEvent))
    // Nada foi persistido antes do primeiro evento: removemos a mensagem local
    // e o rascunho continua no compositor para um reenvio explícito.
    if (!started) setMessages((current) => current.filter((message) => message.id !== localId))
    else intent.current = null
    return started
  }, [chat, run, writingId])

  const retry = useCallback(async (messageId: string) => {
    const index = messages.findIndex((message) => message.id === messageId)
    if (index < 0) return
    const author = messages[index]!.role === 'author' ? messages[index]! : [...messages.slice(0, index)].reverse().find((message) => message.role === 'author')
    if (!author) return
    if (author.id.startsWith('local:')) { await send(author.content); return }
    setMessages((current) => { const at = current.findIndex((message) => message.id === author.id); return current.filter((message, position) => position <= at || message.state !== 'failed') })
    await run((signal, onEvent) => chat.retry(writingId, author.id, crypto.randomUUID(), signal, onEvent))
  }, [chat, messages, run, send, writingId])

  const remember = useCallback(async ({ kind, content, sourceMessageId }: { kind: MemoryKind; content: string; sourceMessageId: string }) => { await chat.remember(writingId, { kind, content, sourceMessageId }) }, [chat, writingId])
  const stop = useCallback(() => controller.current?.abort(), [])
  const value = useMemo(() => ({ messages, status, error, send, retry, remember, stop }), [messages, status, error, send, retry, remember, stop])
  return <ChatContext value={value}>{children}</ChatContext>
}

export function useChat() {
  const value = use(ChatContext)
  if (!value) throw new Error('Chat deve ser usado dentro de ChatProvider.')
  return value
}
