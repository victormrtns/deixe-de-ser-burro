import { setupWorker } from 'msw/browser'
import { handlers } from '@/services/mock/handlers'

export const worker = setupWorker(...handlers)
