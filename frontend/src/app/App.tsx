import { useState } from 'react'
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, FileText, MessageCircle, Mic, Plus, Sparkles } from 'lucide-react'
import { NeutralButton, PrimaryButton } from '@/ui/Button'
import { ToastProvider } from '@/ui/ToastProvider'
import { BookDetailPage, type WritingSummary } from '@/features/library/BookDetailPage'
import { BookFormDialog, WritingFormDialog } from '@/features/library/LibraryFormDialog'
import '@/styles/globals.css'
import './app.css'

type Screen = 'library' | 'book' | 'workspace' | 'public'
type BookSummary = { title: string; author: string; color: string; count: string }

function Brand() {
  return <span className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>Entrelinhas</span>
}

function Header({ onPublic }: { onPublic(): void }) {
  return <header className="app-header"><Brand /><div className="header-actions"><span className="budget"><i /> R$ 12,40 de R$ 70,00</span><button className="text-button" onClick={onPublic}>Ver publicação <ArrowUpRight size={15} /></button><span className="avatar">VM</span></div></header>
}

const initialBooks: BookSummary[] = [
  { title: 'Trabalho focado', author: 'Cal Newport', color: 'blue', count: '3 escritas' },
  { title: 'A vida intelectual', author: 'A. D. Sertillanges', color: 'orange', count: '2 escritas' },
  { title: 'Roube como um artista', author: 'Austin Kleon', color: 'green', count: '1 escrita' },
]

function Library({ books, onOpen, onOpenBook, onNewBook, onPublic }: { books: BookSummary[]; onOpen(): void; onOpenBook(): void; onNewBook(): void; onPublic(): void }) {
  return <div><Header onPublic={onPublic} /><main className="library" aria-label="Entrelinhas">
    <section className="library-hero"><div><span className="eyebrow">Estúdio particular</span><h1>Sua biblioteca<br />de ideias</h1><p>Livros não terminam na última página. Aqui, cada leitura continua em áudios, notas e escritas.</p></div><PrimaryButton icon={<Plus size={17} />}>Nova escrita</PrimaryButton></section>
    <section><div className="section-title"><div><small>01</small><h2>Continuar escrevendo</h2></div><button disabled>Ver todas <ChevronRight size={15} /></button></div>
      <button className="writing-card" onClick={onOpen} aria-label="Abrir Ritual antes do foco"><span className="writing-number">14</span><span className="writing-copy"><small>Trabalho focado · cap. 3–4</small><strong>Ritual antes do foco</strong><span>Por que o contexto que antecede o trabalho importa tanto quanto a técnica usada durante ele.</span><em><i /> Salvo · atualizado há 18 min</em></span><span className="mini-rail"><i /><i /><i /></span><span className="open-icon"><ArrowUpRight size={18} /></span></button>
    </section>
    <section><div className="section-title"><div><small>02</small><h2>Na estante</h2></div><NeutralButton onClick={onNewBook} icon={<Plus size={16} />}>Adicionar livro</NeutralButton></div><div className="books-grid">{books.map((book, index) => <article className="book-card" key={book.title}><div className={`book-cover ${book.color}`}><small>0{index + 1}</small><i /></div><div><h3>{book.title}</h3><p>{book.author}</p><small>{book.count}</small></div><button onClick={book.title === 'Trabalho focado' ? onOpenBook : undefined} disabled={book.title !== 'Trabalho focado'} aria-label={`Abrir ${book.title}`}><ChevronRight size={18} /></button></article>)}</div></section>
  </main></div>
}

const events = [['audio', 'Áudio'], ['prompt', 'Prompt'], ['source', 'Fonte'], ['accepted', 'Sugestão aceita']] as const

function Workspace({ onBack, onPublic }: { onBack(): void; onPublic(): void }) {
  return <div className="workspace-shell"><header className="workspace-header"><button onClick={onBack}><Brand /></button><span>Trabalho focado <ChevronRight size={13} /> <strong>Ritual antes do foco</strong></span><em><i /> Salvo</em><NeutralButton onClick={onPublic}>Publicar</NeutralButton></header>
    <main className="workspace" aria-label="Entrelinhas">
      <nav className="workspace-nav" aria-label="Contexto da escrita"><button className="back" onClick={onBack}><ArrowLeft size={15} /> Biblioteca</button><div className="context"><small>Livro</small><h2>Trabalho focado</h2><p>Cal Newport</p></div><span className="nav-label">Nesta escrita</span><button disabled className="nav-active"><FileText size={16} /> Documento</button><button disabled><MessageCircle size={16} /> Conversa <span>8</span></button><button disabled><Mic size={16} /> Áudios <span>3</span></button><button disabled><Sparkles size={16} /> Sugestões <b>2</b></button><aside className="paper-note">“A concentração começa antes de sentar.”<small>Nota da pág. 74</small></aside></nav>
      <section className="document" aria-label="Documento"><header><div><button disabled className="active">Escrever</button><button disabled>Visualizar</button></div><small>Markdown</small></header><div className="document-scroll"><aside className="margin-rail" aria-label="Linha do tempo da escrita"><span />{events.map(([tone, label], i) => <button disabled className={tone} aria-label={`${label} · 10:${i}0`} key={label}>{i === 3 ? <Check size={12} /> : i + 1}</button>)}</aside><article className="draft"><small>Rascunho 04 · 842 palavras</small><h1>Ritual antes do foco</h1><p className="lede">A capacidade de concentração não nasce no instante em que fechamos as abas. Ela começa muito antes, nos pequenos acordos que fazemos com o ambiente.</p><h2>O começo acontece antes</h2><p>Quando Newport descreve o trabalho profundo, é tentador olhar apenas para os blocos de tempo. Mas o que sustenta esses blocos é um ritual: uma sequência reconhecível que avisa ao corpo que agora existe apenas uma tarefa.</p><blockquote>O ritual não serve para controlar o dia. Serve para reduzir o número de decisões até que reste apenas o trabalho.</blockquote><p>Na prática, isso significa preparar a mesa, definir o ponto de chegada e retirar do campo de visão tudo que pede uma resposta imediata.</p></article></div></section>
      <aside className="assistant" aria-label="Assistente"><header><span><Sparkles size={16} /></span><div><h2>Assistente</h2><small>Contexto desta escrita</small></div></header><div className="messages"><article className="user-message"><small>Você</small><p>Organize a ideia do ritual sem perder o tom pessoal.</p></article><article><small>Entrelinhas</small><p>Estruturei a passagem em três movimentos: ambiente, intenção e repetição. A sugestão está pronta para comparar.</p><button disabled><Sparkles size={13} /> Ver sugestão</button></article></div><footer><button disabled aria-label="Gravar áudio"><Mic size={16} /></button><span>Faça uma pergunta ou grave uma ideia</span><button disabled aria-label="Enviar mensagem">↑</button></footer></aside>
    </main></div>
}

function PublicPage({ onBack }: { onBack(): void }) {
  return <main className="public" aria-label="Entrelinhas"><header><button onClick={onBack}><Brand /></button><span>Notas públicas de uma leitura contínua</span><button onClick={onBack}>Abrir estúdio</button></header><article className="prose"><div className="article-meta"><span>Trabalho focado</span><span>8 min de leitura</span></div><h1>Ritual antes<br />do foco</h1><p className="deck">A concentração não começa quando fechamos as abas. Ela nasce dos pequenos acordos que fazemos com o ambiente.</p><hr /><h2>O começo acontece antes</h2><p>Quando Cal Newport descreve o trabalho profundo, é tentador olhar apenas para os blocos de tempo. Mas o que sustenta esses blocos é uma sequência reconhecível que avisa ao corpo: agora existe apenas uma tarefa.</p><blockquote>O ritual reduz o número de decisões até que reste apenas o trabalho.</blockquote></article></main>
}

export function App() {
  const [screen, setScreen] = useState<Screen>('library')
  const [books, setBooks] = useState(initialBooks)
  const [writings, setWritings] = useState<WritingSummary[]>([
    { title: 'Ritual antes do foco', sourceRange: 'Capítulos 3–4', status: 'draft', updated: 'Atualizado há 18 min' },
    { title: 'Atenção como escolha', sourceRange: 'Capítulo 2', status: 'draft', updated: 'Atualizado ontem' },
    { title: 'Trabalho profundo na prática', sourceRange: 'Capítulos 5–6', status: 'published', updated: 'Publicado em 24 ago.' },
  ])
  const [bookDialog, setBookDialog] = useState(false)
  const [writingDialog, setWritingDialog] = useState(false)
  return <ToastProvider>
    {screen === 'library' ? <Library books={books} onOpen={() => setScreen('workspace')} onOpenBook={() => setScreen('book')} onNewBook={() => setBookDialog(true)} onPublic={() => setScreen('public')} /> : null}
    {screen === 'book' ? <><Header onPublic={() => setScreen('public')} /><BookDetailPage writings={writings} onBack={() => setScreen('library')} onCreateWriting={() => setWritingDialog(true)} onOpenWriting={() => setScreen('workspace')} /></> : null}
    {screen === 'workspace' ? <Workspace onBack={() => setScreen('library')} onPublic={() => setScreen('public')} /> : null}
    {screen === 'public' ? <PublicPage onBack={() => setScreen('library')} /> : null}
    <BookFormDialog open={bookDialog} onOpenChange={setBookDialog} onCreate={({ title, author }) => setBooks((current) => [...current, { title, author, color: 'orange', count: '0 escritas' }])} />
    <WritingFormDialog open={writingDialog} onOpenChange={setWritingDialog} onCreate={({ title, sourceRange }) => setWritings((current) => [...current, { title, sourceRange, status: 'draft', updated: 'Criado agora' }])} />
  </ToastProvider>
}
