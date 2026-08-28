import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { App } from '@/app/App'

it('renderiza o marco principal do Entrelinhas', () => {
  render(<App />)
  expect(screen.getByRole('main', { name: 'Entrelinhas' })).toBeInTheDocument()
})
