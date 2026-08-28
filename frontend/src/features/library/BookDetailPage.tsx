import { ArrowLeft, ArrowUpRight, BookOpen, MoreHorizontal, Plus } from 'lucide-react'
import { NeutralButton, PrimaryButton } from '@/ui/Button'

export type WritingSummary = { title: string; sourceRange: string; status: 'draft' | 'published'; updated: string }

type Props = { writings: WritingSummary[]; onBack(): void; onCreateWriting(): void; onOpenWriting(title: string): void }

export function BookDetailPage({ writings, onBack, onCreateWriting, onOpenWriting }: Props) {
  return <main className="book-detail" aria-label="Entrelinhas">
    <button className="detail-back" type="button" onClick={onBack}><ArrowLeft size={16} /> Biblioteca</button>
    <section className="book-hero">
      <div className="detail-cover"><small>01</small><i /><span /></div>
      <div><span className="eyebrow">Livro em leitura</span><h1>Trabalho focado</h1><p>Cal Newport</p><div className="book-facts"><span><strong>{writings.length}</strong> escritas</span><span><strong>2</strong> áudios</span><span><strong>1</strong> publicação</span></div></div>
      <NeutralButton disabled icon={<MoreHorizontal size={17} />}>Opções</NeutralButton>
    </section>
    <section>
      <div className="section-title"><div><small>01</small><h2>Escritas deste livro</h2></div><PrimaryButton onClick={onCreateWriting} icon={<Plus size={16} />}>Nova escrita</PrimaryButton></div>
      {writings.length ? <div className="writing-list">{writings.map((writing, index) => <button type="button" className="writing-row" onClick={() => onOpenWriting(writing.title)} key={writing.title}><span className="row-index">{String(index + 1).padStart(2, '0')}</span><span><small>{writing.sourceRange}</small><h3>{writing.title}</h3><em>{writing.updated}</em></span><span className={`status-chip status-chip--${writing.status}`}>{writing.status === 'draft' ? 'Rascunho' : 'Publicado'}</span><ArrowUpRight size={18} /></button>)}</div> : <div className="library-empty"><span><BookOpen size={24} /></span><h3>Nenhuma escrita ainda</h3><p>Escolha um trecho do livro para começar a pensar por escrito.</p><PrimaryButton onClick={onCreateWriting}>Criar primeira escrita</PrimaryButton></div>}
    </section>
  </main>
}
