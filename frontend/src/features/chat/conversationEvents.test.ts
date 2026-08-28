import { expect, it } from 'vitest'
import type { ConversationEvent } from '@/services/contracts'
import { mergeConversationEvents, sortConversationEvents } from './conversationEvents'

const events: ConversationEvent[] = [
  { id: 'assistant-01', writingId: 'writing-01', type: 'assistant_text', content: 'Vamos desenvolver.', partial: false, status: 'ready', createdAt: '2026-08-28T10:04:00-03:00' },
  { id: 'audio-01', writingId: 'writing-01', type: 'author_audio', title: 'Nota falada', durationSeconds: 42, status: 'ready', createdAt: '2026-08-28T10:02:00-03:00' },
  { id: 'text-01', writingId: 'writing-01', type: 'author_text', content: 'Conecte esta ideia.', status: 'ready', createdAt: '2026-08-28T10:01:00-03:00' },
  { id: 'transcript-01', writingId: 'writing-01', type: 'transcript', audioEventId: 'audio-01', content: 'A atenção começa antes.', status: 'ready', createdAt: '2026-08-28T10:03:00-03:00' },
]

it('ordena texto, áudio, transcrição e assistente na mesma linha do tempo', () => {
  expect(sortConversationEvents(events).map((event) => event.id)).toEqual(['text-01', 'audio-01', 'transcript-01', 'assistant-01'])
})

it('deduplica eventos repetidos e mantém a representação mais recente', () => {
  const audio: Extract<ConversationEvent, { type: 'author_audio' }> = { id: 'audio-01', writingId: 'writing-01', type: 'author_audio', title: 'Nota falada', durationSeconds: 42, status: 'ready', createdAt: '2026-08-28T10:02:00-03:00' }
  const retried: ConversationEvent[] = [{ ...audio, status: 'failed' }, { ...audio, status: 'ready', durationSeconds: 45 }]
  const merged = mergeConversationEvents([audio], retried)
  expect(merged).toHaveLength(1)
  expect(merged[0]).toMatchObject({ status: 'ready', durationSeconds: 45 })
})
