import { useCallback, useLayoutEffect, useRef, type KeyboardEvent, type PointerEvent } from 'react'

export type PanelKey = 'nav' | 'aside'

const LIMITS = {
  nav: { min: 168, max: 380, initial: 210, variable: '--workspace-nav-width', label: 'Largura do contexto do livro' },
  aside: { min: 300, max: 680, initial: 360, variable: '--workspace-aside-width', label: 'Largura do assistente' },
} as const satisfies Record<PanelKey, { min: number; max: number; initial: number; variable: string; label: string }>

export function clampWidth(panel: PanelKey, width: number) {
  const { min, max } = LIMITS[panel]
  return Math.min(max, Math.max(min, Math.round(width)))
}

// A largura é preferência local de um leitor, não estado do documento: localStorage,
// e nunca deixa a tela inutilizável se o navegador recusar (janela privada, cookies bloqueados).
function readStored(panel: PanelKey) {
  try {
    const stored = Number(localStorage.getItem(`workspace:${panel}-width`))
    return stored ? clampWidth(panel, stored) : LIMITS[panel].initial
  } catch {
    return LIMITS[panel].initial
  }
}

function writeStored(panel: PanelKey, width: number) {
  try {
    localStorage.setItem(`workspace:${panel}-width`, String(width))
  } catch {
    /* preferência é descartável */
  }
}

export function PanelResizer({ panel }: { panel: PanelKey }) {
  const { min, max, initial, variable, label } = LIMITS[panel]
  const handle = useRef<HTMLDivElement>(null)
  // Fora do estado do React de propósito: arrastar re-renderizaria o editor e a conversa a cada
  // pointermove. O nó do grid é a única coisa que precisa mudar.
  const width = useRef<number>(initial)

  const apply = useCallback((next: number) => {
    const node = handle.current
    if (!node?.parentElement) return
    width.current = next
    node.parentElement.style.setProperty(variable, `${next}px`)
    node.setAttribute('aria-valuenow', String(next))
  }, [variable])

  useLayoutEffect(() => { apply(readStored(panel)) }, [apply, panel])

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return
    const node = event.currentTarget
    const grid = node.parentElement
    if (!grid) return
    const bounds = grid.getBoundingClientRect()
    node.setPointerCapture(event.pointerId)
    document.body.classList.add('is-resizing')

    const move = (moved: globalThis.PointerEvent) => {
      apply(clampWidth(panel, panel === 'nav' ? moved.clientX - bounds.left : bounds.right - moved.clientX))
    }
    const stop = () => {
      node.removeEventListener('pointermove', move)
      node.removeEventListener('pointerup', stop)
      node.removeEventListener('pointercancel', stop)
      document.body.classList.remove('is-resizing')
      writeStored(panel, width.current)
    }
    node.addEventListener('pointermove', move)
    node.addEventListener('pointerup', stop)
    node.addEventListener('pointercancel', stop)
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.shiftKey ? 48 : 16
    const towardsPanel = panel === 'nav' ? 1 : -1
    const next =
      event.key === 'ArrowLeft' ? width.current - step * towardsPanel
      : event.key === 'ArrowRight' ? width.current + step * towardsPanel
      : event.key === 'Home' ? min
      : event.key === 'End' ? max
      : event.key === 'Enter' ? initial
      : null
    if (next === null) return
    event.preventDefault()
    const clamped = clampWidth(panel, next)
    apply(clamped)
    writeStored(panel, clamped)
  }

  function reset() {
    apply(initial)
    writeStored(panel, initial)
  }

  return <div
    ref={handle}
    className="workspace-resizer"
    role="separator"
    tabIndex={0}
    aria-orientation="vertical"
    aria-label={label}
    aria-valuemin={min}
    aria-valuemax={max}
    aria-valuenow={initial}
    onPointerDown={startDrag}
    onKeyDown={onKeyDown}
    onDoubleClick={reset}
  />
}
