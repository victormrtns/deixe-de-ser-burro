import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import axe from 'axe-core'
import { expect, it } from 'vitest'
import { SignInPage } from '@/features/auth/SignInPage'
import { PublicArticlePage } from '@/public-site/PublicArticlePage'
import { AppProviders } from '@/app/AppProviders'
import { createMockApi } from '@/services/mockApi'

it.each([['entrada', <AppProviders api={createMockApi({ session: 'anonymous' })}><MemoryRouter><SignInPage /></MemoryRouter></AppProviders>], ['artigo', <AppProviders api={createMockApi()}><MemoryRouter><PublicArticlePage /></MemoryRouter></AppProviders>]])('não possui violações axe críticas em %s', async (_name, view) => {
  const { container } = render(view)
  const result = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } })
  expect(result.violations.filter((violation) => ['critical', 'serious'].includes(violation.impact ?? ''))).toEqual([])
})
