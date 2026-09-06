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
  const recentArticles = data?.recentArticles ?? []
  const publishedBooks = data?.publishedBooks ?? []
  const isEmpty = data ? !data.featuredArticle && recentArticles.length === 0 && publishedBooks.length === 0 : false

  return (
    <PublicReadingShell>
      <section className="landing-intro">
        <p className="editorial-kicker">Caderno público de leitura</p>
        <h1>Ideias que continuam<br />depois da última página.</h1>
        <p>Ensaios nascidos do encontro entre livros, anotações e tempo.</p>
      </section>
      {isLoading && <p className="public-status" role="status">Abrindo a estante…</p>}
      {error && (
        <section className="public-status">
          <h2>Não foi possível abrir a estante.</h2>
          <PrimaryButton onClick={() => void mutate()}>Tentar novamente</PrimaryButton>
        </section>
      )}
      {isEmpty && (
        <section className="public-status public-status--empty">
          <p className="editorial-kicker">Primeiro capítulo</p>
          <h2>Os primeiros ensaios ainda estão sendo preparados.</h2>
          <p>Quando uma leitura virar texto público, ela aparece aqui.</p>
        </section>
      )}
      {data?.featuredArticle && <FeaturedArticle article={data.featuredArticle} />}
      {recentArticles.length > 0 && <RecentArticles articles={recentArticles} />}
      {publishedBooks.length > 0 && <PublishedBooks books={publishedBooks} />}
      {(recentArticles.length > 0 || publishedBooks.length > 0) && <PublicArchive />}
    </PublicReadingShell>
  )
}
