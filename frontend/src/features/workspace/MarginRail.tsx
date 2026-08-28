import { MessageCircle, Mic, Sparkles } from 'lucide-react'
const events = [{ label: 'Áudio da ideia inicial', Icon: Mic, tone: 'audio' }, { label: 'Pergunta ao assistente', Icon: MessageCircle, tone: 'prompt' }, { label: 'Sugestão aceita', Icon: Sparkles, tone: 'accepted' }]
export function MarginRail() { return <aside className="workspace-margin-rail" aria-label="Linha do tempo da escrita">{events.map(({ label, Icon, tone }) => <button type="button" disabled className={`margin-event margin-event--${tone}`} aria-label={label} key={label}><Icon size={13} /></button>)}</aside> }
