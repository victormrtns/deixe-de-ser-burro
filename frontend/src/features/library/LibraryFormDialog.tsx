import * as DialogPrimitive from '@radix-ui/react-dialog'
import { useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import { Field } from '@/ui/Field'
import { GhostButton, PrimaryButton } from '@/ui/Button'

type BookValues = { title: string; author: string }
type WritingValues = { title: string; sourceRange: string }

type SharedProps = {
  open: boolean
  onOpenChange(open: boolean): void
}

function Frame({ open, onOpenChange, title, description, children }: SharedProps & { title: string; description: string; children: React.ReactNode }) {
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}><DialogPrimitive.Portal><DialogPrimitive.Overlay className="dialog__overlay" /><DialogPrimitive.Content className="dialog library-dialog"><button className="dialog-close" type="button" onClick={() => onOpenChange(false)} aria-label="Fechar"><X size={18} /></button><span className="eyebrow">Novo começo</span><DialogPrimitive.Title className="dialog__title">{title}</DialogPrimitive.Title><DialogPrimitive.Description className="dialog__description">{description}</DialogPrimitive.Description>{children}</DialogPrimitive.Content></DialogPrimitive.Portal></DialogPrimitive.Root>
}

export function BookFormDialog({ open, onOpenChange, onCreate }: SharedProps & { onCreate(values: BookValues): void }) {
  const [error, setError] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const title = String(data.get('title') ?? '').trim()
    const author = String(data.get('author') ?? '').trim()
    if (!title) { setError('Informe um título.'); return }
    onCreate({ title, author: author || 'Autor não informado' }); setError(''); onOpenChange(false)
  }
  return <Frame open={open} onOpenChange={onOpenChange} title="Adicionar livro" description="Crie um lugar para reunir as escritas de uma leitura."><form noValidate onSubmit={submit} className="dialog-form"><Field autoFocus label="Título" name="title" {...(error ? { error } : {})} /><Field label="Autor" name="author" /><div className="dialog__actions"><GhostButton type="button" onClick={() => onOpenChange(false)}>Cancelar</GhostButton><PrimaryButton type="submit">Adicionar à estante</PrimaryButton></div></form></Frame>
}

export function WritingFormDialog({ open, onOpenChange, onCreate }: SharedProps & { onCreate(values: WritingValues): void }) {
  const [error, setError] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const title = String(data.get('title') ?? '').trim()
    const sourceRange = String(data.get('sourceRange') ?? '').trim()
    if (!title) { setError('Informe um título.'); return }
    onCreate({ title, sourceRange: sourceRange || 'Trecho livre' }); setError(''); onOpenChange(false)
  }
  return <Frame open={open} onOpenChange={onOpenChange} title="Nova escrita" description="Defina um recorte. Você poderá ampliá-lo conforme as ideias avançarem."><form noValidate onSubmit={submit} className="dialog-form"><Field autoFocus label="Título" name="title" {...(error ? { error } : {})} /><Field label="Trecho coberto" name="sourceRange" description="Por exemplo: capítulos 3–4 ou páginas 72–96." /><div className="dialog__actions"><GhostButton type="button" onClick={() => onOpenChange(false)}>Cancelar</GhostButton><PrimaryButton type="submit">Criar escrita</PrimaryButton></div></form></Frame>
}
