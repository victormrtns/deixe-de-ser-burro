export type AudioStage = 'uploading' | 'queued' | 'transcribing' | 'organizing' | 'ready' | 'failed'

const labels: Record<AudioStage, string> = {
  uploading: 'Enviando',
  queued: 'Na fila',
  transcribing: 'Transcrevendo',
  organizing: 'Organizando',
  ready: 'Sugestão pronta',
  failed: 'Falha no processamento',
}

export function AudioJobCard({ title, stage, onRetry }: { title: string; stage: AudioStage; onRetry?: () => void }) {
  return (
    <article className="audio-job">
      <span className={`audio-stage audio-stage--${stage}`} aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{labels[stage]}</p>
      </div>
      {stage === 'failed' && onRetry && <button type="button" className="text-action" onClick={onRetry}>Tentar novamente</button>}
    </article>
  )
}
