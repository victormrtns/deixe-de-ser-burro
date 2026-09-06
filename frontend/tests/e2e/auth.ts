import type { Page } from '@playwright/test'

export const author = {
  email: process.env.E2E_AUTHOR_EMAIL ?? 'e2e@example.com',
  password: process.env.E2E_AUTHOR_PASSWORD ?? 'correct horse',
}

export async function signIn(page: Page) {
  await page.goto('/entrar')
  await page.getByLabel('E-mail').fill(author.email)
  await page.getByLabel('Senha').fill(author.password)
  await page.getByRole('button', { name: 'Entrar no estúdio' }).click()
}
