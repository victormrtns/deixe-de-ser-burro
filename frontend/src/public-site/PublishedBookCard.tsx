import { Link } from 'react-router-dom'
import type { PublicBookSummary } from '@/services/contracts'

export function PublishedBookCard({ book }: { book: PublicBookSummary }) {
  return <article className="published-book"><Link to={`/livros/${book.slug}`} aria-label={`Explorar artigos de ${book.title}`}>{book.coverImageUrl ? <img src={book.coverImageUrl} alt={`Capa de ${book.title}`} /> : <div className="published-book__cover" aria-hidden="true"><small>{book.author}</small><strong>{book.title}</strong><span>Entrelinhas</span></div>}<div className="published-book__copy"><p>{book.author}</p><h3>{book.title}</h3><span>{book.publishedArticleCount} artigos publicados</span><small>Mais recente</small><strong>{book.latestArticle.title}</strong></div></Link></article>
}
