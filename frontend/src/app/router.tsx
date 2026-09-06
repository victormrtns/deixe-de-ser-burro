import { lazy, Suspense } from 'react'
import { createBrowserRouter, createMemoryRouter, type RouteObject } from 'react-router-dom'
import { RequireAuthor } from '@/features/auth/RequireAuthor'
import { LibraryPage } from '@/features/library/LibraryPage'
import { BookDetailPage } from '@/features/library/BookDetailPage'
import { SignInPage } from '@/features/auth/SignInPage'
import { PublicArticlePage } from '@/public-site/PublicArticlePage'
import { PublicLibraryPage } from '@/public-site/PublicLibraryPage'
import { PublicBookPage } from '@/public-site/PublicBookPage'
import { PublicAboutPage } from '@/public-site/PublicAboutPage'
import { PublicArticlesPage } from '@/public-site/PublicArticlesPage'
import { PublicBooksPage } from '@/public-site/PublicBooksPage'
import { ForbiddenPage, NotFoundPage } from '@/ui/RouteErrorPage'

const WorkspacePage = lazy(() => import('@/features/workspace/WorkspacePage').then((module) => ({ default: module.WorkspacePage })))

function appRoutes(): RouteObject[] { return [
  { path: '/', element: <PublicLibraryPage /> },
  { path: '/artigos', element: <PublicArticlesPage /> },
  { path: '/livros', element: <PublicBooksPage /> },
  { path: '/livros/:slug', element: <PublicBookPage /> },
  { path: '/artigos/:slug', element: <PublicArticlePage /> },
  { path: '/sobre', element: <PublicAboutPage /> },
  { path: '/entrar', element: <SignInPage /> },
  { path: '/studio', element: <RequireAuthor><LibraryPage /></RequireAuthor> },
  { path: '/studio/livros/:bookId', element: <RequireAuthor><BookDetailPage /></RequireAuthor> },
  { path: '/studio/escritas/:id', element: <RequireAuthor><Suspense fallback={<main aria-label="Entrelinhas">Abrindo escrita…</main>}><WorkspacePage /></Suspense></RequireAuthor> },
  { path: '/sem-permissao', element: <ForbiddenPage /> },
  { path: '*', element: <NotFoundPage /> },
] }

// Router factory is colocated to keep the route contract statically analyzable.
// eslint-disable-next-line react-refresh/only-export-components
export function createAppRouter(initialEntries = ['/']) {
  return createMemoryRouter(appRoutes(), { initialEntries })
}

export function createBrowserAppRouter() { return createBrowserRouter(appRoutes()) }
