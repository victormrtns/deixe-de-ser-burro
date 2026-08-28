import type { HTMLAttributes } from 'react'
import './ui.css'

export function Surface({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`surface ${className}`.trim()} />
}
