import { render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { RouterProvider } from 'react-router-dom'
import { expect, it } from 'vitest'
import { AppProviders } from '@/app/AppProviders'
import { createAppRouter } from '@/app/router'
import { createMockApi } from '@/services/mockApi'

it('renderiza o marco principal do Entrelinhas', async () => {
  render(<AppProviders api={createMockApi()}><RouterProvider router={createAppRouter(['/studio'])} /></AppProviders>)
  expect(await screen.findByRole('main', { name: 'Entrelinhas' })).toBeInTheDocument()
})

it('não monta o adaptador mock no entrypoint de produção', () => {
  const entrypoint = readFileSync(`${process.cwd()}/src/main.tsx`, 'utf8')
  expect(entrypoint).not.toContain('createMockApi')
  expect(entrypoint).toContain('httpApi')
})
