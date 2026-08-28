import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
for (const path of ['/', '/artigos/ritual-antes-do-foco', '/entrar', '/studio', '/studio/escritas/writing-01']) test(`acessibilidade ${path}`, async ({ page }) => { await page.goto(path); const results = await new AxeBuilder({ page }).analyze(); expect(results.violations).toEqual([]) })
