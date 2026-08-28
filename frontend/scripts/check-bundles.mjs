import { readdir, readFile } from 'node:fs/promises'
const assets = new URL('../dist/assets/', import.meta.url)
const files = (await readdir(assets)).filter((file) => file.endsWith('.js'))
const initial = files.filter((file) => file.startsWith('index-'))
const forbidden = ['codemirror', 'mermaid', 'katex', 'diff-match-patch']
const violations = []
for (const file of initial) { const source = (await readFile(new URL(file, assets), 'utf8')).toLowerCase(); for (const name of forbidden) if (source.includes(name)) violations.push(`${name} em ${file}`) }
if (violations.length) { console.error(violations.join('\n')); process.exit(1) }
console.log(`Bundle público inicial: ${initial.join(', ')} sem módulos privados pesados.`)
