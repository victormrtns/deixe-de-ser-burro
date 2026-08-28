import { createContext, use, useCallback, useMemo, useRef, useState, type ReactNode } from 'react'

export type ChatMessage = { id: string; role: 'author' | 'assistant' | 'audio'; content: string; interrupted?: boolean }
export type StreamReply = (prompt: string, signal: AbortSignal, onChunk: (chunk: string) => void) => Promise<void>

type ChatContract = {
  messages: ChatMessage[]
  status: 'idle' | 'streaming' | 'failed'
  error: string | null
  send(prompt: string): Promise<void>
  addAudio(title: string): void
  stop(): void
}

const ChatContext = createContext<ChatContract | null>(null)

export function ChatProvider({ children, stream }: { children: ReactNode; stream: StreamReply }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ChatContract['status']>('idle')
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)

  const send = useCallback(async (prompt: string) => {
    const content = prompt.trim()
    if (!content || controller.current) return
    const request = new AbortController()
    const responseId = crypto.randomUUID()
    controller.current = request
    setError(null)
    setStatus('streaming')
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'author', content }, { id: responseId, role: 'assistant', content: '' }])
    try {
      await stream(content, request.signal, (chunk) => {
        if (request.signal.aborted) return
        setMessages((current) => current.map((message) => message.id === responseId ? { ...message, content: message.content + chunk } : message))
      })
      setStatus('idle')
    } catch (cause) {
      if (request.signal.aborted) {
        setMessages((current) => current.map((message) => message.id === responseId ? { ...message, interrupted: true } : message))
        setStatus('idle')
      } else {
        setStatus('failed')
        setError(cause instanceof Error ? cause.message : 'Não foi possível gerar a resposta.')
      }
    } finally {
      controller.current = null
    }
  }, [stream])

  const stop = useCallback(() => controller.current?.abort(), [])
  const addAudio = useCallback((title: string) => setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'audio', content: title }]), [])
  const value = useMemo(() => ({ messages, status, error, send, stop, addAudio }), [messages, status, error, send, stop, addAudio])
  return <ChatContext value={value}>{children}</ChatContext>
}

export function useChat() {
  const value = use(ChatContext)
  if (!value) throw new Error('Chat deve ser usado dentro de ChatProvider.')
  return value
}
