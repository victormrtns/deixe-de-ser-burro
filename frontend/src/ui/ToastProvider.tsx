import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import './ui.css'

type ToastTone = 'success' | 'warning' | 'info' | 'error'
type Toast = { id: number; message: string; tone: ToastTone }
type ToastActions = { notify(message: string, tone?: ToastTone): void }

const ToastContext = createContext<ToastActions | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const nextId = useRef(0)
  const notify = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = (nextId.current += 1)
    setToasts((current) => [...current.filter((item) => item.message !== message), { id, message, tone }].slice(-3))
    // Aviso efêmero: o desfecho já está na tela; o toast não pode virar painel permanente sobre o conteúdo.
    timers.current.push(setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 8000))
  }, [])
  useEffect(() => { const pending = timers.current; return () => { pending.forEach(clearTimeout) } }, [])
  const actions = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext value={actions}>
      {children}
      <div className="toast-stack">
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
