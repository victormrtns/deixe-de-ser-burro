import { lazy, Suspense } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PublicReadingShell } from './PublicReadingShell'
import { usePublicArticle } from './usePublicContent'

const MarkdownPreview = lazy(() => import('@/features/workspace/MarkdownPreview').then((module) => ({ default: module.MarkdownPreview })))

export function PublicArticlePage() {
  const { slug = 'ritual-antes-do-foco' } = useParams()
  const { data: article, error, isLoading, mutate } = usePublicArticle(slug)
  useDocumentTitle(`${article?.title ?? 'Artigo'} — Entrelinhas`)
  return <PublicReadingShell>{isLoading ? <p className="public-status" role="status">Abrindo o ensaio…</p> : null}{error ? <section className="public-status"><h1>Artigo não encontrado.</h1><button type="button" onClick={() => void mutate()}>Tentar novamente</button><Link to="/artigos">Voltar ao arquivo</Link></section> : null}{article ? <article className="prose public-article"><div className="article-meta"><Link to={`/livros/${article.sourceBook.slug}`}>{article.sourceBook.title}</Link><span>{article.readingMinutes} min de leitura</span></div><Suspense fallback={<p role="status">Preparando a leitura…</p>}><MarkdownPreview markdown={article.markdown} /></Suspense></article> : null}</PublicReadingShell>
}
