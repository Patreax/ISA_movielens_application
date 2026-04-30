import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react'

export type ToastType = 'error' | 'warning' | 'success'

interface ToastItem {
  id: number
  type: ToastType
  message: string
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_CONFIG: Record<ToastType, { icon: string; color: string; border: string; bg: string }> = {
  error: {
    icon: 'error',
    color: '#e50914',
    border: 'rgba(229,9,20,0.55)',
    bg: 'rgba(229,9,20,0.07)',
  },
  warning: {
    icon: 'warning',
    color: '#eab308',
    border: 'rgba(234,179,8,0.55)',
    bg: 'rgba(234,179,8,0.07)',
  },
  success: {
    icon: 'check_circle',
    color: '#22c55e',
    border: 'rgba(34,197,94,0.55)',
    bg: 'rgba(34,197,94,0.07)',
  },
}

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: () => void }) {
  const { icon, color, border, bg } = TOAST_CONFIG[toast.type]
  return (
    <div
      className="toast-enter flex items-start gap-3 px-4 py-3 rounded-sm shadow-2xl w-[340px]"
      style={{ background: `#141414`, border: `1px solid ${border}`, backgroundColor: bg }}
    >
      <span
        className="material-symbols-outlined shrink-0 mt-0.5"
        style={{ color, fontSize: '20px' }}
      >
        {icon}
      </span>
      <p className="text-sm text-zinc-200 leading-snug flex-1">{toast.message}</p>
      <button
        onClick={onDismiss}
        className="text-zinc-600 hover:text-zinc-300 transition-colors shrink-0 mt-0.5"
        aria-label="Dismiss"
      >
        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
          close
        </span>
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counterRef = useRef<number>(0)

  const showToast = useCallback((message: string, type: ToastType = 'error') => {
    const id = ++counterRef.current
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4500)
  }, [])

  function dismiss(id: number) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[200] flex flex-col gap-3 pointer-events-none">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastCard toast={toast} onDismiss={() => dismiss(toast.id)} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}
