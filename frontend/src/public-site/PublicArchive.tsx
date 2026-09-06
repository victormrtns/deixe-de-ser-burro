import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function PublicArchive() {
  return (
    <aside className="public-archive">
      <p>Uma biblioteca em construção</p>
      <h2>Nem todo livro termina na última página.</h2>
      <span>O arquivo reúne ensaios, perguntas e ideias que continuaram trabalhando depois da leitura.</span>
      <Link className="editorial-link" to="/artigos">Visitar todos os artigos <ArrowRight size={17} aria-hidden="true" /></Link>
    </aside>
  )
}
