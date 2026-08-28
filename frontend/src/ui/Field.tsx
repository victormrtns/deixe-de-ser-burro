import { useId, type InputHTMLAttributes } from 'react'
import './ui.css'

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  description?: string
  error?: string
}

export function Field({ label, description, error, id, className = '', ...props }: FieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const helpId = description ? `${inputId}-help` : undefined
  const errorId = error ? `${inputId}-error` : undefined
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={`field ${className}`.trim()}>
      <label className="field__label" htmlFor={inputId}>{label}</label>
      {description ? <span className="field__help" id={helpId}>{description}</span> : null}
      <input
        {...props}
        id={inputId}
        className="field__input"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
      {error ? <span className="field__error" id={errorId}>{error}</span> : null}
    </div>
  )
}
