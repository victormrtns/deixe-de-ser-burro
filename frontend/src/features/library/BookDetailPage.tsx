import { useState } from 'react'
import { ArrowLeft, ArrowUpRight, BookOpen, Plus } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApi } from '@/services/api'
import type { HttpAppApi } from '@/services/contracts'
import { NeutralButton, PrimaryButton } from '@/ui/Button'
import { WritingFormDialog } from './LibraryFormDialog'
import { useBook, useBookWritings } from './useLibrary'
import { useDocumentTitle } from '@/ui/useDocumentTitle'

export function BookDetailPage() {
  const { bookId = '' } = useParams()
  const navigate = useNavigate()
  const api = useApi() as HttpAppApi
  const { data: book, error: bookError, mutate: retryBook } = useBook(bookId)
  const { data: writings, error: writingsError, mutate } = useBookWritings(bookId)
  const [dialogOpen, setDialogOpen] = useState(false)
  useDocumentTitle(`${book?.title ?? 'Livro'} — deixedeserburro`)

  if (bookError || writingsError) return <main className="book-detail"><h1>Não foi possível abrir este livro</h1><NeutralButton onClick={() => void Promise.all([retryBook(), mutate()])}>Tentar novamente</NeutralButton></main>
  if (!book || !writings) return <main className="book-detail" aria-label="Carregando livro">Abrindo livro…</main>

  return <main className="book-detail" aria-label="deixedeserburro">
    <button className="detail-back" type="button" onClick={() => navigate('/studio')}><ArrowLeft size={16} /> Biblioteca</button>
    <section className="book-hero"><div className="detail-cover"><small>01</small><i /><span /></div><div><span className="eyebrow">Livro em leitura</span><h1>{book.title}</h1><p>{book.author}</p><div className="book-facts"><span><strong>{writings.length}</strong> escritas</span></div></div></section>
    <section><div className="section-title"><div><small>01</small><h2>Escritas deste livro</h2></div><PrimaryButton onClick={() => setDialogOpen(true)} icon={<Plus size={16} />}>Nova escrita</PrimaryButton></div>
      {writings.length ? <div className="writing-list">{writings.map((writing, index) => <button type="button" className="writing-row" onClick={() => navigate(`/studio/escritas/${writing.id}`)} key={writing.id}><span className="row-index">{String(index + 1).padStart(2, '0')}</span><span><small>{writing.sourceRange}</small><h3>{writing.title}</h3><em>{new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(writing.updatedAt))}</em></span><span className={`status-chip status-chip--${writing.status}`}>{writing.status === 'draft' ? 'Rascunho' : 'Publicado'}</span><ArrowUpRight size={18} /></button>)}</div> : <div className="library-empty"><span><BookOpen size={24} /></span><h3>Nenhuma escrita ainda</h3><p>Escolha um trecho do livro para começar a pensar por escrito.</p><PrimaryButton onClick={() => setDialogOpen(true)}>Criar primeira escrita</PrimaryButton></div>}
    </section>
    <WritingFormDialog open={dialogOpen} onOpenChange={setDialogOpen} onCreate={async (values, key) => { const created = await api.writings.create(bookId, values, key); await mutate(); navigate(`/studio/escritas/${created.id}`) }} />
  </main>
}
