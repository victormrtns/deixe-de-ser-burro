import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ChatPanel } from './Chat'

it('coloca texto e áudio na mesma conversa cronológica', async () => {
  const user = userEvent.setup()
  const track = { stop: vi.fn() }
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [track] })
  render(<ChatPanel stream={async (_prompt, _signal, onChunk) => onChunk('Resposta.')} getUserMedia={getUserMedia} />)

  await user.type(screen.getByLabelText('Mensagem'), 'Conecte esta ideia ao capítulo.')
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
  await user.click(screen.getByRole('button', { name: 'Gravar áudio' }))
  await user.click(await screen.findByRole('button', { name: 'Parar gravação' }))

  const timeline = screen.getByRole('log', { name: 'Conversa sobre a escrita' })
  expect(within(timeline).getByText('Conecte esta ideia ao capítulo.')).toBeInTheDocument()
  expect(within(timeline).getByText('Nota de áudio')).toBeInTheDocument()
})
