import { LockKeyhole } from 'lucide-react'
import { Field } from '@/ui/Field'
import { PrimaryButton } from '@/ui/Button'
import { useDocumentTitle } from '@/ui/useDocumentTitle'

export function SignInPage() {
  useDocumentTitle('Entrar — Entrelinhas')
  return <main className="sign-in" aria-label="Entrelinhas"><section><span className="sign-in-mark"><LockKeyhole size={20} /></span><span className="eyebrow">Estúdio particular</span><h1>Volte ao seu caderno</h1><p>Entre para continuar uma leitura, recuperar uma ideia ou publicar uma escrita.</p><form noValidate><Field label="E-mail" name="email" type="email" autoComplete="username" /><Field label="Senha" name="password" type="password" autoComplete="current-password" /><PrimaryButton type="submit">Entrar no estúdio</PrimaryButton></form></section><aside aria-hidden="true"><span>Entre</span><span>linhas</span><i /></aside></main>
}
