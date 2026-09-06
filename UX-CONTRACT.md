# Entrelinhas — contrato de experiência

## Fontes e escopo

| Tema | Fonte | Consequência de interface |
|---|---|---|
| Produto, privacidade e ciclo de publicação | `docs/superpowers/specs/2026-08-28-ai-books-learning-blog-design.md` | Área privada autenticada; artigo público nunca expõe artefatos de trabalho; limpeza tem recuperação por três dias. |
| Identidade e implementação | `docs/superpowers/plans/2026-08-28-visual-identity-frontend.md` | UI em pt-BR, WCAG 2.2 AA e contratos compartilhados. |
| Referência visual | `design.md` | Papel claro, superfícies hairline, tipografia calma e acentos pontuais. |

## Rotas e títulos

| Rota | Título | Acesso | Destino principal |
|---|---|---|---|
| `/` | `Entrelinhas — Leituras que continuam` | Público | Estante pública |
| `/artigos/:slug` | `Título do artigo — Entrelinhas` | Público | Leitura do artigo |
| `/entrar` | `Entrar — Entrelinhas` | Público | Autenticação do autor |
| `/studio` | `Biblioteca — Entrelinhas` | Privado | Livros e escritas |
| `/studio/livros/:id` | `Livro — Entrelinhas` | Privado | Escritas do livro |
| `/studio/escritas/:id` | `Escrita — Entrelinhas` | Privado | Workspace |

Rotas 403, 404 e falhas usam páginas próprias, preservam navegação possível e recebem títulos honestos. Rotas públicas nunca carregam navegação ou módulos privados.

## Mapa canônico de UI

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Form | `Field` e formulários `noValidate` | Este contrato | criar / editar / entrar | unidade + teclado |
| Scrollbar | `styles/globals.css` | `DESIGN.md` | apenas geometria documentada | estilo computado |
| Toast | `ToastProvider` | Este contrato | sucesso / aviso / informação / erro | live region |
| Dialog | `Dialog` | Este contrato | modal / alertdialog | foco + Escape |
| CRUD | rotas e serviços de biblioteca | Especificação do produto | retornar à lista / permanecer | E2E completo |

## Ledger de comportamento

| Operação | Gatilho | Pendente | Sucesso | Recuperação de falha |
|---|---|---|---|---|
| Salvar rascunho | alteração no editor, debounce de 800 ms | “Salvando…” inline | “Salvo” inline | preservar texto e oferecer nova tentativa |
| Enviar prompt | “Enviar” | mensagem em streaming + “Parar geração” | resposta persistida | tentar novamente o último prompt |
| Gravar áudio | “Gravar áudio” | tempo decorrido + “Parar” | cartão de processamento | reter blob local e repetir envio |
| Aceitar sugestão | “Aceitar alteração” | ações do diff bloqueadas | nova versão visível | recarregar versão canônica |
| Publicar | confirmação em diálogo | botão com geometria estável | URL pública + aviso de três dias | manter rascunho e explicar a falha |
| Entrar | envio de e-mail e senha | botão ocupado sem salto de layout | retorno à rota privada solicitada | credencial inválida inline, preservando e-mail |
| Sair | ação “Sair” na shell privada | sessão sendo revogada | landing pública sem acesso ao cache privado | permitir nova tentativa sem expor dados |
| Sessão expirada | resposta `authentication_required` | preservar o texto local | redirecionar a `/entrar` com destino de retorno | nunca descartar edição silenciosamente |
| Conflito de versão | autosave ou restauração com versão antiga | texto local permanece editável | recarregar versão canônica por ação explícita | nunca fazer merge silencioso |
| Retirar publicação | “Voltar para rascunho” | ação ocupada | snapshot deixa de ser público | manter estado publicado e explicar falha |

## Navegação e foco

Em desktop, a shell privada mantém contexto à esquerda e conteúdo no centro. Em mobile, navegação vira cabeçalho compacto e abas preservam a rota. Voltar respeita a hierarquia livro → biblioteca. Após fechar diálogo, foco retorna ao gatilho; após navegação, o título principal recebe foco programático quando necessário. Escape fecha o overlay superior e nunca descarta dados silenciosamente.

Cada painel do workspace declara seu scroll. A shell global não usa `overflow: hidden` para forçar altura. Na leitura pública, o documento é o único dono do scroll.

## Formulários, feedback e falhas

Formulários usam `noValidate`, erros inline associados, valores preservados e foco no primeiro campo inválido. Submissão duplicada é bloqueada sem mudar dimensões. Toast confirma ações concluídas; nunca carrega a única explicação de um erro corrigível. Diálogos destrutivos nomeiam objeto e consequência, focam inicialmente a opção segura e restauram foco ao fechar.

Estados assíncronos cobrem carregando, vazio, sem resultados, erro, cancelamento, sucesso e nova tentativa quando honesta. O layout reserva espaço para feedback. Sessão expirada preserva trabalho local não sensível e direciona a autenticação. Rascunhos pendentes de sincronização são explicitamente rotulados.

## Público, privacidade e orçamento

Artigos públicos contêm apenas versão congelada e metadados públicos. Conversas, prompts, transcrições, áudios, sugestões e identificadores internos não aparecem no bundle nem nas respostas públicas.

O orçamento não aparece até existir medição real no backend. A interface nunca apresenta valores simulados como se fossem consumo do autor.

## Responsividade, locale e acessibilidade

Idioma e locale são `pt-BR`; datas, moeda e números usam APIs de internacionalização. O alvo é WCAG 2.2 AA. Interações têm semântica nativa, hover, foco visível, ativo, desabilitado e ocupado quando aplicável. O sistema respeita `prefers-reduced-motion`, mantém scrollbars visíveis e funciona com teclado e zoom de 200%.
