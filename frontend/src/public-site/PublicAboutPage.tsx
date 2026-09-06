import { PublicReadingShell } from './PublicReadingShell'
import { useDocumentTitle } from '@/ui/useDocumentTitle'

export function PublicAboutPage() {
  useDocumentTitle('Sobre — deixedeserburro')
  return <PublicReadingShell><section className="public-index"><span className="eyebrow">Sobre</span><h1>Uma leitura que continua.</h1><p>deixedeserburro é uma publicação independente de ensaios nascidos de livros, notas e estudo.</p></section></PublicReadingShell>
}
