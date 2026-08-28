import { ChatProvider, type StreamReply } from './ChatProvider'
import { MessageList } from './MessageList'
import { PromptComposer } from './PromptComposer'
import { Recorder } from '@/features/audio/Recorder'
import { useChat } from './ChatProvider'
import './chat.css'
import './multimodal.css'

function ChatContent({ getUserMedia }: { getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream> }) {
  const { addAudio } = useChat()
  return <section className="chat-frame" aria-label="Conversa sobre a escrita"><header><span className="eyebrow">Assistente de margem</span><h2>Pense junto com suas notas</h2></header><MessageList /><div className="multimodal-composer"><PromptComposer /><Recorder {...(getUserMedia ? { getUserMedia } : {})} onReady={() => addAudio('Nota de áudio')} /></div></section>
}

export function ChatPanel({ stream, getUserMedia }: { stream: StreamReply; getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream> }) {
  return <ChatProvider stream={stream}><ChatContent {...(getUserMedia ? { getUserMedia } : {})} /></ChatProvider>
}
