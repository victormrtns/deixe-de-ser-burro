import { render, screen } from '@testing-library/react'
import { RouterProvider } from 'react-router-dom'
import { expect, it } from 'vitest'
import { createAppRouter } from '@/app/router'
import { AppProviders } from '@/app/AppProviders'
import { createMockApi } from '@/services/mockApi'

function renderRoute(path: string, authenticated = true) {
  return render(<AppProviders api={createMockApi()}><RouterProvider router={createAppRouter([path], { authenticated })} /></AppProviders>)
}

it('permite leitura pública sem autenticação', async () => {
  renderRoute('/artigos/ritual-antes-do-foco')
  expect(await screen.findByRole('heading', { name: 'Ritual antes do foco' })).toBeVisible()
})

it('redireciona a rota privada para entrada quando não há sessão', async () => {
  renderRoute('/studio', false)
  expect(await screen.findByRole('heading', { name: 'Volte ao seu caderno' })).toBeVisible()
  expect(document.title).toBe('Entrar — Entrelinhas')
})

it('renderiza páginas próprias para 403 e 404', async () => {
  const { unmount } = renderRoute('/sem-permissao')
  expect(await screen.findByRole('heading', { name: 'Acesso restrito' })).toBeVisible()
  unmount()
  renderRoute('/rota-inexistente')
  expect(await screen.findByRole('heading', { name: 'Página não encontrada' })).toBeVisible()
})

it.each([
  ['/artigos', 'Artigos — Entrelinhas'],
  ['/livros', 'Livros — Entrelinhas'],
  ['/livros/trabalho-focado', 'Trabalho focado — Entrelinhas'],
  ['/sobre', 'Sobre — Entrelinhas'],
])('renderiza a rota pública %s com título honesto', async (path, title) => {
  const { unmount } = renderRoute(path)

  expect(await screen.findByRole('main')).toBeInTheDocument()
  expect(document.title).toBe(title)
  unmount()
})
