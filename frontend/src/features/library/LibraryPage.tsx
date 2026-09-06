import { useState } from 'react'
import { ChevronRight, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '@/services/api'
import { NeutralButton } from '@/ui/Button'
import { useToast } from '@/ui/ToastProvider'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { BookFormDialog } from './LibraryFormDialog'
import { useBooks } from './useLibrary'
import { useSession } from '@/features/auth/SessionProvider'
import '@/app/app.css'

export function LibraryPage() {
  useDocumentTitle('Biblioteca — deixedeserburro')
  const api = useApi()
  const navigate = useNavigate()
  const { data: books, error, isLoading, mutate } = useBooks()
  const [dialogOpen, setDialogOpen] = useState(false)
  const { state: session, actions: sessionActions } = useSession()
  const { notify } = useToast()

  return (
    <>
      <header className="app-header">
        <span className="brand">
          <img src="/favicon.svg" alt="" width={30} height={30} />
          <img className="brand__wordmark" src="/brand/wordmark.svg" alt="deixedeserburro" width={176} height={30} />
        </span>
        <div className="header-actions">
          <span>{session.status === 'author' ? session.email : ''}</span>
          <button type="button" className="text-button" onClick={() => void sessionActions.signOut().then(() => navigate('/'))}>Sair</button>
        </div>
      </header>
      <main className="library" aria-label="deixedeserburro">
        <section className="library-hero">
          <div>
            <span className="eyebrow">Estúdio particular</span>
            <h1>Sua biblioteca<br />de ideias</h1>
            <p>Livros não terminam na última página. Aqui, cada leitura continua em notas e escritas.</p>
          </div>
        </section>
        <section>
          <div className="section-title">
            <div>
              <small>01</small>
              <h2>Na estante</h2>
            </div>
            <NeutralButton onClick={() => setDialogOpen(true)} icon={<Plus size={16} />}>Adicionar livro</NeutralButton>
          </div>
          {isLoading ? <div className="library-empty" aria-label="Carregando biblioteca">Abrindo a estante…</div> : null}
          {error ? (
            <div className="library-empty">
              <h3>Não foi possível carregar a biblioteca</h3>
              <NeutralButton onClick={() => void mutate()}>Tentar novamente</NeutralButton>
            </div>
          ) : null}
          {books && books.length === 0 ? (
            <div className="library-empty">
              <h3>Sua estante está vazia</h3>
              <p>Adicione o primeiro livro para começar uma escrita.</p>
              <NeutralButton onClick={() => setDialogOpen(true)}>Adicionar livro</NeutralButton>
            </div>
          ) : null}
          {books?.length ? (
            <div className="books-grid">
              {books.map((book, index) => (
                <article className="book-card" key={book.id}>
                  <div className="book-cover blue">
                    <small>{String(index + 1).padStart(2, '0')}</small>
                    <i />
                  </div>
                  <div>
                    <h3>{book.title}</h3>
                    <p>{book.author}</p>
                    <small>{book.writingCount} {book.writingCount === 1 ? 'escrita' : 'escritas'}</small>
                  </div>
                  <button type="button" onClick={() => navigate(`/studio/livros/${book.id}`)} aria-label={`Abrir ${book.title}`}><ChevronRight size={18} /></button>
                </article>
              ))}
            </div>
          ) : null}
        </section>
        <BookFormDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onCreate={async (values, key) => {
            await api.books.create(values, key)
            await mutate()
            notify(`“${values.title}” entrou na estante.`, 'success')
          }}
        />
      </main>
    </>
  )
}
