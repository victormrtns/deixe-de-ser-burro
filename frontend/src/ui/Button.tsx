import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './ui.css'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean
  icon?: ReactNode
}

function ActionButton({ busy = false, className = '', children, icon, disabled, ...props }: ButtonProps & { tone: string }) {
  const { tone, ...buttonProps } = props
  return (
    <button
      {...buttonProps}
      className={`button button--${tone} ${className}`.trim()}
      disabled={disabled || busy}
      aria-busy={busy}
      aria-label={busy && typeof children === 'string' ? children : buttonProps['aria-label']}
    >
      <span className="button__content">{icon}{children}</span>
      {busy ? <span className="sr-only" role="status" aria-label="Em andamento">Em andamento</span> : null}
    </button>
  )
}

export function PrimaryButton(props: ButtonProps) {
  return <ActionButton {...props} tone="primary" />
}

export function NeutralButton(props: ButtonProps) {
  return <ActionButton {...props} tone="neutral" />
}

export function GhostButton(props: ButtonProps) {
  return <ActionButton {...props} tone="ghost" />
}

export function DangerButton(props: ButtonProps) {
  return <ActionButton {...props} tone="danger" />
}
