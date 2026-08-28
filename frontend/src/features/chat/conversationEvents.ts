import type { ConversationEvent } from '@/services/contracts'

export function sortConversationEvents(events: ConversationEvent[]) {
  return [...events].sort((left, right) => left.createdAt.localeCompare(right.createdAt) || left.id.localeCompare(right.id))
}

export function mergeConversationEvents(existing: ConversationEvent[], incoming: ConversationEvent[]) {
  const byId = new Map(existing.map((event) => [event.id, event]))
  for (const event of incoming) byId.set(event.id, event)
  return sortConversationEvents([...byId.values()])
}
