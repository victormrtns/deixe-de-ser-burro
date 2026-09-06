# Handoff de UI — o que já foi arrumado e o que ficou aberto

Branch `feat/workspace-layout`, worktree `~/wt-layout`, 6 de setembro de 2026.

Este documento existe para quem for aprimorar a UI a seguir. Ele registra o estado
depois da sabatina de componentes: o que mudou, por que mudou, e onde a interface
continua sem desenho. **Nada aqui é sugestão de estética** — as decisões de cor,
tipografia e linguagem visual continuam em `design.md`, e as regras de comportamento
em `UX-CONTRACT.md`.

## Onde está cada fonte

| Documento | O que manda | O que não manda |
|---|---|---|
| `design.md` | Cor, tipografia, linguagem visual, escala | Não é inventário de componentes. É referência externa; os cartões de feature, linhas de Send/Swap/Receive e marcas cripto que ele cita são calibragem de estilo, não coisas a construir |
| `UX-CONTRACT.md` | Rotas, títulos, donos canônicos de UI, ledger de comportamento, acessibilidade | Não define valores visuais |
| `brand/README.md` | Logo, wordmark, favicon e faixas de tamanho | — |

## O sistema de ação, depois da sabatina

Toda ação clicável é uma de três formas. Nenhum `<button>` do produto declara o
próprio preenchimento, raio ou peso.

| Forma | Primitiva | Papel |
|---|---|---|
| Pílula escura | `PrimaryButton` | A única ação escura por região |
| Pílula clara | `NeutralButton` | Secundária ao lado da primária |
| Fantasma | `GhostButton` | Saída de diálogo, baixa consequência |
| Destrutiva | `DangerButton` | Exclusão, sempre atrás de diálogo |
| Link de ação | `.text-action` | Recuperação dentro de conteúdo — tentar de novo, restaurar, lembrar |

`busy` preserva o rótulo e a largura e marca `aria-busy`. Trocar o texto por gerúndio
(`Publicando…`) é proibido: muda a geometria no meio da interação.

### O que foi corrigido

Antes disso, 45 botões se resolviam sozinhos. O que estava quebrado:

- **Sem CSS nenhum, botão default do navegador:** diálogo de publicar, histórico de
  versões (`Restaurar`, `Tentar novamente`), tela de erro ao abrir escrita, retry do
  cartão de áudio.
- **Terceira forma inventada:** o site público tinha um retângulo preto quadrado; o
  compositor do chat, um pill próprio; aceitar/descartar sugestão, outro; o diálogo de
  conflito, mais um. Quatro implementações paralelas do mesmo botão.
- **Geometria instável:** `Publicar versão` → `Publicando…` e `Aceitar alteração` →
  `Aplicando…` mudavam a largura no clique, contra o ledger.
- **`Sair` sumia no mobile:** `.text-button{display:none}` abaixo de 780px escondia a
  ação em vez do e-mail.
- **Diálogo de conflito focava a ação destrutiva.** O contrato pede foco inicial na
  opção segura.
- **`Copiar minhas alterações` copiava a string literal `'Minhas alterações'`** para o
  clipboard. Stub fingindo ser função. Removido.
- **Erro de rota usava layout de conteúdo.** Falha que impede a tela inteira agora usa
  `.route-error`, a mesma página do 403 e do 404.
- **2,5 KB de CSS morto:** 15 classes sem uma referência no TSX — `workspace-shell`
  (duplicata de `workspace-feature`), `writing-card`, `writing-copy`, `mini-rail`,
  `paper-note`, `document-scroll`, `deck`, `avatar`, `lede`, `user-message` e outras.
  35 regras removidas.

### Toasts, agora ligados

`ToastProvider` estava montado só na biblioteca e `useToast` nunca era chamado. Subiu
para `AppProviders` e confirma as operações cujo resultado não é visível na tela onde a
ação aconteceu: publicar, retirar publicação, cancelar limpeza, restaurar versão, criar
livro, criar escrita. Falha de retirar publicação e de cancelar limpeza — que antes não
tinham tratamento nenhum — viram toast de erro.

Aceitar e descartar sugestão **não** recebem toast: já se confirmam inline, no lugar
onde a ação aconteceu.

Duas armadilhas encontradas ao ligar, que valem para quem for adicionar mais toasts:

1. `restoreVersion` e `accept` capturavam a própria exceção e devolviam `Promise<void>`.
   Encadear `.then(() => notify('sucesso'))` nelas anuncia sucesso em cima de falha.
   `restoreVersion` passou a devolver `boolean`; o estado do provider de sugestão é
   quem diz o desfecho.
2. A variante `info` do toast era a única das quatro do contrato sem regra de estilo.
   Agora tem.

### Painéis redimensionáveis

O workspace ganhou separadores arrastáveis entre contexto ↔ documento ↔ assistente,
no modelo do Overleaf. As colunas de 1px que já desenhavam a hairline **são** os
separadores — não há elemento sobreposto. Arrastar com ponteiro, setas no teclado
(16px, 48px com Shift), duplo clique reseta, largura guardada em `localStorage`.
`role="separator"` com `aria-valuenow`. Some abaixo de 780px.

A largura não passa pelo estado do React de propósito: um re-render no meio do arrasto
faria o painel pular de volta.

### Espaçamento

Corrigidos os pontos onde texto e botão estavam colados: rótulo → texto da mensagem no
chat (5,6px), botões da nav lateral (5px), bloco "Livro ativo" (2px), ícones do
cabeçalho (6px), abas do documento (encostadas), campos de formulário (6px), ações de
diálogo (10px).

Não foi feito rescale global. O codebase tem cerca de 130 valores fora da escala de 4px
do `design.md`; refluir tudo é redesenho, não ajuste.

---

## O que continua sem desenho — trabalho para a próxima passada

### 1. Excluir livro e excluir escrita não existem

`DangerButton` é a única forma de ação sem uso em produção — aparece só no teste de
primitivas. O autor precisa poder excluir livro e escrita, e o backend já expõe
`DELETE /api/books/{id}` e `DELETE /api/writings/{id}`.

Falta: onde mora o gatilho (menu no cartão? ação dentro do livro?), o diálogo destrutivo
nomeando objeto e consequência, e o que acontece com as escritas de um livro excluído.
O contrato já registra a regra; a interface não existe.

### 2. Aceitar sugestão é um stub

`WorkspacePage` passa `accept={() => Promise.resolve()}` e a sugestão exibida é uma
constante no arquivo. O painel inteiro é maquete. Todo o fluxo de sugestão — de onde
ela vem, como chega, o que acontece com o texto — está por fazer.

### 3. Histórico de versões é um `<details>` sem desenho próprio

Ganhou o mínimo para não parecer quebrado: o summary herda o estilo dos itens da nav e
as linhas viram uma grade de duas colunas. Não é um componente pensado. Comparar
versões, ver o que mudou, e desfazer uma restauração não existem.

### 4. Áudio está dormente e divergente

`Recorder.tsx` e `audio.css` não são renderizados em lugar nenhum — notas de áudio estão
fora desta fase, e o painel do assistente diz isso ao usuário. **Manter como está, por
decisão do autor.** Quando voltar, o CSS precisa de revisão: usa pílula com borda
própria, fora das quatro formas.

### 5. Código morto — removido

`MarginRail.tsx` (o trilho de marginalia do `DESIGN.md` superado), `MarkdownEditor.tsx`
(editor CodeMirror que nada renderizava — o editor real é um `textarea`), `useAutosave.ts`
(debounce reimplementado em `WorkspaceProvider`) e `conversationEvents.ts` (só o próprio
teste importava) foram apagados em 2026-09-06, junto com as duas dependências de
CodeMirror que ninguém usava. O `DESIGN.md` superado também saiu: dois arquivos chamados
`design.md` e `DESIGN.md` no mesmo diretório colidem em macOS e Windows.

O áudio fica, por decisão do autor, mesmo dormente.

### 6. Corpo de texto — decidido: 15px

`design.md` trazia `--text-body: 17px`, herdado da referência de origem, e o produto
sempre usou 15px em `body`. O autor decidiu por **15px** em 2026-09-06: o estúdio é
ferramenta de trabalho e não página de marketing, e a leitura pública já ganha escala
pela classe `.prose`, que usa `clamp(1rem, 0.96rem + 0.2vw, 1.125rem)`. `design.md` foi
corrigido; nenhuma mudança de código, porque o produto já estava assim.

### 7. Dois diálogos, duas implementações

`ui/Dialog` é `AlertDialog` do Radix (confirmação); `LibraryFormDialog` tem o próprio
`Frame` sobre `react-dialog` (criação com formulário). São papéis diferentes e ambos
ficam — o contrato foi atualizado para registrar os dois donos. Visualmente devem
permanecer indistinguíveis; se um mudar, o outro muda junto.

### 8. Eyebrows decorativos

Todo diálogo carrega um rótulo em caixa alta acima do título — "Confirmação", "Novo
começo". A mesma marcação aparece em várias seções. Não foi tocado nesta passada porque
é decisão de linguagem, não de componente.

### Foco: o anel azul nas superfícies de escrita

`globals.css` aplicava a mesma regra de foco a botão, link, `input` e `textarea`:
anel de 2px **deslocado 3px para fora** mais um brilho de 3px. Em campo de texto,
`:focus-visible` casa também no clique do mouse — o navegador considera que campo de
escrita sempre precisa de indicador —, então bastava clicar para escrever e aparecia
um halo azul duplo saltando por cima dos vizinhos. No editor, que é um `textarea` de
760px por painel inteiro, virava uma moldura azul em volta de tudo.

O `.markdown-editor` até declarava `outline:0`, mas `textarea:focus-visible` (0,1,1)
vence `.markdown-editor` (0,1,0) na especificidade. A tentativa do autor nunca teve efeito.

Agora: botões e links seguem com o anel de fora, que é o certo para eles. Campos de
texto recebem o anel **por dentro** da própria borda, sem brilho — o campo acende em
vez de ganhar halo. O editor não recebe anel nenhum: o cursor é o indicador, como no
Overleaf, e o painel marca a borda esquerda em azul para quem navega por teclado.

### Estúdio: o que mais estava errado

- **`role="tab"` que não controlava nada.** As três abas do documento não tinham
  `aria-controls`, não havia `tabpanel`, e as setas não trocavam de aba. Agora seguem o
  padrão WAI-ARIA: setas navegam, só a aba ativa entra na ordem de tabulação, e o canvas
  é o painel que elas controlam.
- **`100vh` no estúdio.** Em navegador móvel a barra de endereço torna `100vh` maior que
  o viewport visível, cortando o rodapé do layout. Trocado por `100dvh`.
- **"Lado a lado" em 390px** eram duas colunas de ~190px. No mobile as abas escondiam o
  botão em vez de resolver o layout; agora o modo empilha.
- **Botões da nav do assistente** tinham só a classe `is-active`: leitor de tela não
  sabia qual painel estava aberto. Ganharam `aria-pressed`.
- **`SaveStatus`** desenhava o próprio link de ação no CSS do workspace. Passou a usar
  `.text-action`.
- **Estado dos painéis** agora persiste como no Overleaf — as larguras já persistiam, o
  aberto/fechado não.

### Fica registrado: os botões de ícone do cabeçalho

Os três controles de painel no topo do workspace são quadrados de 32px desenhados em
`workspace-sovereign.css`. Passam no alvo mínimo de 24px da WCAG 2.2, e são o formato
certo para uma barra de ferramentas ao estilo Overleaf — mas são uma sexta forma de ação
que o contrato não nomeia. Ou viram uma primitiva `.icon-button` em `ui/`, ou o contrato
passa a listar a forma. Não resolvi para não colidir com as branches paralelas.

---

## Como verificar

```bash
cd frontend
npm run typecheck && npm run lint && npm run test:unit
npm run test:a11y && npm run verify:premium
npm run build && npm run verify:bundles
```

Estado atual: 63 testes, 0 erros de lint, axe sem violações críticas ou sérias,
0 violações no check premium, bundle público sem módulos privados.

Para ver rodando, com o backend do Compose de pé:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5174
```
