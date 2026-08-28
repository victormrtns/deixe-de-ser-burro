import { Link, useParams } from 'react-router-dom'
import { PublicReadingShell } from './PublicReadingShell'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { usePublicArticles, usePublicBooks } from './usePublicContent'

export function PublicBookPage() {
  const { slug = '' } = useParams()
  const books = usePublicBooks()
  const articles = usePublicArticles()
  const book = books.data?.find((item) => item.slug === slug)
  const bookArticles = articles.data?.filter((article) => article.sourceBook.slug === slug) ?? []
  useDocumentTitle(`${book?.title ?? 'Livro'} — Entrelinhas`)
  return <PublicReadingShell>{books.isLoading || articles.isLoading ? <p className="public-status" role="status">Abrindo o caderno…</p> : null}{books.error || articles.error ? <section className="public-status"><h1>Não foi possível abrir este livro.</h1><button type="button" onClick={() => { void books.mutate(); void articles.mutate() }}>Tentar novamente</button></section> : null}{book ? <><header className="book-header"><p className="editorial-kicker">Caderno de leitura</p><h1>{book.title}</h1><p>{book.author}</p><span>{book.publishedArticleCount} artigos publicados</span></header><ol className="archive-list">{bookArticles.map((article, index) => <li key={article.slug}><span>{String(index + 1).padStart(2, '0')}</span><article><p>{article.readingMinutes} min de leitura</p><h2><Link to={`/artigos/${article.slug}`}>{article.title}</Link></h2><p>{article.excerpt}</p></article></li>)}</ol></> : null}{books.data && !book ? <section className="public-status"><h1>Livro não encontrado.</h1><Link to="/livros">Voltar à estante</Link></section> : null}</PublicReadingShell>
}
