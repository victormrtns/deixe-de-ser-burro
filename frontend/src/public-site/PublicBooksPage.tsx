import { PublicReadingShell } from './PublicReadingShell'
import { PrimaryButton } from '@/ui/Button'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PublishedBooks } from './PublishedBooks'
import { usePublicBooks } from './usePublicContent'

export function PublicBooksPage() {
  useDocumentTitle('Livros — deixedeserburro')
  const { data: books, error, isLoading, mutate } = usePublicBooks()

  return (
    <PublicReadingShell>
      <header className="archive-header">
        <p className="editorial-kicker">Estante publicada</p>
        <h1>Livros</h1>
        <p>Livros que já deram origem a artigos públicos.</p>
      </header>
      {isLoading ? <p className="public-status" role="status">Abrindo a estante…</p> : null}
      {error ? (
        <section className="public-status">
          <h2>Não foi possível abrir os livros.</h2>
          <PrimaryButton onClick={() => void mutate()}>Tentar novamente</PrimaryButton>
        </section>
      ) : null}
      {books ? <PublishedBooks books={books.filter((book) => book.publishedArticleCount > 0)} /> : null}
    </PublicReadingShell>
  )
}
