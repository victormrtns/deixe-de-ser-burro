import useSWR from 'swr'
import { useApi } from '@/services/api'
import type { HttpAppApi } from '@/services/contracts'
import { useWorkspace } from './WorkspaceProvider'

export function VersionHistory({ writingId }: { writingId: string }) {
  const api = useApi() as HttpAppApi
  const { actions } = useWorkspace()
  const { data, error, mutate } = useSWR(`writings/${writingId}/versions`, () => api.writings.listVersions(writingId))
  return <details className="version-history"><summary>Histórico de versões</summary>
    {error ? <p>Não foi possível carregar o histórico. <button onClick={() => void mutate()}>Tentar novamente</button></p> : null}
    {!data ? <p>Carregando versões…</p> : null}
    {data?.items.map((version) => <div key={version.version}><span>Versão {version.version}</span><small>{new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(version.createdAt))}</small><button type="button" onClick={() => void actions.restoreVersion(version.version)}>Restaurar</button></div>)}
  </details>
}
