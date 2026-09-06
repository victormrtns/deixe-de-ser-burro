# Auditoria de refinamento visual — deixedeserburro

Branch: `feat/brand-visual-audit` · worktree `wt-brand` · duas rodadas (2026-09-05)

---

## 1. Reconciliação — **corrigida por decisão do autor**

> A rodada 1 desta auditoria concluiu que `DESIGN.md` vencia o contrato de tokens. **Essa conclusão foi revertida.**

| Camada | Vence | Nota |
|---|---|---|
| **Cor, tipografia e linguagem visual** | **`design.md`** | Decisão do autor (2026-09-05). É a paleta canônica do produto e é ela que está em `tokens.css`. |
| **Ativos** | **`brand/`** | Arquivos vetoriais finais. `brand/README.md` manda no dimensionamento e no uso. |
| **`DESIGN.md`** | **Superado** | Recebeu um aviso no topo. Apagado depois, em 2026-09-06: dois arquivos com o mesmo nome diferindo só na caixa colidem em macOS e Windows. |

**Nome do produto: `deixedeserburro`.** "Entrelinhas" está morto. Com isso, o conflito de duas marcas na mesma linha — que na rodada 1 impedia o uso do wordmark — deixou de existir.

### O problema de status, resolvido dentro do `design.md`

A rodada 1 argumentou que `success`/`danger` precisavam vir do `DESIGN.md` porque `design.md` não tem verde/vermelho de status com contraste AA. O argumento estava errado — a saída não era importar cor de fora, era **parar de usar status como texto colorido**.

`design.md` já diz, nas próprias linhas dos tokens, que grass-green, mint e alert-red são *"supporting accent, not a status color"* e que mint/honey/alert-red são *"wash for highlight backgrounds"*. E descreve o componente **Status Badge Pill**: pill 9999px, fundo no acento, texto escuro. Ou seja, o padrão do sistema é **o acento carrega o fundo; o texto vai em tinta escura**.

Medições feitas (WCAG 2.x, fundo creme `#fbfaf9`):

| Combinação | Razão | |
|---|---|---|
| Grass Green `#00c978` como **texto** sobre creme | 2,09:1 | reprova |
| Gold `#d48f00` como **texto** sobre creme | 2,61:1 | reprova |
| Alert Red `#ff2b3a` como **texto** sobre creme | 3,56:1 | reprova em texto normal |
| Branco sobre Alert Red (botão destrutivo anterior) | 3,71:1 | reprova |
| **Ink `#121212` sobre Alert Red** | **5,05:1** | passa |
| **Ink `#121212` sobre Mint `#00ca48`** | **8,51:1** | passa |
| **Ink `#121212` sobre Honey `#ffbb26`** | **11,05:1** | passa |
| **Ink `#121212` sobre Sun Yellow `#ffcd6c`** | **12,67:1** | passa |
| **Ink `#121212` sobre Sky Blue `#64c6ff`** | **9,87:1** | passa |

O padrão wash+tinta resolve **todos** os casos de status com folga. Nenhuma cor foi inventada e nada foi importado do `DESIGN.md`.

---

## 2. `tokens.css` — o que mudou

Só **três** tokens de cor divergiam de fato do `design.md`. Os outros dez já coincidiam exatamente (canvas, surface, stone, ink, charcoal, border, link, ember, focus).

| Token | Antes | Agora | Papel em `design.md` |
|---|---|---|---|
| `--color-text-muted` | `#6f6d69` (fora da paleta) | `#474645` | Body Brown. Contraste sobe de 4,95:1 → **9,03:1**. |
| `--color-success` | `#007a4d` (fora da paleta) | `#00ca48` | Mint — agora **fundo**, nunca texto |
| `--color-danger` | `#c91d2e` (fora da paleta) | `#ff2b3a` | Alert Red — agora **fundo/borda**, nunca texto |
| `--color-pending` | `#d48f00` | `#ffbb26` | Honey. `#d48f00` (Gold) é papel de *texto*; o produto só usa este token como preenchimento, e o Status Badge Pill do `design.md` especifica honey. |

**Adicionado:** `--color-status-ink: #121212` (a tinta que vai sobre qualquer acento de status).

**Removidos** — a lavagem virou desnecessária quando o acento passou a ser o próprio fundo: `--color-pending-wash`, `--color-pending-ink`, `--color-success-wash`.

**Cores ilustrativas remapeadas para os fills nomeados do `design.md`:**

| Antes (inventado na rodada 1) | Agora |
|---|---|
| `--color-cover-blue: #b8e0ff` | `--color-illustration-sky: #64c6ff` (Sky Blue) |
| `--color-note: #fff4bd` | `--color-illustration-sun: #ffcd6c` (Sun Yellow) |
| `--color-cover-orange: #ffb399`, `--color-cover-green: #a7e3c7` | **removidos** — só existiam nas regras `.book-cover.orange` / `.book-cover.green`, ambas código morto (só `.blue` é usada no TSX). As regras foram apagadas junto. |

`--color-annotation-wash` deixou de ser um hex avulso (`#ffdfd2`, sem equivalente no `design.md`) e passou a ser derivado da própria paleta: `color-mix(in srgb, var(--color-annotation) 18%, var(--color-canvas))`.

Os dois hovers (`--color-ink-hover`, `--color-danger-hover`) também deixaram de ser hexes inventados e viraram `color-mix` sobre a paleta. `#a91423` estava órfão de qualquer forma — era derivado do vermelho antigo.

**Resultado:** `tokens.css` contém hoje **apenas valores do `design.md`**, mais dois cinzas de scrollbar (ver §6.2).
Zero literais hexadecimais em qualquer outro `.css`; zero literais de cor em `.tsx`.

### Os call sites de status

| Arquivo | Antes | Agora |
|---|---|---|
| `ui.css` `.button--danger` | `background: danger; color: white` (3,71:1) | `color: var(--color-status-ink)` (5,05:1) |
| `ui.css` `.field__error` | `color: var(--color-danger)` | `color: var(--color-ink)` — a borda vermelha do `aria-invalid` já carrega a cor |
| `app.css` `.status-chip` | wash bege + tinta `#755000` | `background: var(--color-pending); color: var(--color-status-ink)` |
| `app.css` `.status-chip--published` | wash verde + texto `#007a4d` | `background: var(--color-success); color: var(--color-status-ink)` |
| `chat.css` `.chat-error` | `color: var(--color-danger)`, sem outro portador | barra lateral vermelha de 3px + texto em tinta — **reaproveita o padrão que `.recorder [role=alert]` já usava** |
| `chat.css` `.chat-stop` | `color: var(--color-danger)` | texto em tinta; o `inset … 1px danger` que já existia carrega a cor |
| `audio.css` `[role=alert]` | `color: var(--color-danger)` | texto em tinta; a barra vermelha já existia |
| `workspace.css` `.workspace-save--failed` | `color: var(--color-danger)` | texto em tinta; o ponto vermelho `:before` já existia |

Verificação: `grep -rnoE "(^|[;{ ])color:\s*var\(--color-(danger|success|pending)\)" src --include=*.css` → **vazio**. Todos os 21 usos restantes desses três tokens são `background`, `border-color`, `border-left` ou `text-decoration-color`.

---

## 3. Renomeação — alcance

`grep -rn "Entrelinhas"` no worktree: **77 ocorrências em 37 arquivos**.

**Renomeadas nesta rodada: 25 ocorrências em 17 arquivos, todas no `frontend/`.**

| Grupo | Arquivos |
|---|---|
| Títulos de documento | `index.html`, `SignInPage`, `LibraryPage`, `PublicLibraryPage`, `PublicArticlePage`, `PublicBookPage`, `PublicArticlesPage`, `PublicBooksPage`, `PublicAboutPage`, `RouteErrorPage` (×2) |
| `aria-label` de `<main>` | `router.tsx`, `SignInPage`, `LibraryPage`, `BookDetailPage`, `RouteErrorPage` (×2), `PublicReadingShell` |
| Texto de página | `PublicAboutPage` ("… é uma publicação independente…"), `PublishedBookCard` (marca impressa na capa) |
| Testes que asseveram esses textos | `router.test.tsx` (×5), `smoke.test.tsx` (×2) |
| Artefato estático | `public/design-review/index.html` (`<title>`) |

Além da string literal, o trocadilho do painel decorativo do login foi refeito: `<span>Entre</span><span>linhas</span>` → `<span>deixedeser</span><span>burro</span>`, seguindo a quebra que o `brand/README.md` descreve (peso 400 em `deixedeser`, 750 em `burro`).

**Não tocado, conforme instruído** — ver o apêndice em §7.

---

## 4. Wordmark e assinatura

Com o nome resolvido, `wordmark.svg` e `logo.svg` entraram em uso.

Antes disso, uma correção da rodada 1: eu tinha usado `logo-icon.svg` a 26px e 34px. O `brand/README.md` diz *"Use o favicon entre 16 e 48 px e o mascote completo a partir de 64 px"* — as duas aplicações **violavam a orientação da própria marca**. Corrigido.

| Lugar | Aplicação |
|---|---|
| Nav do studio (`LibraryPage`) | `favicon.svg` a 30px (`alt=""`, decorativo) + `wordmark.svg` (`alt="deixedeserburro"`, **conteúdo**) |
| Cabeçalho público (`PublicReadingShell`) | `favicon.svg` a 38px (`alt=""`) + `wordmark.svg` (`alt="deixedeserburro"`), preservando o subtítulo "notas à margem" |
| Sign-in (`SignInPage`) | `logo.svg` — a assinatura horizontal completa — a 340px de largura. É o **único lugar do produto com espaço para os ≥320px que o README pede**. |

`public/brand/logo-icon.svg` foi removido (nenhuma aplicação restante cai na faixa ≥64px). Nos headers a marca é o favicon (dentro da faixa 16–48px) e o nome é o wordmark; juntos reconstituem a assinatura horizontal na escala do cabeçalho.

O `alt` do wordmark é o nome da marca porque **o wordmark é conteúdo, não decoração** — é a única coisa que nomeia o produto ali. O mascote ao lado leva `alt=""` para não duplicar o nome no leitor de tela.

---

## 5. `design.md` e `DESIGN.md`

**`design.md`** (agora canônico) — corrigidas as duas incoerências, e só elas:

1. **`Family` → `Bricolage Grotesque`** na tabela de tipografia (título da entrada, campo *Substitute*, campo *Role*), nos dois Do's/Don'ts que citavam a face, e no `--font-family` do Quick Start. O campo *Substitute* agora registra o motivo: os ativos de `brand/` estão desenhados em Bricolage (peso 400 em `deixedeser`, 750 em `burro`), e `Family` é proprietária e não instalada.
2. **Seção *Imagery* reescrita.** Descrevia mascotes cartoon chapados com olhos de pontinho e membros de palito, traço fino — o oposto do ativo real. Agora descreve o que `brand/` de fato é: line-art de traço pesado, o burro de perfil saindo de um livro aberto, fita laranja marcando a página, roundel oldschool; peso no contorno e não no preenchimento; os arquivos canônicos e as regras de dimensionamento do `brand/README.md`; e a restrição de que os fills de acento servem a capas e painéis, nunca a status.

**`DESIGN.md`** — nota `[!IMPORTANT]` no topo dizendo que está superado, que `design.md` é canônico para cor/tipografia/linguagem visual, apontando os pontos exatos em que ele diverge (`success`, `danger`, `textMuted`) e registrando que o padrão de status correto é fundo no acento + texto escuro. Mantido como registro histórico.

---

## 6. Divergências que sobraram

### 6.1 Status: nenhuma

Todo caso de status fechou dentro do `design.md` com o padrão wash+tinta. Não sobrou nenhum ponto precisando de texto colorido sem cor AA disponível. **Nada a decidir aqui.**

### 6.2 Papéis que o `design.md` simplesmente não cobre

Não são divergências de valor — são lacunas do documento. Deixei como está e registro:

- **Face monoespaçada.** `design.md` não define nenhuma. O produto precisa de mono (editor Markdown, micro-rótulos, metadados). `--font-code` continua `IBM Plex Mono`, herdado do `DESIGN.md`.
- **Cinzas de scrollbar** (`#a8a39c`, `#77726c`). Sem papel correspondente no `design.md`, e o `UX-CONTRACT.md` trata scrollbar como contrato de comportamento. Preservados.
- **Estados de hover.** `design.md` é uma referência estática, não especifica hover. Os dois hovers agora são `color-mix` derivado da paleta, então não introduzem cor nova.

### 6.3 Contraste AA na própria paleta do `design.md` — **precisa da sua chamada**

Duas cores canônicas reprovam AA como texto de tamanho normal sobre creme, e **nenhuma delas é status**, então o padrão wash não as resolve:

| Token | Uso | Contraste sobre `#fbfaf9` |
|---|---|---|
| `--color-link` `#0086fc` | links inline, `.route-error a`, `.workspace-save button`, `.publication-status a` | **3,46:1** — reprova AA (mínimo 4,5:1) |
| `--color-annotation` `#ff3e00` | eyebrows, kickers, `.row-index`, `.article-meta`, `.margin-rail` | **3,39:1** — reprova AA |

Ambas são pré-existentes, não regressão desta rodada, e ambas estão no `design.md` exatamente nesses papéis (Link Blue: *"inline links"*; Ember Orange: *"inline links and feature callouts"*). **Não inventei substituto.** As opções são suas:

- aceitar como está e assumir a não-conformidade;
- restringir as duas a texto ≥18,66px/bold, onde 3:1 basta (a maioria dos usos de ember já é micro-rótulo em caixa alta — mas micro-rótulo é *pequeno*, então isso não salva);
- escurecer os dois valores no `design.md`, o que muda a paleta canônica;
- manter a cor e adicionar sublinhado/peso como portador redundante, o que resolve "cor não opera sozinha" mas **não** resolve o contraste.

O `test:a11y` não pega isto: a regra `color-contrast` do axe está desligada na suíte (`accessibility.test.tsx` linha 12).

### 6.4 Corpo de texto a 15px vs. 17px no `design.md`

`design.md` fixa `--text-body: 17px`; o produto usa 15px em `body`. Com `design.md` canônico para tipografia, isto é divergência real. **Não alterei** — mudar a base tipográfica reflui todas as telas, o que é redesenho e estava fora do escopo. Além disso `tokens.css` não tem tokens de tamanho de fonte, então não havia o que "reconciliar" no arquivo. Registro para uma decisão sua.

### 6.5 Resíduos no `design.md` fora do escopo autorizado

Duas linhas ainda carregam a origem do documento e contradizem a seção *Imagery* que reescrevi. Você disse para não tocar no resto, então não toquei:

- linha 1: `# Family — Style Reference`;
- linha 6, o parágrafo de visão geral: *"hand-drawn characters and scattered confetti shapes… the cartoon illustrations carry all the emotional weight"*.

Recomendo uma passada curta trocando o título por `# deixedeserburro — Style Reference` e realinhando o parágrafo à nova *Imagery*. Não executado.

---

## 7. Apêndice — "Entrelinhas" fora do frontend (52 ocorrências, 20 arquivos)

> **Resolvido em 2026-09-06.** A prosa (`UX-CONTRACT.md`, `ia/`, `docs/`, `DESIGN.md`, `Description=` das units) e as strings de backend que chegam ao usuário/modelo foram renomeadas. Os identificadores de infra permanecem `entrelinhas` por decisão registrada em `README.md`.

Não tocado à época (`ia/` e `docs/` estão sendo editados por outros agentes; identificadores de infra não devem mudar aqui). Lista para uma passada separada:

**Contrato (o mais urgente — ficou desatualizado no instante em que os títulos mudaram):**
- `UX-CONTRACT.md` — 7 ocorrências, incluindo a **tabela de rotas e títulos inteira** (linhas 15–20), que agora descreve títulos que o frontend não emite mais.

**Documentação e estudo:**
- `ia/CONTEUDOS.md` (3), `ia/ROADMAP.md` (2), `ia/PARTE-1-CONVERSA-CONTEXTUAL.md` (3)
- `docs/handoffs/current.md` (1)
- `docs/superpowers/plans/…-public-landing-and-unified-conversation.md` (5), `…-visual-identity-frontend.md` (2), `…-backend-crud-infrastructure.md` (1)
- `docs/superpowers/specs/…-contextual-ai-conversation-design.md` (4), `…-public-landing-and-unified-conversation-design.md` (3), `…-backend-crud-infrastructure-design.md` (1)
- `DESIGN.md` (1, na visão geral — o título já foi ajustado junto com a nota de superado)
- `.superpowers/brainstorm/…/landing-directions.html` (1)

**Backend — inclui strings que chegam ao usuário/modelo:**
- `backend/app/main.py:42` — `FastAPI(title="Entrelinhas API")` (aparece no OpenAPI/docs)
- `backend/app/assistant/context.py:21` — **prompt do sistema**: *"Você é o assistente do Entrelinhas…"*
- `backend/app/assistant/editorial.md:5` — `# Linha editorial do Entrelinhas`
- `backend/tests/unit/test_assistant_context.py:143` e `test_openai_gateway.py:35` — asseveram essas strings
- `backend/migrations/versions/0001_initial.py:1` — docstring (histórico, não renomear)

**Infra — não renomear sem migração deliberada:**
- `ops/cleanup.service:2`, `ops/cleanup.timer:2` — `Description=` de units systemd
- Nome do pacote npm `entrelinhas-frontend` em `frontend/package.json`, `PUBLIC_ORIGIN`, nomes de container e de banco: **não verificados nem tocados**, conforme instruído.

---

## 8. Verificação

Saída real, após todas as mudanças desta rodada.

```
$ npm --prefix frontend run lint
✖ 15 problems (0 errors, 15 warnings)
```
Mesmas 15 warnings pré-existentes (`react-refresh/only-export-components` ×12, `react-hooks/exhaustive-deps` ×2, +1). Nenhuma em arquivo tocado.

```
$ npm --prefix frontend run typecheck
> tsc -b --pretty false
(sem saída, exit 0)
```

```
$ npm --prefix frontend run test:unit
 Test Files  16 passed (16)
      Tests  58 passed (58)
   Duration  6.58s
```

```
$ npm --prefix frontend run build
✓ built in 13.48s
EXIT=0
<title>deixedeserburro — Leituras que continuam</title>
dist/favicon.svg  dist/brand/logo.svg  dist/brand/wordmark.svg
```
Aviso pré-existente de chunk >500 kB (mermaid/katex/cytoscape), não relacionado.

```
$ npm --prefix frontend run verify:premium
Premium static check: 79 arquivos, 0 violações.
```

```
$ npm --prefix frontend run test:a11y
 Test Files  1 passed (1)
      Tests  2 passed (2)
```
Cobre `SignInPage` (que ganhou o `logo.svg` e o texto renomeado) e `PublicArticlePage` (que renderiza pelo `PublicReadingShell`, com o wordmark). Nenhuma violação séria ou crítica. **Ressalva importante:** a regra `color-contrast` está desligada nesta suíte, então ela **não** valida o padrão wash+tinta — o que valida são as medições da §1, feitas pela fórmula de luminância relativa da WCAG.

Auditorias estáticas:
```
$ grep -rnoE "#[0-9a-fA-F]{3,8}" frontend/src --include=*.css | grep -v tokens.css
(vazio)

$ grep -rnoE "(^|[;{ ])color:\s*var\(--color-(danger|success|pending)\)" frontend/src --include=*.css
(vazio)

$ grep -rn "Entrelinhas" frontend/src frontend/index.html frontend/public
(vazio)
```

### Sem verificação em navegador

O Chromium não inicia nesta máquina:
```
chrome-headless-shell: error while loading shared libraries:
libnspr4.so: cannot open shared object file: No such file or directory
```
Tentado uma vez na rodada 1, sem workaround. **Nada neste documento foi verificado visualmente.** O wordmark, a assinatura no sign-in, o favicon e as novas cores de status **não foram vistos renderizados** — precisam da sua conferência ocular ou de uma máquina com `libnspr4`.

---

## 9. O que continua deliberadamente intocado

- **~120 espaçamentos fora da base 4px** — fechar é redesenhar.
- **~8 KB de CSS morto em `app.css`** (≈35 classes do shell protótipo: `.workspace-shell`, `.assistant`, `.margin-rail`, `.draft`, `.paper-note`, `.mini-rail`, `.avatar`, `.budget`…). PR próprio, com varredura de `className` dinâmico antes de apagar. Nesta rodada só saíram `.book-cover.orange` e `.book-cover.green`, porque o único conteúdo delas era uma cor fora da paleta.
- **Raios de lombada de livro** (`4px 9px 9px 4px` etc.) — geometria ilustrativa; `design.md` autoriza formas orgânicas em capas e ilustração.
- **Pesos de fonte não canônicos** (560/580/620/650) — possíveis por a fonte ser variável; normalizar é redesenho tipográfico.
- **Gate visual no `verify:premium`.** `check-anti-patterns.mjs` só varre `.ts|.tsx` procurando `alert(`/`dangerouslySetInnerHTML`/mock/fetch — **não tem regra visual e nem lê `.css`**. Nada aqui o duplica. Um gate que reprovasse hex fora de `tokens.css`, gradiente e raio fora de escala seria ~10 linhas no mesmo script, mas não foi pedido e exigiria lista de exceções para os raios de lombada.

---

## Histórico da rodada 1

Fechado antes desta reconciliação, e ainda válido: `--shadow-overlay` reduzido de `0 24px 80px rgb(18 18 18/18%)` para o teto de overlay do `design.md`; `--shadow-raised` declarado (era consumido em `public-site.css` sem existir); favicon e `apple-touch-icon` ligados pela primeira vez; `.brand-mark` removida (uma marca concorrente desenhada em CSS — três barras inclinadas — que já era código morto); raios de chrome fora da escala (16/18/8/7px) normalizados; zero gradientes no codebase, confirmado.
