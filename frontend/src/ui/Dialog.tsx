import * as AlertDialog from '@radix-ui/react-alert-dialog'
import type { ReactNode } from 'react'
import './ui.css'

type DialogProps = {
  open: boolean
  onOpenChange(open: boolean): void
  title: string
  description: string
  children: ReactNode
}

export function Dialog({ open, onOpenChange, title, description, children }: DialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="dialog__overlay" />
        <AlertDialog.Content className="dialog" onEscapeKeyDown={() => onOpenChange(false)}>
          <span className="eyebrow">Confirmação</span>
          <AlertDialog.Title className="dialog__title">{title}</AlertDialog.Title>
          <AlertDialog.Description className="dialog__description">{description}</AlertDialog.Description>
          <div className="dialog__actions">{children}</div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
