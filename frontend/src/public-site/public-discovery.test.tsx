import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SWRConfig } from 'swr'
import { expect, it } from 'vitest'
import { ApiContext } from '@/services/api'
import { createMockApi } from '@/services/mockApi'
import { PublicArticlePage } from './PublicArticlePage'
import { PublicArticlesPage } from './PublicArticlesPage'
import { PublicBookPage } from './PublicBookPage'
import { PublicBooksPage } from './PublicBooksPage'

function renderPublicRoute(path: string) {
  return render(<SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}><ApiContext value={createMockApi()}><MemoryRouter initialEntries={[path]}><Routes><Route path="/artigos" element={<PublicArticlesPage />} /><Route path="/livros" element={<PublicBooksPage />} /><Route path="/livros/:slug" element={<PublicBookPage />} /><Route path="/artigos/:slug" element={<PublicArticlePage />} /></Routes></MemoryRouter></ApiContext></SWRConfig>)
}

it('navega de um livro publicado para um de seus artigos', async () => {
  const user = userEvent.setup()
  renderPublicRoute('/livros/trabalho-focado')

  await user.click(await screen.findByRole('link', { name: 'Ritual antes do foco' }))

  expect(await screen.findByRole('heading', { level: 1, name: 'Ritual antes do foco' })).toBeInTheDocument()
  expect(document.body.textContent).not.toMatch(/writing-|prompt|transcrição/i)
})

it('lista somente livros com artigos publicados', async () => {
  renderPublicRoute('/livros')

  expect(await screen.findByRole('link', { name: 'Explorar artigos de Trabalho focado' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Explorar artigos de A coragem de não agradar' })).toBeInTheDocument()
  expect(screen.queryByText('Livro sem publicação')).not.toBeInTheDocument()
})

it('expõe o arquivo público de artigos por slug', async () => {
  renderPublicRoute('/artigos')

  expect(await screen.findByRole('link', { name: 'Ritual antes do foco' })).toHaveAttribute('href', '/artigos/ritual-antes-do-foco')
  expect(screen.getByRole('link', { name: 'Liberdade sem romper o pertencimento' })).toBeInTheDocument()
})
