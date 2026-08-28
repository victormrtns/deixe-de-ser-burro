import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { Recorder } from './Recorder'

it('explica a permissão negada e mantém envio de arquivo disponível', async () => {
  render(<Recorder getUserMedia={() => Promise.reject(new DOMException('Denied', 'NotAllowedError'))} />)
  await userEvent.click(screen.getByRole('button', { name: 'Gravar áudio' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Permita o microfone no navegador')
  expect(screen.getByLabelText('Enviar arquivo de áudio')).toBeEnabled()
})
