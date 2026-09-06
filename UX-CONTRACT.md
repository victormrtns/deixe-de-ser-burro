# deixedeserburro — contrato de experiência

## Fontes e escopo

| Tema | Fonte | Consequência de interface |
|---|---|---|
| Produto, privacidade e ciclo de publicação | `docs/superpowers/specs/2026-08-28-ai-books-learning-blog-design.md` | Área privada autenticada; artigo público nunca expõe artefatos de trabalho; limpeza tem recuperação por três dias. |
| Identidade e implementação | `docs/superpowers/plans/2026-08-28-visual-identity-frontend.md` | UI em pt-BR, WCAG 2.2 AA e contratos compartilhados. |
| Referência visual | `design.md` | Fonte única de cor, tipografia e linguagem visual. É referência extraída de fora: os componentes e marcas que ele cita são calibragem de estilo, não o inventário do produto. |
| Marca e ativos | `brand/` e `brand/README.md` | Nome público `deixedeserburro`; logo, wordmark e favicon vêm dos arquivos versionados, com as faixas de tamanho do README. |

## Rotas e títulos

| Rota | Título | Acesso | Destino principal |
|---|---|---|---|
| `/` | `deixedeserburro — Leituras que continuam` | Público | Estante pública |
| `/artigos` | `Artigos — deixedeserburro` | Público | Índice de artigos |
| `/artigos/:slug` | `Título do artigo — deixedeserburro` | Público | Leitura do artigo |
| `/livros` | `Livros — deixedeserburro` | Público | Índice de livros |
| `/livros/:slug` | `Título do livro — deixedeserburro` | Público | Artigos publicados do livro |
| `/sobre` | `Sobre — deixedeserburro` | Público | Sobre a publicação |
| `/entrar` | `Entrar — deixedeserburro` | Público | Autenticação do autor |
| `/studio` | `Biblioteca — deixedeserburro` | Privado | Livros e escritas |
| `/studio/livros/:bookId` | `Título do livro — deixedeserburro` | Privado | Escritas do livro |
| `/studio/escritas/:id` | `Título da escrita — deixedeserburro` | Privado | Workspace |
| `/sem-permissao` | `Acesso restrito — deixedeserburro` | Público | Página 403 |
| `*` | `Página não encontrada — deixedeserburro` | Público | Página 404 |

O sufixo da marca é sempre ` — deixedeserburro`; só a landing inverte a ordem. Enquanto o recurso carrega, o título usa o rótulo genérico da rota (`Livro`, `Escrita`, `Artigo`) e nunca herda o título da página anterior.

As páginas de 403, 404 e de falha são próprias, preservam a navegação possível e recebem títulos honestos. Rotas públicas nunca carregam navegação ou módulos privados.

## Mapa canônico de UI

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Ação | `ui/Button` | Este contrato | `primary` / `neutral` / `ghost` / `danger` | unidade + teclado |
| Ação inline | classe `.text-action` em `ui/ui.css` | Este contrato | única | contraste + teclado |
| Ação de ícone | `.workspace-header-actions > button` em `features/workspace/workspace-sovereign.css` | Este contrato | alternar painel / focar documento | rótulo acessível + alvo mínimo |
| Form | `Field` e formulários `noValidate` | Este contrato | criar / editar / entrar | unidade + teclado |
| Scrollbar | `styles/globals.css` | Este contrato | apenas geometria documentada | estilo computado |
| Toast | `ToastProvider` | Este contrato | sucesso / aviso / informação / erro | live region |
| Dialog | `ui/Dialog` (confirmação) e `LibraryFormDialog` (criação) | Este contrato | alertdialog de confirmação / dialog de formulário | foco + Escape |
| Página de falha | `ui/RouteErrorPage` e a classe `.route-error` | Este contrato | 403 / 404 / falha de carregamento | título + navegação possível |
| CRUD | rotas e serviços de biblioteca | Especificação do produto | retornar à lista / permanecer | E2E completo |

Toda ação clicável é uma das formas acima. Nenhum `<button>` do produto declara o
próprio preenchimento, raio ou peso: quem precisa de um botão importa a primitiva.
Um botão sem classe é defeito, não variante.

A ação de ícone é a barra de ferramentas do estúdio — quadrado de 32px, sem rótulo
visível, `aria-label` obrigatório e `aria-pressed` quando alterna estado. Fica em
`workspace-sovereign.css` porque só o workspace tem barra de ferramentas; no dia em que
uma segunda região precisar dela, vira `.icon-button` em `ui/ui.css` e este contrato
muda de dono junto. Ícone sozinho nunca carrega ação destrutiva nem ação primária.

`primary` é a única ação escura por região e nunca aparece duas vezes na mesma decisão.
`danger` existe para exclusão e nunca carrega texto claro sobre o vermelho. É a forma de
excluir livro, excluir escrita e qualquer ação que descarte trabalho de forma irreversível,
sempre atrás de um diálogo que nomeia o objeto e a consequência.
`.text-action` é para recuperação e ações secundárias dentro de conteúdo — tentar de
novo, restaurar, lembrar — e nunca substitui uma ação primária.

Botão ocupado usa `busy`, que preserva o rótulo, mantém a largura e marca `aria-busy`.
Trocar o texto por um gerúndio (`Publicando…`, `Aplicando…`) é proibido: muda a
geometria no meio da interação e quebra a promessa do ledger abaixo.

Falha de rota e falha de carregamento usam a mesma página. Um erro que impede a tela
inteira não é um parágrafo dentro do layout de conteúdo.

## Ledger de comportamento

| Operação | Gatilho | Pendente | Sucesso | Recuperação de falha |
|---|---|---|---|---|
| Salvar rascunho | alteração no editor, debounce de 800 ms | “Salvando…” inline | “Salvo” inline | preservar texto e oferecer nova tentativa |
| Enviar prompt | “Enviar” | mensagem em streaming + “Parar geração” | resposta persistida | tentar novamente o último prompt |
| Gravar áudio | “Gravar áudio” | tempo decorrido + “Parar” | cartão de processamento | reter blob local e repetir envio |
| Aceitar sugestão | “Aceitar alteração” | botão `busy`, demais ações do diff bloqueadas | nova versão visível | recarregar versão canônica |
| Publicar | confirmação em diálogo | botão `busy`, rótulo e largura preservados | URL pública, aviso de três dias e toast | manter rascunho e explicar a falha |
| Entrar | envio de e-mail e senha | botão ocupado sem salto de layout | retorno à rota privada solicitada | credencial inválida inline, preservando e-mail |
| Sair | ação “Sair” na shell privada | sessão sendo revogada | landing pública sem acesso ao cache privado | permitir nova tentativa sem expor dados |
| Sessão expirada | resposta `authentication_required` | preservar o texto local | redirecionar a `/entrar` com destino de retorno | nunca descartar edição silenciosamente |
| Conflito de versão | autosave ou restauração com versão antiga | texto local permanece editável | recarregar versão canônica por ação explícita | nunca fazer merge silencioso |
| Retirar publicação | “Voltar para rascunho” | ação ocupada | snapshot deixa de ser público, toast confirma | manter estado publicado e explicar falha em toast de erro |
| Cancelar limpeza | “Cancelar limpeza” | ação ocupada | contexto privado permanece, toast confirma | manter agendamento e explicar falha em toast de erro |
| Restaurar versão | “Restaurar” no histórico | ação ocupada | texto substituído, toast nomeia a versão | conflito recarrega a versão canônica, sem toast de sucesso |
| Excluir livro ou escrita | ação destrutiva em diálogo | ação ocupada | item some da lista, toast confirma | manter o item e explicar a falha |

## Navegação e foco

Em desktop, a shell privada mantém contexto à esquerda e conteúdo no centro. Em mobile, navegação vira cabeçalho compacto e abas preservam a rota. Voltar respeita a hierarquia livro → biblioteca. Após fechar diálogo, foco retorna ao gatilho; após navegação, o título principal recebe foco programático quando necessário. Escape fecha o overlay superior e nunca descarta dados silenciosamente.

Cada painel do workspace declara seu scroll. A shell global não usa `overflow: hidden` para forçar altura. Na leitura pública, o documento é o único dono do scroll.

## Formulários, feedback e falhas

Diálogos destrutivos e de confirmação focam inicialmente a ação que não altera nada — “Cancelar” ou “Continuar editando” — e a ação que confirma nunca recebe `autoFocus`.

Formulários usam `noValidate`, erros inline associados, valores preservados e foco no primeiro campo inválido. Submissão duplicada é bloqueada sem mudar dimensões. Toast confirma ações concluídas cujo resultado não é visível na tela em que a ação
aconteceu — publicar, retirar publicação, cancelar limpeza, restaurar versão, criar livro
ou escrita. Ação que já se confirma no próprio lugar, como aceitar uma sugestão, não recebe
toast: seria a segunda cópia da mesma informação. Toast nunca carrega a única explicação de
um erro corrigível, e nunca anuncia sucesso que não aconteceu — operação que engole a própria
exceção precisa devolver o desfecho a quem chamou antes de notificar. Diálogos destrutivos nomeiam objeto e consequência, focam inicialmente a opção segura e restauram foco ao fechar.

Estados assíncronos cobrem carregando, vazio, sem resultados, erro, cancelamento, sucesso e nova tentativa quando honesta. O layout reserva espaço para feedback. Sessão expirada preserva trabalho local não sensível e direciona a autenticação. Rascunhos pendentes de sincronização são explicitamente rotulados.

## Público, privacidade e orçamento

Artigos públicos contêm apenas versão congelada e metadados públicos. Conversas, prompts, transcrições, áudios, sugestões e identificadores internos não aparecem no bundle nem nas respostas públicas.

O orçamento não aparece até existir medição real no backend. A interface nunca apresenta valores simulados como se fossem consumo do autor.

## Responsividade, locale e acessibilidade

Idioma e locale são `pt-BR`; datas, moeda e números usam APIs de internacionalização. O alvo é WCAG 2.2 AA. Interações têm semântica nativa, hover, foco visível, ativo, desabilitado e ocupado quando aplicável. O sistema respeita `prefers-reduced-motion`, mantém scrollbars visíveis e funciona com teclado e zoom de 200%.
