import { useDeferredValue, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'

export function MarkdownPreview({ markdown }: { markdown: string }) {
  const deferred = useDeferredValue(markdown)
  useEffect(() => { if (deferred.includes('```mermaid')) void import('mermaid'); if (/\$[^$]+\$/.test(deferred)) void import('katex') }, [deferred])
  return <article className="markdown-preview prose" aria-label="Preview do documento"><ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{deferred}</ReactMarkdown></article>
}
