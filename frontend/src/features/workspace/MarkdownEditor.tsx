import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { EditorView } from '@codemirror/view'

export function MarkdownEditor({ value, onChange }: { value: string; onChange(value: string): void }) {
  return <div className="markdown-editor"><CodeMirror value={value} extensions={[markdown(), EditorView.contentAttributes.of({ 'aria-label': 'Conteúdo Markdown' })]} minHeight="calc(100vh - 180px)" basicSetup={{ lineNumbers: false, foldGutter: false }} onChange={onChange} /></div>
}
