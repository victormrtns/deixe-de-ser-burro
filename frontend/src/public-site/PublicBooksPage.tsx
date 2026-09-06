import type { PublicBookSummary } from '@/services/contracts'
import { PublicReadingShell } from './PublicReadingShell'
import { PrimaryButton } from '@/ui/Button'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { PublishedBooks } from './PublishedBooks'
import { usePublicBooks } from './usePublicContent'

function PublishedBooksSection({ books }: { books: PublicBookSummary[] }) {
  if (books.length === 0) return <section className="public-status public-status--empty"><h2>Nenhum livro chegou à parte pública.</h2><p>Um livro aparece aqui quando ganha o primeiro artigo publicado.</p></section>
  return <PublishedBooks books={books} />
}

export function PublicBooksPage() {
  useDocumentTitle('Livros — deixedeserburro')
  const { data: books, error, isLoading, mutate } = usePublicBooks()
  return <PublicReadingShell><header className="archive-header"><p className="editorial-kicker">Estante publicada</p><h1>Livros</h1><p>Livros que já deram origem a artigos públicos.</p></header>{isLoading ? <p className="public-status" role="status">Abrindo a estante…</p> : null}{error ? <section className="public-status"><h2>Não foi possível abrir os livros.</h2><PrimaryButton onClick={() => void mutate()}>Tentar novamente</PrimaryButton></section> : null}{books ? <PublishedBooksSection books={books.filter((book) => book.publishedArticleCount > 0)} /> : null}</PublicReadingShell>
}
