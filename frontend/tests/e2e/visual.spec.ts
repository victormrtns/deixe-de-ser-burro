import { expect, test } from '@playwright/test'
test('biblioteca pública permanece visualmente estável', async ({ page }) => { await page.goto('/'); await expect(page).toHaveScreenshot('biblioteca-publica.png', { fullPage: true }) })
test('workspace permanece visualmente estável', async ({ page }) => { await page.goto('/studio/escritas/writing-01'); await expect(page).toHaveScreenshot('workspace.png', { fullPage: true }) })
