import { delay, http, HttpResponse } from 'msw'
import { publicArticleFixtures, publicBookFixtures, publicLandingFixture, usageFixtures, workspaceFixture } from '@/services/mock/fixtures'

export const handlers = [
  http.get('/api/public/landing', () => HttpResponse.json(publicLandingFixture)),
  http.get('/api/public/articles', () => HttpResponse.json(publicArticleFixtures)),
  http.get('/api/public/books', () => HttpResponse.json(publicBookFixtures)),
  http.get('/api/writings/:id/workspace', ({ params }) => params.id === workspaceFixture.writing.id ? HttpResponse.json(workspaceFixture) : HttpResponse.json({ message: 'Escrita não encontrada.' }, { status: 404 })),
  http.get('/api/usage', ({ request }) => {
    const scenario = new URL(request.url).searchParams.get('scenario') as keyof typeof usageFixtures | null
    return HttpResponse.json(usageFixtures[scenario ?? 'normal'] ?? usageFixtures.normal)
  }),
  http.get('/api/scenarios/slow-workspace', async () => { await delay(800); return HttpResponse.json(workspaceFixture) }),
  http.get('/api/scenarios/workspace-error', () => HttpResponse.json({ message: 'Não foi possível carregar a escrita.' }, { status: 503 })),
]
