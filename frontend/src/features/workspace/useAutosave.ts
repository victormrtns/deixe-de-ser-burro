import { useEffect, useRef } from 'react'
export function useAutosave(value: string, save: (value: string) => Promise<void>, delay = 800) { const initial = useRef(true); useEffect(() => { if (initial.current) { initial.current = false; return }; const timer = window.setTimeout(() => void save(value), delay); return () => window.clearTimeout(timer) }, [value, save, delay]) }
