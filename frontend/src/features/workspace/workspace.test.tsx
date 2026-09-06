import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { WorkspacePage } from '@/features/workspace/WorkspacePage'
import { WorkspaceProvider, type SaveMarkdown } from '@/features/workspace/WorkspaceProvider'
import { Workspace } from '@/features/workspace/Workspace'
import { AppProviders } from '@/app/AppProviders'
import { createMockApi } from '@/services/mockApi'
import type { HttpAppApi } from '@/services/contracts'

afterEach(() => vi.useRealTimers())

function renderWorkspace(save: SaveMarkdown) {
  return render(<AppProviders api={createMockApi()}><WorkspacePage save={save} /></AppProviders>)
}

it('salva após 800 ms e preserva o texto quando a requisição falha', async () => {
  vi.useFakeTimers()
  const save = vi.fn().mockRejectedValue(new Error('network'))
  renderWorkspace(save)

  fireEvent.change(screen.getByRole('textbox', { name: 'Conteúdo Markdown' }), { target: { value: '# Uma nova ideia' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(800) })

  expect(screen.getByText('Não foi possível salvar.')).toBeVisible()
  expect(screen.getByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue('# Uma nova ideia')
})

it('salva uma única vez por edição e usa a versão devolvida na próxima edição', async () => {
  vi.useFakeTimers()
  const save = vi.fn()
    .mockResolvedValueOnce({ id: 'writing-demo', bookId: 'book-demo', title: 'Ritual', markdown: '# Primeira', sourceRange: '', status: 'draft', version: 2, updatedAt: '' })
    .mockResolvedValueOnce({ id: 'writing-demo', bookId: 'book-demo', title: 'Ritual', markdown: '# Segunda', sourceRange: '', status: 'draft', version: 3, updatedAt: '' })
  renderWorkspace(save)

  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  fireEvent.change(editor, { target: { value: '# Primeira' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(1600) })
  expect(save).toHaveBeenCalledTimes(1)
  expect(save).toHaveBeenLastCalledWith('# Primeira', 1)

  fireEvent.change(editor, { target: { value: '# Segunda' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(800) })
  expect(save).toHaveBeenLastCalledWith('# Segunda', 2)
})

it('alterna entre escrita e preview mantendo o conteúdo', async () => {
  const user = userEvent.setup()
  renderWorkspace(vi.fn().mockResolvedValue(undefined))
  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  await user.clear(editor)
  await user.type(editor, '# Atenção como escolha')
  await user.click(screen.getByRole('tab', { name: 'Visualizar' }))

  expect(screen.getByRole('heading', { name: 'Atenção como escolha' })).toBeVisible()
  await user.click(screen.getByRole('tab', { name: 'Escrever' }))
  expect(screen.getByRole('textbox', { name: 'Conteúdo Markdown' })).toHaveValue('# Atenção como escolha')
})

it('mantém uma conversa única e não oferece áudio nesta fase', async () => {
  const user = userEvent.setup()
  renderWorkspace(vi.fn().mockResolvedValue(undefined))

  expect(screen.getByRole('button', { name: 'Conversa' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Áudios' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Conversa' }))
  expect(screen.getByRole('log', { name: 'Conversa sobre a escrita' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Gravar áudio' })).not.toBeInTheDocument()
})

it('mantém o editor utilizável durante a geração do assistente', async () => {
  const user = userEvent.setup()
  const mock = createMockApi()
  let release = () => {}
  const api: HttpAppApi = { ...mock, chat: { ...mock.chat, streamReply: async (_writingId, _content, _key, _signal, onEvent) => {
    onEvent({ type: 'generation.started', version: 1, attemptId: 'a1', sequence: 0, messageId: 'assistant-1', attemptNumber: 1 })
    onEvent({ type: 'response.delta', version: 1, attemptId: 'a1', sequence: 1, delta: 'Trecho parcial' })
    await new Promise<void>((resolve) => { release = resolve })
  } } }
  render(<AppProviders api={api}><WorkspacePage save={vi.fn().mockResolvedValue(undefined)} /></AppProviders>)

  await user.click(screen.getByRole('button', { name: 'Conversa' }))
  await user.type(screen.getByLabelText('Mensagem'), 'Organize esta explicação')
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('Trecho parcial')).toBeVisible()

  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  fireEvent.change(editor, { target: { value: '# Ainda editável durante a geração' } })
  expect(editor).toHaveValue('# Ainda editável durante a geração')
  await act(async () => { release() })
})

it('expande o documento ao recolher os dois contextos sem perder o texto', async () => {
  const user = userEvent.setup()
  renderWorkspace(vi.fn().mockResolvedValue(undefined))
  const editor = screen.getByRole('textbox', { name: 'Conteúdo Markdown' })
  await user.type(editor, '\nNota preservada')

  await user.click(screen.getByRole('button', { name: 'Focar no documento' }))

  expect(screen.getByRole('button', { name: 'Mostrar contexto do livro' })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole('button', { name: 'Mostrar assistente' })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole<HTMLTextAreaElement>('textbox', { name: 'Conteúdo Markdown' }).value).toContain('Nota preservada')
})

it('troca o modo do documento pelas setas e aponta a aba para o painel', async () => {
  const user = userEvent.setup()
  render(<WorkspaceProvider save={async () => {}} initialMarkdown="# Texto" initialVersion={1}><Workspace.Tabs /><Workspace.Canvas /></WorkspaceProvider>)

  const escrever = screen.getByRole('tab', { name: 'Escrever' })
  expect(escrever).toHaveAttribute('aria-selected', 'true')
  expect(escrever).toHaveAttribute('aria-controls', 'workspace-canvas')
  expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'workspace-tab-edit')

  escrever.focus()
  await user.keyboard('{ArrowRight}')
  expect(screen.getByRole('tab', { name: 'Visualizar' })).toHaveAttribute('aria-selected', 'true')
  expect(escrever).toHaveAttribute('tabindex', '-1')

  await user.keyboard('{ArrowLeft}')
  expect(screen.getByRole('tab', { name: 'Escrever' })).toHaveAttribute('aria-selected', 'true')
})
