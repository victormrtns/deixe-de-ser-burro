import { useState, type FormEvent } from 'react'
import { LockKeyhole } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '@/services/httpApi'
import { Field } from '@/ui/Field'
import { PrimaryButton } from '@/ui/Button'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { useSession } from './SessionProvider'

interface SignInLocationState {
  from?: { pathname: string; search?: string; hash?: string }
}

export function SignInPage() {
  useDocumentTitle('Entrar — deixedeserburro')
  const { actions } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string>()
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError(undefined)
    setIsSubmitting(true)
    try {
      await actions.signIn(String(form.get('email') ?? ''), String(form.get('password') ?? ''))
      const destination = (location.state as SignInLocationState | null)?.from
      await navigate(destination ?? '/studio', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError && caught.code === 'invalid_credentials'
        ? 'E-mail ou senha inválidos.'
        : 'Não foi possível entrar. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return <main className="sign-in" aria-label="deixedeserburro"><section><img className="sign-in-logo" src="/brand/logo.svg" alt="deixedeserburro" width={340} height={104} /><span className="sign-in-mark"><LockKeyhole size={20} /></span><span className="eyebrow">Estúdio particular</span><h1>Volte ao seu caderno</h1><p>Entre para continuar uma leitura, recuperar uma ideia ou publicar uma escrita.</p><form noValidate onSubmit={submit}><Field label="E-mail" name="email" type="email" autoComplete="username" /><Field label="Senha" name="password" type="password" autoComplete="current-password" {...(error ? { error } : {})} /><PrimaryButton type="submit" busy={isSubmitting}>Entrar no estúdio</PrimaryButton></form></section><aside aria-hidden="true"><span>deixedeser</span><span>burro</span><i /></aside></main>
}
