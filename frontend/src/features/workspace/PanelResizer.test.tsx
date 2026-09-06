import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { PanelResizer, clampWidth } from './PanelResizer'

function renderInGrid(panel: 'nav' | 'aside') {
  return render(<div data-testid="grid"><PanelResizer panel={panel} /></div>)
}

beforeEach(() => localStorage.clear())

it('mantém a largura dentro dos limites do painel', () => {
  expect(clampWidth('nav', 10)).toBe(168)
  expect(clampWidth('nav', 9999)).toBe(380)
  expect(clampWidth('nav', 240.4)).toBe(240)
  expect(clampWidth('aside', 10)).toBe(300)
  expect(clampWidth('aside', 9999)).toBe(680)
})

it('aplica a largura inicial na variável do grid', () => {
  renderInGrid('nav')
  expect(screen.getByTestId('grid').style.getPropertyValue('--workspace-nav-width')).toBe('210px')
  expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '210')
})

it('ajusta pelo teclado e persiste a preferência', async () => {
  const user = userEvent.setup()
  renderInGrid('nav')
  const separator = screen.getByRole('separator')
  separator.focus()

  await user.keyboard('{ArrowRight}')
  expect(screen.getByTestId('grid').style.getPropertyValue('--workspace-nav-width')).toBe('226px')
  expect(localStorage.getItem('workspace:nav-width')).toBe('226')

  await user.keyboard('{Home}')
  expect(separator).toHaveAttribute('aria-valuenow', '168')
})

it('cresce o assistente quando a seta aponta para fora do painel', async () => {
  const user = userEvent.setup()
  renderInGrid('aside')
  screen.getByRole('separator').focus()

  await user.keyboard('{ArrowLeft}')
  expect(screen.getByTestId('grid').style.getPropertyValue('--workspace-aside-width')).toBe('376px')
})

it('recupera a largura guardada e ignora valor fora do limite', () => {
  localStorage.setItem('workspace:aside-width', '99999')
  renderInGrid('aside')
  expect(screen.getByTestId('grid').style.getPropertyValue('--workspace-aside-width')).toBe('680px')
})
