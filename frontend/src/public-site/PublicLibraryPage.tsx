import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PrimaryButton } from '@/ui/Button'
import { FeaturedArticle } from './FeaturedArticle'
import { PublishedBooks } from './PublishedBooks'
import { PublicArchive } from './PublicArchive'
import { PublicReadingShell } from './PublicReadingShell'
import { RecentArticles } from './RecentArticles'
import { usePublicLanding } from './usePublicContent'

export function PublicLibraryPage() {
  useDocumentTitle('deixedeserburro — Leituras que continuam')
  const { data, error, isLoading, mutate } = usePublicLanding()

  return <PublicReadingShell><section className="landing-intro"><p className="editorial-kicker">Caderno público de leitura</p><h1>Ideias que continuam<br />depois da última página.</h1><p>Ensaios nascidos do encontro entre livros, anotações e tempo.</p></section>{isLoading && <p className="public-status" role="status">Abrindo a estante…</p>}{error && <section className="public-status"><h2>Não foi possível abrir a estante.</h2><PrimaryButton onClick={() => void mutate()}>Tentar novamente</PrimaryButton></section>}{data && !data.featuredArticle && data.recentArticles.length === 0 && data.publishedBooks.length === 0 && <section className="public-status public-status--empty"><p className="editorial-kicker">Primeiro capítulo</p><h2>Os primeiros ensaios ainda estão sendo preparados.</h2><p>Quando uma leitura virar texto público, ela aparece aqui.</p></section>}{data?.featuredArticle && <FeaturedArticle article={data.featuredArticle} />}{data && data.recentArticles.length > 0 && <RecentArticles articles={data.recentArticles} />}{data && data.publishedBooks.length > 0 && <PublishedBooks books={data.publishedBooks} />}{data && (data.recentArticles.length > 0 || data.publishedBooks.length > 0) && <PublicArchive />}</PublicReadingShell>
}
