import { Link } from 'react-router-dom'
import { PrimaryButton } from '@/ui/Button'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PublicReadingShell } from './PublicReadingShell'
import { usePublicArticles } from './usePublicContent'

export function PublicArticlesPage() {
  useDocumentTitle('Artigos — deixedeserburro')
  const { data: articles, error, isLoading, mutate } = usePublicArticles()
  return <PublicReadingShell><header className="archive-header"><p className="editorial-kicker">Arquivo público</p><h1>Artigos</h1><p>Ensaios nascidos de livros, notas e estudo.</p></header>{isLoading ? <p className="public-status" role="status">Abrindo o arquivo…</p> : null}{error ? <section className="public-status"><h2>Não foi possível abrir os artigos.</h2><PrimaryButton onClick={() => void mutate()}>Tentar novamente</PrimaryButton></section> : null}{articles ? <ol className="archive-list">{articles.map((article, index) => <li key={article.slug}><span>{String(index + 1).padStart(2, '0')}</span><article><p>{article.sourceBook.title} · {article.readingMinutes} min de leitura</p><h2><Link to={`/artigos/${article.slug}`}>{article.title}</Link></h2><p>{article.excerpt}</p></article></li>)}</ol> : null}</PublicReadingShell>
}
