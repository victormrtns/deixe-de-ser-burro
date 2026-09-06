import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../src', import.meta.url))
const forbidden = [/\balert\s*\(/, /\bconfirm\s*\(/, /\bprompt\s*\(/, /dangerouslySetInnerHTML/]
const files = []
async function walk(path) {
  for (const entry of await readdir(path, { withFileTypes: true })) {
    const target = join(path, entry.name)
    if (entry.isDirectory()) await walk(target)
    else if (/\.(ts|tsx)$/.test(entry.name)) files.push(target)
  }
}
await walk(root)
const violations = []
for (const file of files) {
  const source = await readFile(file, 'utf8')
  for (const pattern of forbidden) if (pattern.test(source)) violations.push(`${file}: ${pattern}`)
  if (file.endsWith('/main.tsx') && /createMockApi/.test(source)) violations.push(`${file}: mock no entrypoint de produção`)
  if (!file.includes('/services/') && /\bfetch\s*\(/.test(source)) violations.push(`${file}: fetch direto fora do adaptador`)
  if (/R\$ 12,40 de R\$ 70,00/.test(source)) violations.push(`${file}: orçamento fictício`)
}
if (violations.length) {
  console.error(violations.join('\n'))
  process.exit(1)
}
console.log(`Premium static check: ${files.length} arquivos, 0 violações.`)
