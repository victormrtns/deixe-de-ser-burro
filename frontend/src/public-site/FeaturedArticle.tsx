import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { PublicArticleSummary } from '@/services/contracts'

function formatDate(value: string) {
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(value))
}

export function FeaturedArticle({ article }: { article: PublicArticleSummary }) {
  return <article className="featured-article"><div className="featured-article__mark" aria-hidden="true"><span>ler</span><i /></div><div className="featured-article__content"><p className="editorial-kicker">Em destaque · {formatDate(article.publishedAt)}</p><p className="featured-article__source">{article.sourceBook.title}<span>— {article.sourceBook.author}</span></p><h2><Link to={`/artigos/${article.slug}`}>{article.title}</Link></h2><p>{article.excerpt}</p><span className="reading-time">{article.readingMinutes} min de leitura</span><Link className="editorial-link" to={`/artigos/${article.slug}`}>Continuar lendo <ArrowUpRight size={17} aria-hidden="true" /></Link></div></article>
}
