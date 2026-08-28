import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, it } from 'vitest'
import { DangerButton, PrimaryButton } from '@/ui/Button'
import { Dialog } from '@/ui/Dialog'
import { Field } from '@/ui/Field'

function PrimitiveHarness() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <DangerButton onClick={() => setOpen(true)}>Excluir escrita</DangerButton>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Excluir escrita"
        description="Esta ação remove o rascunho e seus materiais privados."
      >
        <PrimaryButton onClick={() => setOpen(false)}>Manter escrita</PrimaryButton>
      </Dialog>
    </>
  )
}

it('mantém a intenção explícita e restaura o foco do diálogo', async () => {
  const user = userEvent.setup()
  render(<PrimitiveHarness />)

  const trigger = screen.getByRole('button', { name: 'Excluir escrita' })
  await user.click(trigger)
  expect(screen.getByRole('alertdialog')).toHaveAccessibleName('Excluir escrita')
  await user.keyboard('{Escape}')
  expect(trigger).toHaveFocus()
})

it('associa ajuda e erro ao campo sem depender da cor', () => {
  render(
    <Field
      label="Título"
      name="title"
      description="Use o título que aparecerá na biblioteca."
      error="Informe um título."
    />,
  )

  expect(screen.getByLabelText('Título')).toHaveAccessibleDescription(
    'Use o título que aparecerá na biblioteca. Informe um título.',
  )
  expect(screen.getByLabelText('Título')).toHaveAttribute('aria-invalid', 'true')
})

it('preserva o rótulo da ação enquanto o botão está ocupado', () => {
  render(<PrimaryButton busy>Publicar</PrimaryButton>)
  expect(screen.getByRole('button', { name: 'Publicar' })).toBeDisabled()
  expect(screen.getByRole('status')).toHaveTextContent('Em andamento')
})
