import type { PublicArticleSummary, PublicBookSummary, PublicLanding, UsageSummary, WorkspacePayload } from '@/services/contracts'

export const workspaceFixture: WorkspacePayload = {
  writing: { id: 'writing-deep-work-01', bookId: 'book-deep-work', title: 'Ritual antes do foco', markdown: '# Ritual antes do foco', sourceRange: 'Capítulos 3–4', status: 'draft', version: 4, updatedAt: '2026-08-28T10:21:00-03:00' },
  messages: [{ id: 'message-01', writingId: 'writing-deep-work-01', role: 'author', content: 'Organize esta ideia.', state: 'completed', createdAt: '2026-08-28T10:10:00-03:00' }],
  audio: [{ id: 'audio-01', writingId: 'writing-deep-work-01', title: 'Ideia sobre o ritual', status: 'ready', durationSeconds: 214 }],
  suggestions: [{ id: 'suggestion-01', writingId: 'writing-deep-work-01', summary: 'Uma explicação mais linear', before: 'O foco começa.', after: 'O foco começa antes do trabalho.', status: 'pending' }],
}

export const usageFixtures: Record<'normal' | 'near-limit' | 'blocked', UsageSummary> = {
  normal: { period: '2026-08', spentUsdMicros: 120_000, reservedUsdMicros: 0, limitUsdMicros: 2_000_000, limitState: 'normal' },
  'near-limit': { period: '2026-08', spentUsdMicros: 1_700_000, reservedUsdMicros: 40_000, limitUsdMicros: 2_000_000, limitState: 'near_limit' },
  blocked: { period: '2026-08', spentUsdMicros: 2_000_000, reservedUsdMicros: 0, limitUsdMicros: 2_000_000, limitState: 'blocked' },
}

export const publicArticleFixtures: PublicArticleSummary[] = [
  { slug: 'ritual-antes-do-foco', title: 'Ritual antes do foco', excerpt: 'Sobre ambiente, intenção e os pequenos acordos que antecedem a concentração.', publishedAt: '2026-08-24T09:00:00-03:00', readingMinutes: 8, sourceBook: { slug: 'trabalho-focado', title: 'Trabalho focado', author: 'Cal Newport' } },
  { slug: 'o-trabalho-que-nos-desvia', title: 'O trabalho que nos desvia de nós', excerpt: 'Quando ocupar o dia deixa pouco espaço para aquilo que realmente importa.', publishedAt: '2026-08-22T09:00:00-03:00', readingMinutes: 15, sourceBook: { slug: 'trabalho-focado', title: 'Trabalho focado', author: 'Cal Newport' } },
  { slug: 'profundidade-e-uma-escolha', title: 'Profundidade é uma escolha', excerpt: 'A atenção como prática deliberada, não como traço de personalidade.', publishedAt: '2026-08-18T09:00:00-03:00', readingMinutes: 11, sourceBook: { slug: 'trabalho-focado', title: 'Trabalho focado', author: 'Cal Newport' } },
  { slug: 'a-coragem-de-nao-ter-controle', title: 'A coragem de não ter tudo sob controle', excerpt: 'Notas sobre autonomia, expectativa e a liberdade de desagradar.', publishedAt: '2026-08-20T09:00:00-03:00', readingMinutes: 14, sourceBook: { slug: 'a-coragem-de-nao-agradar', title: 'A coragem de não agradar', author: 'Ichiro Kishimi e Fumitake Koga' } },
  { slug: 'separar-tarefas', title: 'Separar tarefas para viver melhor', excerpt: 'Uma fronteira simples para relações menos governadas por aprovação.', publishedAt: '2026-08-16T09:00:00-03:00', readingMinutes: 9, sourceBook: { slug: 'a-coragem-de-nao-agradar', title: 'A coragem de não agradar', author: 'Ichiro Kishimi e Fumitake Koga' } },
  { slug: 'liberdade-e-pertencimento', title: 'Liberdade sem romper o pertencimento', excerpt: 'Como sustentar escolhas próprias sem abandonar o vínculo com os outros.', publishedAt: '2026-08-12T09:00:00-03:00', readingMinutes: 12, sourceBook: { slug: 'a-coragem-de-nao-agradar', title: 'A coragem de não agradar', author: 'Ichiro Kishimi e Fumitake Koga' } },
]

export const publicBookFixtures: PublicBookSummary[] = [
  { slug: 'trabalho-focado', title: 'Trabalho focado', author: 'Cal Newport', publishedArticleCount: 3, latestArticle: { slug: 'ritual-antes-do-foco', title: 'Ritual antes do foco', publishedAt: '2026-08-24T09:00:00-03:00' }, publicTopics: ['atenção', 'ritual', 'profundidade'] },
  { slug: 'a-coragem-de-nao-agradar', title: 'A coragem de não agradar', author: 'Ichiro Kishimi e Fumitake Koga', publishedArticleCount: 3, latestArticle: { slug: 'a-coragem-de-nao-ter-controle', title: 'A coragem de não ter tudo sob controle', publishedAt: '2026-08-20T09:00:00-03:00' }, publicTopics: ['autonomia', 'relações', 'liberdade'] },
]

export const publicLandingFixture: PublicLanding = {
  featuredArticle: publicArticleFixtures[0] ?? null,
  recentArticles: publicArticleFixtures.slice(0, 5),
  publishedBooks: publicBookFixtures,
}
