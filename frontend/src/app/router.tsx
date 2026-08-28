import { lazy, Suspense } from 'react'
import { createBrowserRouter, createMemoryRouter, Navigate, type RouteObject } from 'react-router-dom'
import { SignInPage } from '@/features/auth/SignInPage'
import { PublicArticlePage } from '@/public-site/PublicArticlePage'
import { PublicLibraryPage } from '@/public-site/PublicLibraryPage'
import { PublicBookPage } from '@/public-site/PublicBookPage'
import { PublicAboutPage } from '@/public-site/PublicAboutPage'
import { PublicArticlesPage } from '@/public-site/PublicArticlesPage'
import { PublicBooksPage } from '@/public-site/PublicBooksPage'
import { ForbiddenPage, NotFoundPage } from '@/ui/RouteErrorPage'
import { useDocumentTitle } from '@/ui/useDocumentTitle'
import { App } from './App'

const WorkspacePage = lazy(() => import('@/features/workspace/WorkspacePage').then((module) => ({ default: module.WorkspacePage })))

function StudioPlaceholder() {
  useDocumentTitle('Biblioteca — Entrelinhas')
  return <App />
}

function appRoutes(authenticated: boolean): RouteObject[] { return [
  { path: '/', element: <PublicLibraryPage /> },
  { path: '/artigos', element: <PublicArticlesPage /> },
  { path: '/livros', element: <PublicBooksPage /> },
  { path: '/livros/:slug', element: <PublicBookPage /> },
  { path: '/artigos/:slug', element: <PublicArticlePage /> },
  { path: '/sobre', element: <PublicAboutPage /> },
  { path: '/entrar', element: <SignInPage /> },
  { path: '/studio', element: authenticated ? <StudioPlaceholder /> : <Navigate to="/entrar" replace /> },
  { path: '/studio/escritas/:id', element: authenticated ? <Suspense fallback={<main aria-label="Entrelinhas">Abrindo escrita…</main>}><WorkspacePage save={() => Promise.resolve()} /></Suspense> : <Navigate to="/entrar" replace /> },
  { path: '/sem-permissao', element: <ForbiddenPage /> },
  { path: '*', element: <NotFoundPage /> },
] }

// Router factory is colocated to keep the route contract statically analyzable.
// eslint-disable-next-line react-refresh/only-export-components
export function createAppRouter(initialEntries = ['/'], options: { authenticated?: boolean } = {}) {
  const authenticated = options.authenticated ?? true
  return createMemoryRouter(appRoutes(authenticated), { initialEntries })
}

export function createBrowserAppRouter() { return createBrowserRouter(appRoutes(true)) }
