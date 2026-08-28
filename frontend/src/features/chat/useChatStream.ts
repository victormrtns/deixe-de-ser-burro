import type { StreamReply } from './ChatProvider'

export const createDemoChatStream = (): StreamReply => async (_prompt, signal, onChunk) => {
  const chunks = ['Uma forma de tornar essa ideia mais nítida é ', 'separar o ritual em ambiente, intenção e primeiro gesto.']
  for (const chunk of chunks) {
    await new Promise<void>((resolve, reject) => { const timer = window.setTimeout(resolve, 180); signal.addEventListener('abort', () => { window.clearTimeout(timer); reject(new DOMException('Interrompida', 'AbortError')) }, { once: true }) })
    onChunk(chunk)
  }
}
