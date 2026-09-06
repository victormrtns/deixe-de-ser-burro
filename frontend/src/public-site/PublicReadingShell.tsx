import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import './public-site.css'
import './public-discovery.css'

export function PublicReadingShell({ children }: { children: ReactNode }) {
  return (
    <main className="public-site" aria-label="deixedeserburro">
      <header className="public-reading-header">
        <Link className="public-brand" to="/">
          <img src="/favicon.svg" alt="" width={38} height={38} />
          <span className="public-brand__name">
            <img src="/brand/wordmark.svg" alt="deixedeserburro" width={215} height={37} />
            <span>notas à margem</span>
          </span>
        </Link>
        <nav aria-label="Navegação pública">
          <Link to="/artigos">Artigos</Link>
          <Link to="/livros">Livros</Link>
          <Link to="/sobre">Sobre</Link>
        </nav>
      </header>
      <div className="public-page">{children}</div>
      <footer className="public-footer">
        <Link to="/">deixedeserburro</Link>
        <p>Leitura, ideias e escrita independente.</p>
        <span>© 2026</span>
      </footer>
    </main>
  )
}
