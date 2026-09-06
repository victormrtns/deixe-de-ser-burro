export type WritingStatus = 'draft' | 'published' | 'cleanup_scheduled'
export type JobStatus = 'queued' | 'uploading' | 'transcribing' | 'analyzing' | 'ready' | 'failed'
export type SuggestionStatus = 'pending' | 'accepted' | 'rejected'
export type LimitState = 'normal' | 'near_limit' | 'blocked'

export interface Book { id: string; title: string; author: string; coverUrl?: string; writingCount: number }
export interface Writing { id: string; bookId: string; title: string; markdown: string; sourceRange: string; status: WritingStatus; version: number; updatedAt: string }
export type MessageState = 'streaming' | 'completed' | 'interrupted' | 'failed'
export type MemoryKind = 'preference' | 'decision' | 'open_question'
export interface Message { id: string; writingId: string; role: 'author' | 'assistant'; content: string; state: MessageState; createdAt: string }
export interface MemoryItem { id: string; kind: MemoryKind; content: string; createdAt: string }
export interface AudioClip { id: string; writingId: string; title: string; status: JobStatus; durationSeconds: number }
export interface Suggestion { id: string; writingId: string; summary: string; before: string; after: string; status: SuggestionStatus }
export interface UsageSummary { period: string; spentUsdMicros: number; reservedUsdMicros: number; limitUsdMicros: number; limitState: LimitState }
export interface GenerationUsage { inputTokens: number; outputTokens: number; totalTokens: number; estimatedCostUsdMicros: number; budgetState: LimitState }
export interface WorkspacePayload { writing: Writing; messages: Message[]; audio: AudioClip[]; suggestions: Suggestion[] }

interface ConversationEventBase { id: string; writingId: string; createdAt: string; status: 'pending' | 'ready' | 'failed' }
export type ConversationEvent =
  | (ConversationEventBase & { type: 'author_text'; content: string })
  | (ConversationEventBase & { type: 'author_link'; url: string; title?: string; summary?: string })
  | (ConversationEventBase & { type: 'author_audio'; title: string; durationSeconds?: number; localPreviewUrl?: string })
  | (ConversationEventBase & { type: 'transcript'; audioEventId: string; content: string })
  | (ConversationEventBase & { type: 'assistant_text'; content: string; partial: boolean })
  | (ConversationEventBase & { type: 'suggestion'; suggestionId: string; summary: string })

export interface PublicArticleSummary {
  slug: string
  title: string
  excerpt: string
  publishedAt: string
  readingMinutes: number
  coverImageUrl?: string
  sourceBook: { slug: string; title: string; author: string }
}

export interface PublicBookSummary {
  slug: string
  title: string
  author: string
  coverImageUrl?: string
  publishedArticleCount: number
  latestArticle: Pick<PublicArticleSummary, 'slug' | 'title' | 'publishedAt'>
  publicTopics: string[]
}

export interface PublicLanding {
  featuredArticle: PublicArticleSummary | null
  recentArticles: PublicArticleSummary[]
  publishedBooks: PublicBookSummary[]
}

export interface ApiErrorShape {
  code: string
  message: string
  details?: Record<string, unknown>
  requestId: string
}

export type AuthSession = { state: 'anonymous' } | { state: 'author'; author: { email: string } }

export interface AuthApi {
  getSession(): Promise<AuthSession>
  signIn(email: string, password: string): Promise<AuthSession>
  signOut(): Promise<void>
}

export interface WritingVersion {
  version: number
  title: string
  sourceRange: string
  markdown: string
  reason: 'created' | 'manual_save' | 'restored' | 'published'
  createdAt: string
}

export interface WritingVersionPage { items: WritingVersion[]; nextCursor: string | null }

export interface PublicationStatus {
  slug: string
  state: 'published' | 'withdrawn'
  publishedAt: string
  cleanupAt: string
  cleanupCancelledAt: string | null
  cleanupCompletedAt: string | null
}

export interface PublicArticleDetail extends PublicArticleSummary { markdown: string }
export interface PublicBookDetail extends PublicBookSummary { articles: PublicArticleSummary[] }

export interface BooksApi {
  list(): Promise<Book[]>
  create(input: Pick<Book, 'title' | 'author'>, idempotencyKey?: string): Promise<Book>
  get(id: string): Promise<Book>
  update(id: string, input: Partial<Pick<Book, 'title' | 'author'>>): Promise<Book>
  remove(id: string): Promise<void>
}
export interface WritingsApi {
  getWorkspace(id: string): Promise<WorkspacePayload>
  save(input: { id: string; markdown: string; expectedVersion: number }): Promise<Writing>
  create(
    bookId: string,
    input: { title: string; sourceRange: string; markdown?: string },
    idempotencyKey?: string,
  ): Promise<Writing>
  listByBook(bookId: string): Promise<Writing[]>
  get(id: string): Promise<Writing>
  updateMetadata(input: { id: string; expectedVersion: number; title?: string; sourceRange?: string }): Promise<Writing>
  remove(id: string): Promise<void>
  listVersions(id: string, cursor?: string): Promise<WritingVersionPage>
  restoreVersion(input: { id: string; versionNumber: number; expectedVersion: number }): Promise<Writing>
}
export type ChatStreamEvent =
  | { type: 'generation.started'; version: 1; attemptId: string; sequence: number; messageId: string; attemptNumber: number }
  | { type: 'response.delta'; version: 1; attemptId: string; sequence: number; delta: string }
  | { type: 'response.completed'; version: 1; attemptId: string; sequence: number; usage: GenerationUsage }
  | { type: 'response.interrupted'; version: 1; attemptId: string; sequence: number }
  | { type: 'response.failed'; version: 1; attemptId: string; sequence: number; error: ApiErrorShape }

export type ChatStreamListener = (event: ChatStreamEvent) => void

export interface ChatApi {
  list(writingId: string): Promise<Message[]>
  streamReply(writingId: string, content: string, idempotencyKey: string, signal: AbortSignal, onEvent: ChatStreamListener): Promise<void>
  retry(writingId: string, messageId: string, idempotencyKey: string, signal: AbortSignal, onEvent: ChatStreamListener): Promise<void>
  remember(writingId: string, input: { kind: MemoryKind; content: string; sourceMessageId?: string }): Promise<MemoryItem>
  getUsage(writingId: string): Promise<UsageSummary>
}
export interface AudioApi { list(writingId: string): Promise<AudioClip[]> }
export interface SuggestionsApi { list(writingId: string): Promise<Suggestion[]> }
export interface PublishingApi {
  publish(writingId: string, idempotencyKey?: string): Promise<{ slug: string; publishedAt: string; cleanupAt: string }>
  getStatus(writingId: string): Promise<PublicationStatus>
  cancelCleanup(writingId: string): Promise<PublicationStatus>
  unpublish(writingId: string): Promise<PublicationStatus>
}
export interface UsageApi { getSummary(): Promise<UsageSummary> }
export interface PublicApi {
  getLanding(): Promise<PublicLanding>
  listArticles(): Promise<PublicArticleSummary[]>
  listBooks(): Promise<PublicBookSummary[]>
  getArticle(slug: string): Promise<PublicArticleDetail>
  getBook(slug: string): Promise<PublicBookDetail>
}

export interface AppApi {
  auth: AuthApi
  books: BooksApi
  writings: WritingsApi
  chat: ChatApi
  audio: AudioApi
  suggestions: SuggestionsApi
  publishing: PublishingApi
  usage: UsageApi
  public: PublicApi
}

// Alias transitório: features/workspace ainda importa este nome em outra branch.
// Remover quando aquela branch encostar.
export type HttpAppApi = AppApi
