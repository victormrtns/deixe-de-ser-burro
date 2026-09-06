import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { AppProviders } from '@/app/AppProviders'
import { createAppRouter } from '@/app/router'
import { ApiError } from '@/services/httpApi'
import { createMockApi } from '@/services/mockApi'

it('mostra credencial inválida inline sem limpar o e-mail digitado', async () => {
  const user = userEvent.setup()
  const api = createMockApi({ session: 'anonymous' })
  api.auth.signIn = vi.fn().mockRejectedValue(new ApiError(401, {
    code: 'invalid_credentials',
    message: 'Credenciais inválidas.',
    requestId: 'request-1',
  }))

  render(<AppProviders api={api}><RouterProvider router={createAppRouter(['/entrar'])} /></AppProviders>)
  const email = await screen.findByLabelText('E-mail')
  await user.type(email, 'autor@example.com')
  await user.type(screen.getByLabelText('Senha'), 'senha-incorreta')
  await user.click(screen.getByRole('button', { name: 'Entrar no estúdio' }))

  expect(await screen.findByText('E-mail ou senha inválidos.')).toBeVisible()
  expect(email).toHaveValue('autor@example.com')
})

it('mantém geometria de carregamento enquanto a sessão não foi resolvida', () => {
  const api = createMockApi({ session: 'anonymous' })
  api.auth.getSession = vi.fn(() => new Promise<never>(() => undefined))

  render(<AppProviders api={api}><RouterProvider router={createAppRouter(['/studio'])} /></AppProviders>)

  expect(screen.getByRole('main', { name: 'Carregando sessão' })).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Volte ao seu caderno' })).not.toBeInTheDocument()
})
