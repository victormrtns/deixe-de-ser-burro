import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { AppProviders } from '@/app/AppProviders'
import { createAppRouter } from '@/app/router'
import type { HttpAppApi } from '@/services/contracts'
import { createMockApi } from '@/services/mockApi'

function renderLibrary(api = createMockApi() as HttpAppApi, path = '/studio') {
  render(<AppProviders api={api}><RouterProvider router={createAppRouter([path])} /></AppProviders>)
  return api
}

it('lista os livros vindos da API com a contagem real de escritas', async () => {
  renderLibrary()
  expect(await screen.findByRole('heading', { name: 'Trabalho focado' })).toBeVisible()
  expect(screen.getByText('3 escritas')).toBeVisible()
})

it('abre o detalhe roteado e cria uma escrita navegando ao workspace', async () => {
  const user = userEvent.setup()
  renderLibrary()
  await user.click(await screen.findByRole('button', { name: 'Abrir Trabalho focado' }))
  expect(await screen.findByRole('heading', { name: 'Escritas deste livro' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Nova escrita' }))
  await user.type(screen.getByLabelText('Título'), 'Ritual de encerramento')
  await user.type(screen.getByLabelText('Trecho coberto'), 'Capítulos 5–6')
  await user.click(screen.getByRole('button', { name: 'Criar escrita' }))
  expect(await screen.findByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue('# Ritual de encerramento')
})

it('reutiliza a chave de idempotência quando a criação do livro é tentada novamente', async () => {
  const user = userEvent.setup()
  const api = createMockApi() as HttpAppApi
  const create = vi.spyOn(api.books, 'create')
    .mockRejectedValueOnce(new Error('indisponível'))
    .mockResolvedValueOnce({ id: 'book-new', title: 'O ofício de escrever', author: 'William Zinsser', writingCount: 0 })
  renderLibrary(api)
  await user.click(await screen.findByRole('button', { name: 'Adicionar livro' }))
  await user.type(screen.getByLabelText('Título'), 'O ofício de escrever')
  await user.type(screen.getByLabelText('Autor'), 'William Zinsser')
  await user.click(screen.getByRole('button', { name: 'Adicionar à estante' }))
  expect(await screen.findByText('Não foi possível adicionar o livro. Tente novamente.')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Adicionar à estante' }))
  expect(create).toHaveBeenCalledTimes(2)
  expect(create.mock.calls[0]?.[1]).toBe(create.mock.calls[1]?.[1])
})
