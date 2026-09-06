import { expect, test } from '@playwright/test'
import { signIn } from './auth'

test('expõe conflito entre duas sessões e recupera o canônico explicitamente', async ({ browser }) => {
  const first = await browser.newPage()
  await signIn(first)
  const suffix = Date.now()
  const bookTitle = `Concorrência ${suffix}`
  await first.getByRole('button', { name: 'Adicionar livro' }).click()
  await first.getByLabel('Título').fill(bookTitle)
  await first.getByRole('button', { name: 'Adicionar à estante' }).click()
  await first.getByRole('button', { name: `Abrir ${bookTitle}` }).click()
  await first.getByRole('button', { name: 'Nova escrita' }).click()
  await first.getByLabel('Título').fill(`Versões ${suffix}`)
  await first.getByRole('button', { name: 'Criar escrita' }).click()
  const writingUrl = first.url()

  const stale = await browser.newPage()
  await signIn(stale)
  await stale.goto(writingUrl)
  await first.getByLabel('Conteúdo Markdown').fill('# Versão canônica')
  await expect(first.getByRole('status')).toContainText('Salvo')
  await stale.getByLabel('Conteúdo Markdown').fill('# Texto local preservado')
  await expect(stale.getByRole('status')).toContainText('Seu texto foi preservado')
  await expect(stale.getByLabel('Conteúdo Markdown')).toHaveValue('# Texto local preservado')
  await stale.getByRole('button', { name: 'Recarregar versão atual' }).click()
  await expect(stale.getByLabel('Conteúdo Markdown')).toHaveValue('# Versão canônica')
})
