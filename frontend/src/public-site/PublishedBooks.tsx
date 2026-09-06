import type { PublicBookSummary } from '@/services/contracts'
import { PublishedBookCard } from './PublishedBookCard'

export function PublishedBooks({ books }: { books: PublicBookSummary[] }) {
  return (
    <section className="editorial-section" aria-labelledby="published-books-title">
      <div className="section-heading">
        <p>Livros que viraram escrita</p>
        <h2 id="published-books-title">Estante publicada</h2>
      </div>
      <div className="published-books">
        {books.map((book) => <PublishedBookCard key={book.slug} book={book} />)}
      </div>
    </section>
  )
}
