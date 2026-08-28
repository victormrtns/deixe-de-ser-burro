import { Link, useParams } from 'react-router-dom'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PublicReadingShell } from './PublicReadingShell'
import { usePublicArticles } from './usePublicContent'

export function PublicArticlePage() {
  const { slug = 'ritual-antes-do-foco' } = useParams()
  const { data: articles, error, isLoading, mutate } = usePublicArticles()
  const article = articles?.find((item) => item.slug === slug)
  useDocumentTitle(`${article?.title ?? 'Artigo'} — Entrelinhas`)
  return <PublicReadingShell>{isLoading ? <p className="public-status" role="status">Abrindo o ensaio…</p> : null}{error ? <section className="public-status"><h1>Não foi possível abrir este artigo.</h1><button type="button" onClick={() => void mutate()}>Tentar novamente</button></section> : null}{article ? <article className="prose public-article"><div className="article-meta"><Link to={`/livros/${article.sourceBook.slug}`}>{article.sourceBook.title}</Link><span>{article.readingMinutes} min de leitura</span></div><h1>{article.title}</h1><p className="deck">{article.excerpt}</p><hr /><h2>O começo acontece antes</h2><p>Algumas ideias pedem tempo depois que a leitura termina. Voltamos a elas não para resumir o livro, mas para descobrir o que ele deslocou em nossa maneira de olhar.</p><blockquote>A leitura continua quando uma pergunta encontra espaço para amadurecer.</blockquote><h2>Uma nota que virou ensaio</h2><p>Este texto nasceu de anotações à margem, conexões refeitas e uma tentativa de dar forma pública ao que ainda estava em movimento.</p></article> : null}{articles && !article ? <section className="public-status"><h1>Artigo não encontrado.</h1><Link to="/artigos">Voltar ao arquivo</Link></section> : null}</PublicReadingShell>
}
