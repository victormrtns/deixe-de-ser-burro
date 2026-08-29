# Integração frontend–backend e sessão real — Especificação de design

## Contexto

O backend P0 (autenticação, biblioteca, escritas com versões, publicação e
leitura pública) está implementado e verificado em `backend/`, e o adaptador
tipado `httpApi` já cobre esses contratos no frontend. A aplicação, porém,
ainda monta `createMockApi()` em `main.tsx`: a rota `/studio` renderiza uma
demonstração estática com dados fixos, o login não autentica e a proteção de
rota é um boolean hardcoded.

Esta fase liga o frontend ao backend real: sessão autenticada de verdade,
estúdio privado operando sobre a API (biblioteca, escritas, autosave com
concorrência otimista, histórico, publicação) e leitura pública servida pelos
snapshots congelados. Ao final, o autor consegue entrar pela tela de login e
executar o ciclo completo — criar livro, escrever, publicar e ler — sem mocks
no caminho.

Permanecem válidos `DESIGN.md`, `UX-CONTRACT.md`, a especificação do produto
(`2026-08-28-ai-books-learning-blog-design.md`) e a separação rigorosa entre
material privado e publicação. Os padrões de implementação obrigatórios são
`docs/patterns/vercel-composition-patterns/`, `docs/patterns/
vercel-react-best-practices/` e `docs/patterns/clean-code/`.

## Objetivos

1. Autenticação real: entrar em `/entrar`, manter sessão por cookie, sair, e
   proteger todas as rotas `/studio/**` pelo estado real da sessão.
2. Substituir o mock pelo `httpApi` na aplicação montada, mantendo o mock como
   ferramenta de teste injetada por provider.
3. Estúdio privado real: biblioteca, detalhe do livro, criação de livro e
   escrita, workspace com autosave versionado, conflito explícito, histórico
   com restauração e fluxo de publicação com janela de limpeza.
4. Leitura pública real: artigo renderizado a partir do Markdown congelado do
   snapshot, com sanitização.
5. Testes ponta a ponta que começam pelo login contra a stack real
   (Compose + autor semeado), cobrindo o ciclo criar → escrever → publicar →
   ler.

## Fora de escopo

- Chamadas de IA, chat persistido, áudio, transcrição e sugestões reais: a
  conversa do workspace continua demonstrativa e claramente rotulada; o
  `WorkspacePayload` segue com coleções vazias.
- Medição real de orçamento (`UsageApi` permanece mock e **não** aparece na
  shell até existir backend — a interface não exibe dados fictícios).
- Upload de capa pela interface (a API existe; a tela fica para um ciclo de
  refinamento da biblioteca).
- Recuperação de senha, múltiplos autores, "lembrar de mim".
- Edição de metadados do livro e exclusões pela interface além do necessário
  para o ciclo principal.

## Decisões de arquitetura

### Mesma origem, sempre

O frontend fala exclusivamente com `/api` na própria origem: em
desenvolvimento e nos testes E2E o Vite faz proxy para o backend
(`VITE_API_PROXY_TARGET`); em produção o reverse proxy da VPS faz o mesmo.
Não há CORS, e o cookie `HttpOnly` + `SameSite=Lax` circula naturalmente com
`credentials: 'include'`. O backend valida `Origin` em mutações contra
`PUBLIC_ORIGIN`; cada ambiente configura esse valor para a origem do frontend
(dev `http://127.0.0.1:5173`, E2E `http://127.0.0.1:4173`).

### Seleção de adaptador

`main.tsx` monta `httpApi` incondicionalmente. Testes unitários e de
componente continuam injetando `createMockApi()` (ou stubs) via
`AppProviders`/`ApiContext` — o mock deixa de ser o adaptador da aplicação e
vira infraestrutura de teste. Não há flag de runtime para alternar adaptador.

### Sessão

Um `SessionProvider` focado (padrão provider + interface genérica
`state/actions`) é dono do estado de sessão:

```ts
type SessionState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'author'; email: string }

interface SessionActions {
  signIn(email: string, password: string): Promise<void>
  signOut(): Promise<void>
}
```

- Na montagem, resolve `GET /api/auth/session` (via SWR, chave `auth/session`).
- `signIn` chama a API, atualiza o estado e devolve o autor à rota que ele
  tentou acessar (`location.state.from`), sem segredos na URL.
- `signOut` revoga a sessão, limpa caches SWR privados e leva à landing.
- `RequireAuthor` protege as rotas privadas: `loading` mostra um placeholder
  estável, `anonymous` redireciona a `/entrar` preservando o destino.
- Uma resposta `401 authentication_required` de uma chamada privada marca a
  sessão como anônima; o conteúdo local do editor é preservado em memória e a
  interface aponta para `/entrar` sem descartar texto (contrato de UX de
  sessão expirada).

### Rotas do estúdio

O demo `App.tsx` (telas por `useState`) é removido. As rotas privadas passam a
ser páginas roteadas reais, alinhadas ao `UX-CONTRACT.md`:

| Rota | Página | Conteúdo |
|---|---|---|
| `/studio` | `LibraryPage` | livros reais (`books.list`), continuar escrevendo, criar livro |
| `/studio/livros/:bookId` | `BookDetailPage` | escritas do livro (`writings.listByBook`), criar escrita |
| `/studio/escritas/:writingId` | `WorkspacePage` | workspace real (`getWorkspace`) |

A criação de livro e de escrita envia `Idempotency-Key` gerada com
`crypto.randomUUID()` quando o formulário abre; a mesma chave é reutilizada em
novas tentativas do mesmo envio e uma nova chave é gerada ao reabrir o
formulário — clique repetido nunca duplica recurso.

### Workspace versionado

O `WorkspaceProvider` passa a carregar a escrita real e a rastrear
`expectedVersion`:

- o autosave (debounce de 800 ms já existente) envia
  `{ markdown, expectedVersion }`; sucesso atualiza a versão corrente;
- `409 writing_version_conflict` entra no estado `conflict` já previsto pelo
  contrato do provider: o texto local é preservado, a interface explica e
  oferece “Recarregar versão atual” (refetch do canônico) — nunca merge
  silencioso;
- o histórico lista `writings.listVersions` (paginado por cursor) e
  “Restaurar” chama `restoreVersion` com a versão esperada corrente, seguindo
  o mesmo tratamento de conflito;
- o documento permanece editável durante qualquer falha do assistente
  (que continua demonstrativo nesta fase).

### Publicação

“Publicar” abre o diálogo existente e chama
`publishing.publish(writingId, idempotencyKey)`. Sucesso mostra slug público,
data exata de limpeza em `pt-BR` e as ações “Cancelar limpeza” e “Voltar para
rascunho” enquanto permitidas (`getStatus`, `cancelCleanup`, `unpublish`).
`409 publication_already_active` é apresentado como estado, não como erro
genérico.

### Leitura pública

`PublicArticlePage` deixa de renderizar prosa fixa: busca
`public.getArticle(slug)` e renderiza o Markdown congelado com o
`MarkdownPreview` sanitizado já existente (GFM + `rehype-sanitize`), mantendo
medida de leitura, hierarquia e a garantia de que nenhum artefato privado
entra no bundle público inicial (o preview é carregado sob demanda na rota de
artigo, respeitando o gate de bundles com os módulos pesados fora do chunk
inicial público).

### Honestidade da interface

- O indicador de orçamento fixo (“R$ 12,40 de R$ 70,00”) sai da shell até o
  backend de uso existir.
- O painel do assistente informa que a conversa é demonstrativa nesta fase.
- Contagens (“3 escritas”, “2 áudios”) passam a vir da API ou desaparecem.

## Estados, erros e recuperação

Cada superfície assíncrona nova cobre carregando (geometria reservada), vazio,
erro com “Tentar novamente” (via `mutate` do SWR), sucesso e — quando o
backend sinaliza — conflito. Erros usam o `ApiError` tipado do adaptador:
`validation_error` vira erro inline de formulário; `authentication_required`
vira redirecionamento com preservação de trabalho; códigos de conflito viram
estados nomeados. Toasts confirmam ações concluídas e nunca são o único canal
de um erro corrigível.

## Testes

### Unidade e componente (mock injetado)

- `SessionProvider`: anônimo → login → autor; falha de credencial mostra erro
  inline sem cookie; logout limpa estado; `RequireAuthor` redireciona
  preservando destino.
- Biblioteca: lista real, criação com idempotência (reenvio usa a mesma
  chave), estados vazio/erro/retry.
- Workspace: carga real, autosave envia `expectedVersion` incrementada,
  conflito preserva texto e recarrega canônico, restauração de versão.
- Publicação: diálogo publica uma vez, expõe slug + prazo, cancelamento de
  limpeza e retirada.
- Artigo público: renderiza Markdown sanitizado do snapshot; nada privado.

### Ponta a ponta (stack real)

Playwright contra Vite (porta 4173, proxy para o backend em Compose com
`PUBLIC_ORIGIN=http://127.0.0.1:4173` e autor semeado por `bootstrap-author`):

1. login em `/entrar` e chegada à biblioteca;
2. jornada completa: criar livro → criar escrita → editar com autosave →
   publicar → ler o artigo público anônimo → retirar a publicação;
3. falhas: credencial inválida, rota privada sem sessão, conflito de versão
   (segunda aba/contexto salva antes).

O comando de E2E documenta a dependência da stack (`compose up db backend` +
seed); sem ela, o gate reporta o bloqueio em vez de fingir sucesso.

## Critérios de aceite

1. `main.tsx` monta `httpApi`; nenhum fluxo do estúdio depende de
   `createMockApi()` em runtime (exceto conversa demonstrativa e usage, que
   ficam explícitos).
2. O autor entra por `/entrar`, é devolvido à rota que tentou acessar, e
   `/studio/**` é inacessível anônimo — verificado por teste.
3. Biblioteca, detalhe do livro, workspace e publicação operam sobre a API
   real com todos os estados do contrato de UX.
4. Autosave concorrente nunca perde texto silenciosamente: conflito é visível
   e recuperável.
5. O artigo público exibe o Markdown congelado real, sanitizado, sem expor
   artefatos privados nem inflar o bundle público inicial.
6. E2E com login real cobre o ciclo completo e roda contra a stack local.
7. `UX-CONTRACT.md` e `premium-ui.json` refletem os novos fluxos; todos os
   gates existentes (unit, a11y, premium, bundles, lint, typecheck, build)
   continuam verdes.
