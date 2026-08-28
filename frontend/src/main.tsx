import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { createBrowserAppRouter } from '@/app/router'
import { AppProviders } from '@/app/AppProviders'
import { createMockApi } from '@/services/mockApi'
import '@/styles/globals.css'

const root = document.getElementById('root')
const api = createMockApi()

if (!root) {
  throw new Error('O elemento raiz da aplicação não foi encontrado.')
}

createRoot(root).render(
  <StrictMode>
    <AppProviders api={api}><RouterProvider router={createBrowserAppRouter()} /></AppProviders>
  </StrictMode>,
)
