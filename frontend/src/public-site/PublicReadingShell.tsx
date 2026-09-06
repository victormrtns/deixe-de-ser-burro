import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import './public-site.css'
import './public-discovery.css'

export function PublicReadingShell({ children }: { children: ReactNode }) {
  return <main className="public-site" aria-label="Entrelinhas"><header className="public-reading-header"><Link className="public-brand" to="/"><img src="/brand/logo-icon.svg" alt="" width={34} height={34} /><span className="public-brand__name">Entrelinhas<span>notas à margem</span></span></Link><nav aria-label="Navegação pública"><Link to="/artigos">Artigos</Link><Link to="/livros">Livros</Link><Link to="/sobre">Sobre</Link></nav></header><div className="public-page">{children}</div><footer className="public-footer"><Link to="/">Entrelinhas</Link><p>Leitura, ideias e escrita independente.</p><span>© 2026</span></footer></main>
}
