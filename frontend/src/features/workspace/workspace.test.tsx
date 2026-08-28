import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { WorkspacePage } from '@/features/workspace/WorkspacePage'

afterEach(() => vi.useRealTimers())

it('salva após 800 ms e preserva o texto quando a requisição falha', async () => {
  vi.useFakeTimers()
  const save = vi.fn().mockRejectedValue(new Error('network'))
  render(<WorkspacePage save={save} />)

  fireEvent.change(screen.getByRole('textbox', { name: 'Conteúdo Markdown' }), { target: { value: '# Uma nova ideia' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(800) })

  expect(screen.getByText('Não foi possível salvar.')).toBeVisible()
  expect(screen.getByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue('# Uma nova ideia')
})

it('alterna entre escrita e preview mantendo o conteúdo', async () => {
  const user = userEvent.setup()
  render(<WorkspacePage save={vi.fn().mockResolvedValue(undefined)} />)
  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  await user.clear(editor)
  await user.type(editor, '# Atenção como escolha')
  await user.click(screen.getByRole('tab', { name: 'Visualizar' }))

  expect(screen.getByRole('heading', { name: 'Atenção como escolha' })).toBeVisible()
  await user.click(screen.getByRole('tab', { name: 'Escrever' }))
  expect(screen.getByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue('# Atenção como escolha')
})

it('mantém uma conversa única sem destino separado para áudios', async () => {
  const user = userEvent.setup()
  render(<WorkspacePage save={vi.fn().mockResolvedValue(undefined)} />)

  expect(screen.getByRole('button', { name: 'Conversa' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Áudios' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Conversa' }))
  expect(screen.getByRole('button', { name: 'Gravar áudio' })).toBeInTheDocument()
})

it('expande o documento ao recolher os dois contextos sem perder o texto', async () => {
  const user = userEvent.setup()
  render(<WorkspacePage save={vi.fn().mockResolvedValue(undefined)} />)
  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  await user.type(editor, '\nNota preservada')

  await user.click(screen.getByRole('button', { name: 'Focar no documento' }))

  expect(screen.getByRole('button', { name: 'Mostrar contexto do livro' })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole('button', { name: 'Mostrar assistente' })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole<HTMLTextAreaElement>('textbox', { name: 'Conteúdo Markdown' }).value).toContain('Nota preservada')
})
