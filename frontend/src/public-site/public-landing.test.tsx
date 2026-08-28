import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SWRConfig } from 'swr'
import { describe, expect, it } from 'vitest'
import { ApiContext } from '@/services/api'
import type { AppApi, PublicLanding } from '@/services/contracts'
import { createMockApi } from '@/services/mockApi'
import { PublicLibraryPage } from './PublicLibraryPage'

function renderLanding(publicLanding?: PublicLanding) {
  const baseApi = createMockApi()
  const api: AppApi = publicLanding
    ? { ...baseApi, public: { ...baseApi.public, getLanding: async () => publicLanding } }
    : baseApi

  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <ApiContext value={api}>
        <MemoryRouter><PublicLibraryPage /></MemoryRouter>
      </ApiContext>
    </SWRConfig>,
  )
}

describe('landing pública', () => {
  it('mostra o artigo em destaque, os recentes e somente livros publicados', async () => {
    renderLanding()

    expect(await screen.findByRole('heading', { level: 2, name: 'Ritual antes do foco' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Artigos recentes' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Estante publicada' })).toBeInTheDocument()
    expect(screen.queryByText('Livro sem publicação')).not.toBeInTheDocument()
  })

  it('mostra um estado vazio útil quando ainda não há publicações', async () => {
    renderLanding({ featuredArticle: null, recentArticles: [], publishedBooks: [] })

    expect(await screen.findByText('Os primeiros ensaios ainda estão sendo preparados.')).toBeInTheDocument()
  })
})
