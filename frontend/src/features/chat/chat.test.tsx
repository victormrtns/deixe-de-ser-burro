import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ChatPanel } from './Chat'
import { ApiError } from '@/services/httpApi'
import type { ChatApi, ChatStreamEvent, Message, MessageState } from '@/services/contracts'

const author = (id: string, content: string): Message => ({ id, writingId: 'w1', role: 'author', content, state: 'completed', createdAt: '2026-09-05T10:00:00-03:00' })
const assistant = (id: string, content: string, state: MessageState): Message => ({ id, writingId: 'w1', role: 'assistant', content, state, createdAt: '2026-09-05T10:01:00-03:00' })
const started = (messageId: string): ChatStreamEvent => ({ type: 'generation.started', version: 1, attemptId: 'attempt-1', sequence: 0, messageId, attemptNumber: 1 })
const delta = (text: string): ChatStreamEvent => ({ type: 'response.delta', version: 1, attemptId: 'attempt-1', sequence: 1, delta: text })
const completed: ChatStreamEvent = { type: 'response.completed', version: 1, attemptId: 'attempt-1', sequence: 2, usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30, estimatedCostUsdMicros: 900, budgetState: 'normal' } }
const failed: ChatStreamEvent = { type: 'response.failed', version: 1, attemptId: 'attempt-1', sequence: 2, error: { code: 'provider_rate_limited', message: 'O provedor recusou a chamada agora.', requestId: 'req-9' } }

function createChat(overrides: Partial<ChatApi>): ChatApi {
  return {
    list: async () => [],
    streamReply: async () => undefined,
    retry: async () => undefined,
    remember: async () => ({ id: 'memory-1', kind: 'preference', content: 'lembrança', createdAt: '2026-09-05T10:02:00-03:00' }),
    getUsage: async () => ({ period: '2026-09', spentUsdMicros: 0, reservedUsdMicros: 0, limitUsdMicros: 2_000_000, limitState: 'normal' }),
    ...overrides,
  }
}

async function ask(chat: ChatApi, text = 'Organize esta explicação', messages?: Message[]) {
  const user = userEvent.setup()
  const view = render(<ChatPanel writingId="w1" chat={chat} {...(messages ? { messages } : {})} />)
  await user.type(screen.getByLabelText('Mensagem'), text)
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
  return { user, view }
}

it('mostra a resposta progressivamente enquanto os deltas chegam', async () => {
  let release = () => {}
  const gate = new Promise<void>((resolve) => { release = resolve })
  const persisted = [author('author-1', 'Organize esta explicação'), assistant('assistant-1', 'Primeiro trecho e o resto.', 'completed')]
  const chat = createChat({
    list: async () => persisted,
    streamReply: async (_writingId, _content, _key, _signal, onEvent) => { onEvent(started('assistant-1')); onEvent(delta('Primeiro trecho')); await gate; onEvent(delta(' e o resto.')); onEvent(completed) },
  })
  await ask(chat)

  expect(await screen.findByText('Primeiro trecho')).toBeVisible()
  await act(async () => { release(); await Promise.resolve() })
  expect(await screen.findByText('Primeiro trecho e o resto.')).toBeVisible()
})

it('preserva a resposta parcial quando a geração é interrompida', async () => {
  const chat = createChat({
    list: async () => [author('author-1', 'Organize esta explicação'), assistant('assistant-1', 'Primeiro', 'interrupted')],
    streamReply: async (_writingId, _content, _key, signal, onEvent) => {
      onEvent(started('assistant-1'))
      onEvent(delta('Primeiro'))
      await new Promise<void>((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('stop', 'AbortError')), { once: true }))
    },
  })
  const { user } = await ask(chat)

  expect(await screen.findByText('Primeiro')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Parar geração' }))
  expect(await screen.findByText('Geração interrompida')).toBeVisible()
  expect(screen.getByText('Primeiro')).toBeVisible()
})

it('exibe a falha com retry explícito e sem duplicar a mensagem do autor', async () => {
  const attempts = vi.fn()
  let persisted = [author('author-1', 'Organize esta explicação'), assistant('assistant-1', '', 'failed')]
  const chat = createChat({
    list: async () => persisted,
    streamReply: async (_writingId, _content, _key, _signal, onEvent) => { onEvent(started('assistant-1')); onEvent(failed) },
    retry: async (_writingId, messageId, key, _signal, onEvent) => {
      attempts(messageId, key)
      persisted = [author('author-1', 'Organize esta explicação'), assistant('assistant-2', 'Resposta da segunda tentativa.', 'completed')]
      onEvent(started('assistant-2'))
      onEvent(delta('Resposta da segunda tentativa.'))
      onEvent(completed)
    },
  })
  const { user } = await ask(chat)

  expect(await screen.findByRole('alert')).toHaveTextContent('O provedor recusou a chamada agora.')
  await user.click(await screen.findByRole('button', { name: 'Tentar novamente' }))

  expect(await screen.findByText('Resposta da segunda tentativa.')).toBeVisible()
  expect(attempts).toHaveBeenCalledTimes(1)
  expect(attempts.mock.calls[0]?.[0]).toBe('author-1')
  expect(screen.getAllByText('Organize esta explicação')).toHaveLength(1)
})

it('restaura o histórico persistido ao abrir a escrita novamente', async () => {
  render(<ChatPanel writingId="w1" chat={createChat({})} messages={[author('author-1', 'Organize esta explicação'), assistant('assistant-1', 'Separe ambiente, intenção e primeiro gesto.', 'completed')]} />)

  const timeline = screen.getByRole('log', { name: 'Conversa sobre a escrita' })
  expect(within(timeline).getByText('Organize esta explicação')).toBeVisible()
  expect(within(timeline).getByText('Separe ambiente, intenção e primeiro gesto.')).toBeVisible()
})

it('preserva a mensagem digitada quando a sessão expira antes da geração', async () => {
  const chat = createChat({
    streamReply: async () => { throw new ApiError(401, { code: 'authentication_required', message: 'Sua sessão expirou. Entre novamente.', requestId: 'req-1' }) },
  })
  await ask(chat, 'Conecte esta ideia ao capítulo')

  expect(await screen.findByRole('alert')).toHaveTextContent('Sua sessão expirou. Entre novamente.')
  expect(screen.getByLabelText('Mensagem')).toHaveValue('Conecte esta ideia ao capítulo')
  expect(within(screen.getByRole('log', { name: 'Conversa sobre a escrita' })).queryByText('Conecte esta ideia ao capítulo')).not.toBeInTheDocument()
})

it('registra memória explícita a partir de uma resposta concluída', async () => {
  const remember = vi.fn().mockResolvedValue({ id: 'memory-1', kind: 'decision', content: 'Manter o tom seco.', createdAt: '2026-09-05T10:02:00-03:00' })
  const user = userEvent.setup()
  render(<ChatPanel writingId="w1" chat={createChat({ remember })} messages={[assistant('assistant-1', 'Separe ambiente e intenção.', 'completed')]} />)

  await user.click(screen.getByRole('button', { name: 'Lembrar nesta escrita' }))
  await user.selectOptions(screen.getByLabelText('Tipo de memória'), 'decision')
  await user.type(screen.getByLabelText('O que lembrar'), 'Manter o tom seco.')
  await user.click(screen.getByRole('button', { name: 'Guardar memória' }))

  expect(remember).toHaveBeenCalledWith('w1', { kind: 'decision', content: 'Manter o tom seco.', sourceMessageId: 'assistant-1' })
  expect(await screen.findByText('Guardado na memória desta escrita')).toBeVisible()
})

it('não exibe nenhum dado fictício de custo na conversa', async () => {
  const { container } = render(<ChatPanel writingId="w1" chat={createChat({})} messages={[author('author-1', 'Organize esta explicação'), assistant('assistant-1', 'Separe ambiente e intenção.', 'completed')]} />)

  expect(container.textContent).not.toMatch(/R\$|US\$|\bcusto\b|limite mensal/i)
})
