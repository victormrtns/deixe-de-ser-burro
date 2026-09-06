# Auditoria de responsividade e contrato — o que ficou registrado sem conserto

Branch `feat/front-responsivo`, 6 de setembro de 2026. Escopo auditado: site público,
biblioteca, detalhe de livro, entrada, páginas de erro, primitivas, publicação e os CSS
de `app/` e `styles/`. O workspace do estúdio (`features/workspace/`, `features/chat/`)
ficou de fora por estar em trabalho paralelo.

Método: cada rota renderizada em Chromium a 320, 390, 768, 900, 1024 e 1440px, medindo
`scrollWidth` do documento, elementos que cruzam a borda da viewport, elementos cujo
texto estoura a própria caixa, e alvos clicáveis abaixo de 24×24px (WCAG 2.2 AA, 2.5.8).
Depois das correções desta branch o resultado é zero em todas as quatro medidas, nas onze
rotas, nas seis larguras.

O que segue é o que foi **visto e não consertado**, com o motivo.

---

## 1. `PublicationStatus` não tem estado ocupado

`frontend/src/features/publishing/PublicationStatus.tsx:6`

O ledger do contrato exige "ação ocupada" no pendente de *Retirar publicação* e de
*Cancelar limpeza*. Os dois gatilhos são `onCancelCleanup()` e `onUnpublish()`, callbacks
síncronos `(): void` vindos de `WorkspacePage`. Sem mudar a assinatura para `Promise` e
sem mexer em quem chama — que está em `features/workspace/`, branch paralela — não há
como marcar `aria-busy` honestamente nem bloquear o duplo clique.

O que eu faria: trocar as props para `() => Promise<void>`, guardar `pending` local por
ação e passar `busy` ao `.text-action` (que precisaria ganhar a variante ocupada, hoje só
os botões-pílula a têm).

## 2. Artigo e livro inexistentes não caem na página 404

`frontend/src/public-site/PublicArticlePage.tsx:14`, `PublicBookPage.tsx:20`

Slug desconhecido devolve um bloco `.public-status` com "Artigo não encontrado." dentro do
layout de leitura — em um caso ainda com "Tentar novamente", que é desonesto: repetir a
busca não vai fazer o slug existir. O contrato diz que 403, 404 e falha de carregamento são
páginas próprias.

Não consertei porque a distinção depende do backend: hoje o erro de rede e o 404 chegam
indistinguíveis (`usePublicArticle` não expõe o status HTTP e `PublicBookPage` deduz o 404
de um `find` vazio sobre a lista inteira). Fazer direito é mapear `ApiError.status === 404`
para `NotFoundPage` e manter o `.public-status` só para falha de rede — mexe no adaptador,
não na tela.

## 3. Foco programático no título após navegação

O contrato pede que "após navegação, o título principal recebe foco programático quando
necessário". Nenhuma rota faz isso. É uma decisão transversal (afeta também o workspace) e
mal feita ela atrapalha: mover foco a cada troca de rota faz o leitor de tela reanunciar a
página inteira em navegações que o usuário já entendeu.

O que eu faria: um único `useRouteFocus()` chamado no elemento `<main>` de cada rota, que
foca só quando a navegação veio de um link e não de um retorno de histórico.

## 4. `.suggestion-diff` usa breakpoint de 600px

`frontend/src/features/suggestions/suggestions.css`

Único ponto do sistema que ainda não usa 780px. Deixei intocado porque o painel de sugestão
vive dentro do assistente do workspace, cuja largura não é a da viewport — o valor certo
depende da nova geometria dos painéis redimensionáveis, que é da outra branch. Quando o
workspace estabilizar, isto quer uma container query, não um media query.

## 5. Botão sem primitiva no workspace

`frontend/src/features/workspace/WorkspacePage.tsx:71` — `<button type="button">Abrir
conversa</button>`, sem classe. É defeito pelo contrato ("um botão sem classe é defeito, não
variante"). Fora do meu escopo de edição; registrado para a branch do workspace.

## 6. Corpo de texto 15px vs 17px

Já estava aberto no `docs/ui-handoff.md` (item 6) e continua aberto. `body` usa 15px,
`design.md` fixa 17px. Trocar reflui todas as telas auditadas aqui e invalidaria as medidas
acima. Decisão do autor.

## 7. Escala de 4px

Cerca de 130 valores fora da escala do `design.md` (gaps de 5, 7, 9, 18, 30px). Refluir é
redesenho, não ajuste — mesma conclusão do handoff anterior. Onde toquei em espaçamento
nesta passada foi só para destravar layout, não para normalizar a escala.

## 8. Hifenização nas capas da estante pública

`.published-book__cover strong` hifena títulos longos abaixo de 780px ("A cora-gem de não
agradar"). É correto em pt-BR e evita o texto cortado que existia antes, mas numa lombada
de livro fica estranho. A saída boa é a capa real (`coverImageUrl`), que o contrato já
prevê e o backend ainda não entrega.
