import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { App } from '@/app/App'

it('apresenta a biblioteca como tela-base privada', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: 'Sua biblioteca de ideias' })).toBeVisible()
  expect(screen.getByText('R$ 12,40 de R$ 70,00')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Nova escrita' })).toBeEnabled()
})

it('abre a escrita-base e mantém as três regiões acessíveis', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: /Abrir Ritual antes do foco/i }))

  expect(screen.getByRole('navigation', { name: 'Contexto da escrita' })).toBeVisible()
  expect(screen.getByRole('region', { name: 'Documento' })).toBeVisible()
  expect(screen.getByRole('complementary', { name: 'Assistente' })).toBeVisible()
})
