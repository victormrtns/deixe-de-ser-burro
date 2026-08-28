import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it } from 'vitest'
import { PublicArticlePage } from '@/public-site/PublicArticlePage'
import { AppProviders } from '@/app/AppProviders'
import { createMockApi } from '@/services/mockApi'
it('renderiza somente artefatos públicos da escrita', async () => { render(<AppProviders api={createMockApi()}><MemoryRouter><PublicArticlePage /></MemoryRouter></AppProviders>); expect(await screen.findByRole('article')).toHaveTextContent('Ritual antes do foco'); expect(screen.queryByText('Transcrição original')).not.toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Aceitar alteração' })).not.toBeInTheDocument() })
