import { createContext, use, useCallback, useMemo, useState, type ReactNode } from 'react'
import './ui.css'

type ToastTone = 'success' | 'warning' | 'info' | 'error'
type Toast = { id: number; message: string; tone: ToastTone }
type ToastActions = { notify(message: string, tone?: ToastTone): void }

const ToastContext = createContext<ToastActions | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const notify = useCallback((message: string, tone: ToastTone = 'info') => {
    setToasts((current) => [...current.filter((item) => item.message !== message), { id: Date.now(), message, tone }].slice(-3))
  }, [])
  const actions = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext value={actions}>
      {children}
      <div className="toast-stack" aria-label="Notificações">
        {toasts.map((toast) => <div className={`toast toast--${toast.tone}`} role="status" key={toast.id}>{toast.message}</div>)}
      </div>
    </ToastContext>
  )
}

// Provider and hook intentionally share this focused public contract.
// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const value = use(ToastContext)
  if (!value) throw new Error('useToast deve ser usado dentro de ToastProvider.')
  return value
}
