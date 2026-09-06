import { expect, test } from '@playwright/test'
import { author, signIn } from './auth'

test('protege o estúdio, entra pela sessão real e sai', async ({ page }) => {
  await page.goto('/studio')
  await expect(page).toHaveURL(/\/entrar$/)
  await page.getByLabel('E-mail').fill(author.email)
  await page.getByLabel('Senha').fill('senha-incorreta')
  await page.getByRole('button', { name: 'Entrar no estúdio' }).click()
  await expect(page.getByText('E-mail ou senha inválidos.')).toBeVisible()
  await page.getByLabel('Senha').fill(author.password)
  await page.getByRole('button', { name: 'Entrar no estúdio' }).click()
  await expect(page).toHaveURL(/\/studio$/)
  await page.getByRole('button', { name: 'Sair' }).click()
  await expect(page).toHaveURL('/')
})

test('entra diretamente pela tela de login', async ({ page }) => {
  await signIn(page)
  await expect(page.getByRole('heading', { name: /biblioteca/i })).toBeVisible()
})
