import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ChatPanel } from './Chat'

describe('chat contextual', () => {
  it('preserva a resposta parcial quando a geração é interrompida', async () => {
    const stream = async (_prompt: string, signal: AbortSignal, onChunk: (chunk: string) => void) => {
      onChunk('Primeiro')
      await new Promise<void>((_, reject) => signal.addEventListener('abort', () => reject(new DOMException('stop', 'AbortError')), { once: true }))
    }
    render(<ChatPanel stream={stream} />)
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Mensagem'), 'Organize esta explicação')
    await user.click(screen.getByRole('button', { name: 'Enviar' }))
    expect(await screen.findByText('Primeiro')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Parar geração' }))
    expect(await screen.findByText('Geração interrompida')).toBeVisible()
    expect(screen.getByText('Primeiro')).toBeVisible()
  })
})
