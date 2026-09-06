# Auditoria de padrões de front-end — registrado sem consertar

Escopo da auditoria: `frontend/src/`, contra as regras publicadas pela Vercel em
[react-best-practices](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/AGENTS.md),
[composition-patterns](https://github.com/vercel-labs/agent-skills/blob/main/skills/composition-patterns/AGENTS.md)
e [Conformance](https://vercel.com/docs/conformance/rules). O que foi corrigido está no
commit de `feat/front-patterns`. O que ficou aqui é o que não dava para mexer com segurança.

## 1. Fora de alcance: `features/workspace/**` e `features/chat/**`

Estão sendo trabalhados em outra branch. Só leitura.

| Arquivo | Problema |
|---|---|
| `frontend/src/features/workspace/useAutosave.ts` | Código morto: nenhum importador. O debounce de 800 ms que o UX-CONTRACT descreve está reimplementado dentro do `useEffect` de `WorkspaceProvider.tsx:47`. Duas verdades para a mesma regra; sobra uma. |
| `frontend/src/features/workspace/MarginRail.tsx` | Código morto: nenhum importador. |
| `frontend/src/features/chat/conversationEvents.ts` | Ilha morta: só o próprio teste importa. Junto com ela, `ConversationEvent` em `services/contracts.ts:19-26` não descreve nada que o produto renderize hoje. |
| `frontend/src/features/workspace/VersionHistory.tsx:15` | `new Intl.DateTimeFormat(...)` construído dentro do `.map()` — um formatador por linha, por render. Içar para o módulo (foi o que fizemos em `BookDetailPage` e `PublicationStatus`). |
| `frontend/src/features/workspace/WorkspacePage.tsx:22` | `suggestion` fixture literal no módulo de produção. É dado de mock vivendo num arquivo de produto. |
| `frontend/src/features/workspace/Workspace.tsx` | JSX de 676 colunas em 13 linhas, e 7 dos 13 avisos de `react-refresh/only-export-components` do repositório inteiro. |
| `frontend/src/features/workspace/workspace.css` (3660 col) e `features/chat/chat.css` (1268 col) | Continuam em linha única. Os `.css` fora dessas duas pastas foram expandidos neste commit. |
| `VersionHistory.tsx:8`, `WorkspacePage.tsx:28,41` | `useApi() as HttpAppApi` virou redundante: `useApi()` agora devolve a superfície completa. `HttpAppApi` ficou como alias transitório em `services/contracts.ts` só para esses três casts compilarem. Quando aquela branch encostar: trocar por `useApi()` e apagar o alias. |

## 2. `react-refresh/only-export-components` — 13 avisos

`SessionProvider`, `ChatProvider`, `SuggestionProvider`, `RecorderProvider`,
`WorkspaceProvider`, `PanelResizer` e `Workspace` exportam o componente provider e o hook
de consumo no mesmo arquivo. Isso é exatamente o padrão de composição que a Vercel
recomenda (desacoplar estado da UI atrás de um contrato de Context) — o aviso é do Fast
Refresh, não de arquitetura. `ToastProvider` e `router.tsx` já resolvem com
`eslint-disable-next-line` e um comentário.

Escolhas: espalhar o mesmo `eslint-disable` por mais seis arquivos, ou desligar a regra
para `**/*Provider.tsx` no `eslint.config.js`. Não fiz nenhuma das duas porque é decisão
de convenção do time, não defeito. Enquanto isso, os avisos escondem avisos novos.

## 3. ESLint sem `jsx-a11y` (Vercel Conformance `ESLINT_REACT_RULES_REQUIRED`)

`frontend/eslint.config.js` tem `react-hooks` e `react-refresh`, mas não
`eslint-plugin-jsx-a11y` nem `eslint-plugin-react`. A regra de Conformance da Vercel exige
os três. O alvo declarado no UX-CONTRACT é WCAG 2.2 AA, e hoje a acessibilidade é
verificada só em runtime por `src/test/accessibility.test.tsx` (axe, duas rotas).

Não corrigido: exige dependência nova, e o escopo proibia adicionar dependências.

## 4. Fixtures de mock no bundle de produção

`frontend/src/services/httpApi.ts:133` faz `const deferredToMock = createMockApi()` no
topo do módulo, porque áudio, sugestões e uso ainda não têm backend. Isso arrasta
`services/mockApi.ts` e `services/mock/fixtures.ts` — que contêm mensagens de conversa e
sugestões de exemplo — para dentro do bundle inicial, servido também nas rotas públicas.

O UX-CONTRACT diz: "Conversas, prompts, transcrições, áudios, sugestões e identificadores
internos não aparecem no bundle nem nas respostas públicas." Isso é um furo literal na
promessa, ainda que o conteúdo seja fictício.

Conserto honesto: `import()` dinâmico dos três adaptadores pendentes, o que torna
`audio`/`suggestions`/`usage` assíncronos na montagem do objeto `AppApi`, ou stubs que
lançam `not_implemented` até o backend existir. Ambos mexem no contrato de `AppApi` e
merecem decisão própria, não um efeito colateral de auditoria.
`scripts/check-bundles.mjs` também não cobre isso hoje (só procura codemirror, mermaid,
katex e diff-match-patch).

## 5. `AudioStage` duplica e diverge de `JobStatus`

`frontend/src/features/audio/AudioJobCard.tsx:1` declara
`'uploading' | 'queued' | 'transcribing' | 'organizing' | 'ready' | 'failed'`, enquanto
`services/contracts.ts:2` declara `JobStatus` com `'analyzing'` no lugar de `'organizing'`.
São o mesmo conceito com dois nomes; um `AudioClip` vindo da API não é atribuível ao card.

Não unifiquei porque `AudioJobCard` e `Recorder` ainda não são renderizados por página
nenhuma (só pelo teste), e quem vai ligá-los é a branch do workspace. Unificar agora seria
decidir o vocabulário no lugar de quem monta a tela.

## 6. `PublicBookPage` busca duas listas inteiras para montar uma página

`frontend/src/public-site/PublicBookPage.tsx:9-12` chama `usePublicBooks()` e
`usePublicArticles()` e filtra os dois no cliente por `slug`. `PublicApi.getBook(slug)`
já existe no contrato e é implementado por `httpApi` e por `createMockApi`. A página
carrega o arquivo inteiro para mostrar um livro.

Não troquei porque `getBook` devolve `PublicBookDetail` (com `articles` embutidos) e a
página monta a lista a partir de `PublicArticleSummary`; a migração muda o que a tela
renderiza, não só de onde os dados vêm. É mudança de comportamento, não de padrão.

## 7. `BookFormDialog` e `WritingFormDialog` são quase o mesmo componente

`frontend/src/features/library/LibraryFormDialog.tsx` — dois componentes de ~30 linhas que
diferem em dois nomes de campo, dois rótulos, um default e uma frase de erro. A duplicação
é real, mas o único jeito de fundi-los é um descritor de campos, que é a abstração
especulativa que o escopo proíbe. Fundir quando aparecer o terceiro formulário.
