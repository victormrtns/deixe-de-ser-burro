import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { App } from '@/app/App'

it('abre o livro e apresenta suas escritas', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.click(screen.getByRole('button', { name: 'Abrir Trabalho focado' }))

  expect(screen.getByRole('heading', { name: 'Trabalho focado' })).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Escritas deste livro' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Nova escrita' })).toBeEnabled()
})

it('cria uma escrita dentro do livro selecionado', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.click(screen.getByRole('button', { name: 'Abrir Trabalho focado' }))
  await user.click(screen.getByRole('button', { name: 'Nova escrita' }))
  await user.click(screen.getByRole('button', { name: 'Criar escrita' }))
  expect(screen.getByText('Informe um título.')).toBeVisible()

  await user.type(screen.getByLabelText('Título'), 'Ritual de encerramento')
  await user.type(screen.getByLabelText('Trecho coberto'), 'Capítulos 5–6')
  await user.click(screen.getByRole('button', { name: 'Criar escrita' }))

  const createdTitle = screen.getByRole('heading', { name: 'Ritual de encerramento' })
  expect(createdTitle).toBeVisible()
  expect(within(createdTitle.closest('button')!).getByText('Capítulos 5–6')).toBeVisible()
})

it('cadastra um livro e o mantém visível na estante', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.click(screen.getByRole('button', { name: 'Adicionar livro' }))
  await user.type(screen.getByLabelText('Título'), 'O ofício de escrever')
  await user.type(screen.getByLabelText('Autor'), 'William Zinsser')
  await user.click(screen.getByRole('button', { name: 'Adicionar à estante' }))

  expect(screen.getByRole('heading', { name: 'O ofício de escrever' })).toBeVisible()
  expect(screen.getByText('William Zinsser')).toBeVisible()
})
