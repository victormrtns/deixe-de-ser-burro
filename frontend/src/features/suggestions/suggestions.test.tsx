import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { SuggestionReview } from './SuggestionReview'

const suggestion = { id: 's1', writingId: 'w1', summary: 'Uma explicação mais linear', before: '# Versão atual', after: '# Versão revisada', status: 'pending' as const }
it('não aplica a sugestão antes do aceite e aceita uma única vez', async () => {
  const accept = vi.fn().mockResolvedValue(undefined)
  render(<><textarea className="resize-none" aria-label="Conteúdo Markdown" style={{ resize: 'none' }} defaultValue="# Versão atual" /><SuggestionReview suggestion={suggestion} accept={accept} /></>)
  expect(screen.getByLabelText('Conteúdo Markdown')).toHaveValue('# Versão atual')
  expect(screen.getByText('Uma explicação mais linear')).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'Aceitar alteração' }))
  expect(accept).toHaveBeenCalledTimes(1)
  expect(await screen.findByText('Alteração aceita em uma nova versão.')).toBeVisible()
})
