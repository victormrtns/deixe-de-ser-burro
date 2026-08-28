import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDocumentTitle } from '@/ui/useDocumentTitle'

export function ForbiddenPage() {
  useDocumentTitle('Acesso restrito — Entrelinhas')
  return <main className="route-error" aria-label="Entrelinhas"><span className="error-code">403</span><h1>Acesso restrito</h1><p>Esta parte do caderno pertence ao estúdio particular.</p><Link to="/"><ArrowLeft size={16} /> Voltar para as leituras</Link></main>
}

export function NotFoundPage() {
  useDocumentTitle('Página não encontrada — Entrelinhas')
  return <main className="route-error" aria-label="Entrelinhas"><span className="error-code">404</span><h1>Página não encontrada</h1><p>Esta anotação pode ter mudado de lugar ou nunca ter sido publicada.</p><Link to="/"><ArrowLeft size={16} /> Voltar para as leituras</Link></main>
}
