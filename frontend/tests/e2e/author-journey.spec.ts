import { expect, test } from '@playwright/test'
import { signIn } from './auth'

test('cria livro e escrita, salva, publica, lê anonimamente e retira', async ({ page, browser }) => {
  await signIn(page)
  const suffix = Date.now()
  const bookTitle = `Livro E2E ${suffix}`
  const writingTitle = `Escrita E2E ${suffix}`
  await page.getByRole('button', { name: 'Adicionar livro' }).click()
  await page.getByLabel('Título').fill(bookTitle)
  await page.getByLabel('Autor').fill('Autora E2E')
  await page.getByRole('button', { name: 'Adicionar à estante' }).click()
  await page.getByRole('button', { name: `Abrir ${bookTitle}` }).click()
  await page.getByRole('button', { name: 'Nova escrita' }).click()
  await page.getByLabel('Título').fill(writingTitle)
  await page.getByRole('button', { name: 'Criar escrita' }).click()
  const editor = page.getByLabel('Conteúdo Markdown')
  await editor.fill(`# ${writingTitle}\n\nTexto público congelado.`)
  await expect(page.getByRole('status')).toContainText('Salvo')
  await page.getByRole('button', { name: 'Publicar' }).click()
  await page.getByRole('button', { name: 'Publicar versão' }).click()
  const publicLink = page.getByRole('link', { name: /Abrir artigo público/ })
  const href = await publicLink.getAttribute('href')
  expect(href).toBeTruthy()
  const anonymous = await browser.newPage()
  await anonymous.goto(href!)
  await expect(anonymous.getByRole('heading', { name: writingTitle })).toBeVisible()
  await expect(anonymous.locator('body')).not.toContainText(/writing-|prompt|transcrição/i)
  await anonymous.close()
  await page.getByRole('button', { name: 'Voltar para rascunho' }).click()
})
