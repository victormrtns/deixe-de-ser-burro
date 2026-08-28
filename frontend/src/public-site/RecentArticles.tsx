import { Link } from 'react-router-dom'
import type { PublicArticleSummary } from '@/services/contracts'

export function RecentArticles({ articles }: { articles: PublicArticleSummary[] }) {
  return <section className="editorial-section" aria-labelledby="recent-articles-title"><div className="section-heading"><p>Últimas anotações publicadas</p><h2 id="recent-articles-title">Artigos recentes</h2></div><ol className="recent-articles">{articles.map((article, index) => <li key={article.slug}><span>{String(index + 1).padStart(2, '0')}</span><article><p>{article.sourceBook.title} · {article.readingMinutes} min</p><h3><Link to={`/artigos/${article.slug}`}>{article.title}</Link></h3><p>{article.excerpt}</p></article></li>)}</ol></section>
}
