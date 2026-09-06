export default async function globalSetup() {
  try {
    const response = await fetch('http://127.0.0.1:4173/api/health/ready')
    if (!response.ok) throw new Error(`status ${response.status}`)
  } catch (error) {
    throw new Error(`Backend indisponível para o E2E. Suba e prepare a stack conforme ops/dev-stack.md. Causa: ${String(error)}`)
  }
}
