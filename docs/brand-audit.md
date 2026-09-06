# Auditoria de refinamento visual — Entrelinhas × marca

Branch: `feat/brand-visual-audit` · worktree `wt-brand` · data: 2026-09-05

---

## 1. Reconciliação das três fontes de verdade

Existem três documentos que descrevem a identidade e eles **discordam**. Veredito por camada:

| Camada | Vence | Por quê |
|---|---|---|
| **Contrato de tokens** (nomes, valores, geometria) | **`DESIGN.md`** | É o único que já está implementado em `frontend/src/styles/tokens.css`, é referenciado pelo `UX-CONTRACT.md` (linha do mapa canônico: "Scrollbar → source of truth `DESIGN.md`") e pelo `brand/README.md` ("As cores seguem os tokens de `frontend/src/styles/tokens.css`"). Trocar por `design.md` significaria renomear todos os tokens do produto por zero ganho. |
| **Tipografia de display** | **`DESIGN.md` (Bricolage Grotesque)** | Desempate feito pelos ativos reais: `brand/README.md` diz explicitamente que o wordmark usa **"Bricolage Grotesque, peso 400 em `deixedeser` e 750 em `burro`"**. A `Family` do `design.md` é proprietária, não está instalada e não é distribuível. `design.md` inclusive já prevê substituto. Bricolage não é um *fallback*: é a face da marca impressa nos arquivos finais. |
| **Linguagem visual e regras de elevação/forma** | **`design.md`** | É o documento mais detalhado e mais recente sobre *como* a superfície deve parecer: borda interna hairline no lugar de sombra, planura estrita, raios nomeados, escala tipográfica, gaps de seção. `DESIGN.md` diz as mesmas coisas em versão resumida — não há conflito real, só granularidade. |
| **Ativos e nome da marca** | **`brand/`** | São os arquivos que efetivamente vão para produção. Vetoriais, independentes de fonte, com paleta declarada. |

**Conflitos que NÃO devem ser dissolvidos em silêncio** (viram decisões abertas na seção 5):

1. `design.md` chama a face de display de `Family`; `DESIGN.md` e `brand/` dizem `Bricolage Grotesque`.
2. `DESIGN.md` tem três cores que `design.md` não tem: `success #007a4d`, `danger #c91d2e`, `textMuted #6f6d69`. Elas **são necessárias** — `design.md` não oferece um verde/vermelho de status com contraste AA sobre papel creme (`#00c978` e `#ff2b3a` não passam em texto). Mantidas.
3. O produto se chama **Entrelinhas**; a marca em `brand/` se chama **deixedeserburro**. Não é divergência de estilo, é divergência de nome.
4. A paleta ilustrativa de `design.md` (mascotes storybook, confete, `#64c6ff`, `#ff58ae`, `#9f4fff`…) descreve uma *landing page de carteira cripto*, não este produto. `DESIGN.md` restringe corretamente: "cores ilustrativas adicionais pertencem somente a capas e estados vazios". Seguido.

**Resumo operacional:** `DESIGN.md` é o contrato; `design.md` é o manual de execução visual; `brand/` é o ativo. Onde os três se cruzam, `brand/` decide.

---

## 2. Inventário dos tokens

`frontend/src/styles/tokens.css` tinha 24 tokens. Todos os 13 tokens de cor estavam em uso. Nenhum token órfão.

**Um token era usado sem existir:**

- `--shadow-raised` — consumido em `public-site.css:7` (`.published-book>a:hover`) e **nunca declarado**. O hover do cartão de livro publicado era CSS morto: a transição `box-shadow .18s ease` animava para `initial`. Corrigido.

---

## 3. Tabela de lacunas

Severidade: **A** = contradiz a marca de forma visível · **B** = bypassa o sistema de tokens · **C** = ruído / dívida.

### 3.1 Ativos da marca — a lacuna real

| # | Onde | Violação | Sev | Status |
|---|---|---|---|---|
| 1 | `frontend/index.html` | Zero `<link rel="icon">`. A aba do navegador mostrava o globo padrão do Vite. | **A** | **Corrigido** |
| 2 | `frontend/index.html` | Sem `apple-touch-icon`. `brand/png/icon-180.png` existe e não era usado. | **A** | **Corrigido** |
| 3 | `frontend/public/` | Continha apenas `design-review/`. **Nenhum dos 17 arquivos de `brand/` era referenciado em lugar algum do app.** | **A** | **Corrigido** (favicon, .ico, apple-touch-icon, logo-icon) |
| 4 | `app.css:1` `.brand-mark` | Uma **marca concorrente desenhada em CSS**: três barras inclinadas em tinta + laranja, `border-radius:4px 4px 1px 1px`. Não é o burro. Além disso já era CSS morto (nenhum `className="brand-mark"` no código). | **A** | **Corrigido** (removida, substituída pelo mascote real) |
| 5 | `LibraryPage.tsx:22` | Header privado renderizava `<span className="brand">Entrelinhas</span>` — só texto, sem símbolo. | **A** | **Corrigido** |
| 6 | `PublicReadingShell.tsx:7` | Header público idem — a superfície voltada ao leitor não tinha marca nenhuma. | **A** | **Corrigido** |
| 7 | `frontend/index.html` | Sem `manifest.webmanifest` e sem `og:image`. | **C** | **Adiado** — ver §4 |

### 3.2 Elevação

| # | Onde | Violação | Sev | Status |
|---|---|---|---|---|
| 8 | `tokens.css` `--shadow-overlay` | Era `0 24px 80px rgb(18 18 18 / 18%)`. `design.md` proíbe sombra acima de `rgba(0,0,0,0.04)` fora de overlays e fixa o teto de overlay em `rgba(0,0,0,0.15) 0 0 24px 0`. Offset de 24px + blur de 80px + 18% é "cartão flutuante genérico", explicitamente proibido em `DESIGN.md`. Afetava `.dialog` e `.toast`. | **A** | **Corrigido** → `0 0 24px 0 rgb(0 0 0 / 15%)` |
| 9 | `public-site.css:7` | `var(--shadow-raised)` indefinido. | **B** | **Corrigido** → declarado como o "Subtle Drop on Cards" do `design.md`: `0 1px 6px 0 rgb(0 0 0/4%), 0 0 24px 0 rgb(0 0 0/5%)` |
| 10 | `app.css:5` `.detail-cover` | `box-shadow:inset 4px 0 rgb(18 18 18 / 8%)` | — | **Conforme.** É `inset`, simula a lombada do livro. `design.md` só proíbe *drop* shadows. |

Auditadas 14 declarações de `box-shadow` no total. As demais são `var(--shadow-surface)` (a hairline inset canônica) ou anéis de 1px — todas conformes.

### 3.3 Gradientes

| # | Resultado |
|---|---|
| 11 | `grep -riE "gradient" src/` → **0 ocorrências**. Nenhuma violação. |

### 3.4 Cor — literais que bypassavam os tokens

18 literais hexadecimais fora de `tokens.css`. Todos eliminados.

| # | Onde | Literal | Sev | Status |
|---|---|---|---|---|
| 12 | `globals.css:75` `::selection` | `#ffdfd2` | B | → `--color-annotation-wash` |
| 13 | `ui.css:34` `.button--primary:hover` | `#2a2a29` | B | → `--color-ink-hover` |
| 14 | `ui.css:40` `.button--danger:hover` | `#a91423` | B | → `--color-danger-hover` |
| 15 | `app.css:2,3,5,8` (4×) | `#ffdfd2` (avatar do assistente, ícone de estado vazio, marca do login, seleção) | B | → `--color-annotation-wash` |
| 16 | `app.css:2,5,8` (3×) | `#b8e0ff` (capa de livro, painel do login) | B | → `--color-cover-blue` |
| 17 | `app.css:2` | `#ffb399` | B | → `--color-cover-orange` |
| 18 | `app.css:2` | `#a7e3c7` | B | → `--color-cover-green` |
| 19 | `app.css:3` `.paper-note` | `#fff4bd` | B | → `--color-note` |
| 20 | `app.css:5` `.writing-row:hover` | `#fffdfb` — quase-canvas inventado | B | → `var(--color-canvas)` |
| 21 | `app.css:5` `.status-chip` | `#fff4d1` / `#755000` | B | → `--color-pending-wash` / `--color-pending-ink` |
| 22 | `app.css:5` `.status-chip--published` | `#dff4e9` | B | → `--color-success-wash` |
| 23 | `suggestions.css:1` `del`/`ins` | `#c91d2e12` / `#007a4d12` — duplicavam `--color-danger` e `--color-success` em hex de 8 dígitos | B | → `color-mix(in srgb, var(--color-*) 7%, transparent)` |
| 24 | `tokens.css` scrollbar | `#a8a39c`, `#77726c` — cinzas fora da paleta | C | **Mantido.** Geometria de scrollbar é contrato documentado no `UX-CONTRACT.md`; mexer aqui é mudança de comportamento, não de marca. |

**Cores em uso que não estão na paleta do `design.md`:** as cores de capa (`#b8e0ff`, `#ffb399`, `#a7e3c7`, `#fff4bd`, `#ffdfd2`) são lavagens pastel dos acentos do `design.md`. `DESIGN.md` autoriza explicitamente: *"cores ilustrativas adicionais pertencem somente a capas e estados vazios"*. Decisão: **tokenizar, não repintar.** Elas ficam nomeadas e confinadas ao seu papel; nenhuma virou status nem preenchimento de botão.

Verificação: `grep -rnoE "#[0-9a-fA-F]{3,8}" src --include=*.css | grep -v tokens.css` → **vazio**. Nenhum literal de cor em `.tsx`.

### 3.5 Raio

Escala: 6 / 10 / 12 / 9999. `design.md` acrescenta 32px para pílulas de botão.

| # | Onde | Antes | Sev | Status |
|---|---|---|---|---|
| 25 | `ui.css:69` `.dialog` | `16px` | B | → `var(--radius-card)` (10px) |
| 26 | `app.css:3` `.assistant>footer` | `18px` | B | → `var(--radius-control)` (12px) |
| 27 | `app.css:3` `.workspace-nav>button` | `8px` | B | → `var(--radius-small)` (6px) |
| 28 | `workspace.css:1` `nav>button` | `8px` | B | → `var(--radius-small)` |
| 29 | `workspace-sovereign.css:5` `.workspace-header-actions>button` | `7px` | B | → `var(--radius-small)` |
| 30 | `app.css:2,5` `.writing-number`, `.book-cover`, `.detail-cover` | `4px 9px 9px 4px`, `3px 8px 8px 3px`, `5px 16px 16px 5px` | C | **Mantido deliberadamente.** São lombadas de livro — geometria ilustrativa assimétrica. `DESIGN.md`: *"Capas e ilustrações podem usar formas orgânicas, mas o chrome do produto permanece geométrico."* Normalizar destruiria a metáfora. |
| 31 | `app.css:3` `.messages p` | `13px 13px 13px 3px` | C | **Mantido.** Rabo de balão de conversa. Além disso é CSS morto (ver §3.7). |

Botões usam `--radius-pill` (9999px), o que atende à pílula de `design.md` em qualquer altura. **`.button` não recebeu variante "sand" (`#f6f4ef`)** — ver decisão aberta 4.

### 3.6 Tipografia

| # | Item | Resultado |
|---|---|---|
| 32 | A face de display está ligada? | **Sim.** `globals.css:1` importa `@fontsource-variable/bricolage-grotesque`; `--font-display` resolve para `'Bricolage Grotesque Variable'`. **Não é uma lacuna** — a suspeita da tarefa não se confirma. |
| 33 | Inter em tamanhos de display? | **Não.** Todos os `h1`/`h2` grandes (`.library-hero h1` 48–82px, `.draft h1` 44–68px, `.landing-intro h1` 52–94px, `.public-article h1` 48–82px, `.prose h1..h3`) já usam `var(--font-display)`. Conforme. |
| 34 | Tracking negativo em display | Presente e coerente: −0.03em a −0.065em conforme o tamanho. `design.md` pede −0.031em em 68px; o produto usa mais aperto (−0.055em) — é escolha editorial deliberada, dentro do espírito. Não alterado. |
| 35 | Entrelinha de texto corrido | `body` 1.55, `.prose` 1.76, `.draft p` 1.72. `DESIGN.md` pede 1.55–1.7. `.prose` a 1.76 estoura por 0.06. | **C, adiado** — dentro do ruído, mexer é decisão editorial. |
| 36 | Tamanho de corpo | `body` 15px. `design.md` pede 17px, `DESIGN.md` aceita "15–17px para interface". Conforme ao contrato vigente. Não alterado. |
| 37 | `font-weight:650` / `580` / `560` / `620` | Pesos não-canônicos, só possíveis por a fonte ser variável. `design.md` lista 400/500/600. | **C, mantido** — Bricolage é variável, os pesos renderizam; normalizar é redesign tipográfico. |

### 3.7 Espaçamento e dívida estrutural

| # | Item | Sev | Status |
|---|---|---|---|
| 38 | ~120 declarações de espaçamento fora da base 4px (`gap:9px`, `padding:25px`, `gap:22px`, `padding:14px 12px 11px`, `height:58px`, `gap:62px`, `padding:0 44px`…) | C | **Adiado.** Fechar isso é reescrever o ritmo de todas as telas — explicitamente fora do escopo ("não redesenhe telas"). O ritmo ímpar parece intencional (sensação de traço à mão). |
| 39 | `design.md` pede gap de seção de 80–120px; o produto usa 68–96px | C | **Adiado.** Decisão de densidade, não de marca. |
| 40 | **`app.css` (16 KB, o maior arquivo de CSS) está em grande parte morto.** É o protótipo do shell antigo. ~35 classes definidas nunca aparecem em nenhum `className`: `.workspace-shell`, `.workspace-nav`, `.assistant`, `.messages`, `.user-message`, `.document-scroll`, `.margin-rail`, `.draft`, `.paper-note`, `.mini-rail`, `.avatar`, `.budget`, `.open-icon`, `.writing-card`, `.writing-number`, `.context`, `.nav-label`, `.public`, `.deck`, `.routed-public`, `.back`, `.accepted`, `.prompt`, `.source`, `.lede`, `.orange`, `.green`… As telas reais são servidas por `workspace.css` e `public-site.css`. | **C** | **Adiado e sinalizado.** Achado grande, mas "não reestruture a arquitetura de CSS". Estimativa: ~8 KB deletáveis. Merece um PR próprio, com varredura de `className` dinâmico antes de apagar. |

---

## 4. O que foi mudado

**11 arquivos modificados, 4 ativos adicionados. Nenhuma dependência nova, nenhum componente novo, nenhuma tela redesenhada.**

`frontend/src/styles/tokens.css` — 10 tokens de cor + 1 de sombra adicionados; `--shadow-overlay` reduzido ao teto do `design.md`. **Toda a consolidação de cor foi feita aqui**, não nos 18 pontos de chamada.

`frontend/index.html` — três `<link>` de ícone.

`frontend/public/favicon.svg`, `favicon.ico`, `apple-touch-icon.png`, `brand/logo-icon.svg` — cópias de `brand/`. (Cópia, não import: o Vite não serve arquivos acima da raiz sem `fs.allow`, e favicon é ativo estático por natureza. Custo: duplicação. `brand/README.md` continua sendo a origem.)

`frontend/src/features/library/LibraryPage.tsx` e `frontend/src/public-site/PublicReadingShell.tsx` — `<img src="/brand/logo-icon.svg" alt="" />` ao lado do nome nos dois headers. `alt=""` porque o texto adjacente já nomeia a marca; o mascote é decorativo na árvore de acessibilidade.

`globals.css`, `ui.css`, `app.css`, `workspace.css`, `workspace-sovereign.css`, `suggestions.css`, `public-site.css` — substituição de literais por tokens e correção de raios.

### O que foi deixado em paz, de propósito

- **A paleta `design.md` de mascotes storybook.** O produto não é uma landing de carteira cripto. `DESIGN.md` já restringe corretamente.
- **Os raios de lombada de livro** (§3.5 #30) — geometria ilustrativa, não chrome.
- **Os ~120 espaçamentos fora da grade** (§3.7 #38) — fechar isso é redesenhar.
- **Os 8 KB de CSS morto em `app.css`** (§3.7 #40) — PR próprio.
- **As cores da scrollbar** — contrato de comportamento, não de marca.
- **Os pesos de fonte não-canônicos** — redesign tipográfico.
- **Warnings de lint pré-existentes** (15, todos `react-refresh` / `exhaustive-deps`) — nenhum em arquivo tocado por esta auditoria.

---

## 5. Decisões abertas — precisam da chamada do autor

### 5.1 `Family` ou `Bricolage Grotesque`?
**Recomendação: Bricolage, e corrigir o `design.md`.** `Family` é proprietária, não está instalada, não é distribuível, e o wordmark em `brand/` **já está desenhado em Bricolage** (README, §Paleta). Manter `design.md` dizendo `Family` garante que alguém no futuro vai tentar comprar/instalar a fonte errada. Ação sugerida: editar `design.md` trocando `Family` → `Bricolage Grotesque` e removendo a linha "Substitute: Druk Wide Medium". *Não executado — mexer no documento de marca é decisão sua.*

### 5.2 O produto se chama "Entrelinhas" ou "deixedeserburro"?
Esta é a divergência mais séria e **bloqueia o uso do wordmark**. `brand/wordmark.svg` e `brand/logo.svg` contêm o texto **"deixedeserburro"** em contornos. O app diz "Entrelinhas" em todos os títulos de rota, no `UX-CONTRACT.md` e nos testes.

Por isso wirei apenas o **`logo-icon.svg` (o mascote, sem texto)** e o favicon — são neutros quanto ao nome. **Não coloquei `logo.svg` nem `wordmark.svg` em lugar nenhum**, porque isso faria a interface exibir dois nomes de marca diferentes na mesma linha.

**Recomendação:** decida o nome antes de qualquer outra coisa visual. Se for "deixedeserburro", é uma renomeação de produto (rotas, `<title>`, `UX-CONTRACT.md`, testes) e aí o wordmark entra nos dois headers. Se for "Entrelinhas", o `brand/` precisa de um wordmark redesenhado e o `brand/README.md` precisa de correção. Terceira via: "deixedeserburro" é a marca-casa e "Entrelinhas" é o produto — nesse caso o mascote no header já está certo e nada mais muda.

### 5.3 O mascote burro combina com o `design.md`?
`design.md` descreve "mascotes cartoon storybook com olhos de pontinho e membros de palito" em preenchimentos chapados. O burro de `brand/` é **line-art de traço pesado, roundel old-school** — linguagem oposta (contorno vs. preenchimento). Um dos dois está errado. **Recomendação:** o `brand/` vence (é o ativo produzido); reescrever a seção *Imagery* do `design.md` para descrever line-art de traço pesado em vez de mascotes chapados. *Não executado.*

### 5.4 Falta a variante "sand pill" de botão
`design.md` define exatamente duas pílulas: escura `#121212` e areia `#f6f4ef`. O produto tem quatro variantes (`primary`/`neutral`/`ghost`/`danger`) e nenhuma é areia — `neutral` é branco com hairline. **Recomendação: não adicionar.** Quatro variantes já cobrem o espaço; `#f6f4ef` sequer existe nos tokens, e `--color-surface-muted` (`#f2f0ed`) é próximo o bastante. Só vale mexer se você quiser a leitura tonal específica do par escuro+areia lado a lado. Registro aqui porque é divergência explícita da marca.

### 5.5 Sem `manifest.webmanifest`
Adiado por YAGNI — não há requisito de PWA/instalação. `brand/png/` tem `icon-192` e `icon-512` prontos para o dia em que houver. Um manifesto custa ~8 linhas quando for pedido.

---

## 6. Verificação

Saída real desta branch. Sem verificação em navegador — ver §6.2.

```
$ npm --prefix frontend run lint
✖ 15 problems (0 errors, 15 warnings)
EXIT=0
```
15 warnings, todos pré-existentes (`react-refresh/only-export-components` ×12, `react-hooks/exhaustive-deps` ×2, +1) em `Workspace.tsx`, `RecorderProvider.tsx`, `SuggestionProvider.tsx`, `SessionProvider.tsx`, `ChatProvider.tsx`, `WorkspaceProvider.tsx`, `router.tsx` — nenhum arquivo tocado por esta auditoria.

```
$ npm --prefix frontend run typecheck
> tsc -b --pretty false
EXIT=0
```

```
$ npm --prefix frontend run test:unit
 Test Files  16 passed (16)
      Tests  58 passed (58)
   Duration  8.90s
EXIT=0
```

```
$ npm --prefix frontend run build
✓ built in 14.71s
EXIT=0
```
Aviso pré-existente de chunk >500 kB (mermaid/katex/cytoscape), não relacionado.
Ativos da marca confirmados em `dist/`: `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`, `brand/logo-icon.svg`.

```
$ npm --prefix frontend run verify:premium
Premium static check: 79 arquivos, 0 violações.
EXIT=0
```

```
$ npm --prefix frontend run test:a11y
 Test Files  1 passed (1)
      Tests  2 passed (2)
EXIT=0
```

### 6.1 O que o `verify:premium` já cobre (e o que não)

`frontend/scripts/check-anti-patterns.mjs` verifica **apenas** `alert(`/`confirm(`/`prompt(`, `dangerouslySetInnerHTML`, mock no entrypoint de produção, `fetch` direto dentro de `features/`, e a string de orçamento fictício. **Não tem nenhuma regra visual** — não olha cor, sombra, raio nem gradiente, e nem sequer lê arquivos `.css` (o walk filtra `.ts|.tsx`). Nada nesta auditoria duplica esse gate.

Se você quiser travar as regressões que este PR corrigiu, o gate mais barato seria estender esse mesmo script para varrer `.css` e reprovar: literal hexadecimal fora de `tokens.css`, `linear-gradient`/`radial-gradient`, e `border-radius` numérico fora de {6,10,12,9999}. Cerca de 10 linhas. **Não implementado** — adicionar um gate novo não foi pedido, e ele reprovaria hoje os raios de lombada de livro (§3.5 #30) sem uma lista de exceções.

### 6.2 Verificação em navegador: não realizada

Playwright lista os 8 testes normalmente, mas o Chromium **não inicia nesta máquina**:

```
[pid=800853][err] .../chrome-headless-shell: error while loading shared libraries:
libnspr4.so: cannot open shared object file: No such file or directory
```

Tentado uma vez, falhou, sem workaround. **Nenhuma afirmação neste documento foi verificada visualmente.** As mudanças de cor/raio/sombra foram verificadas por leitura estática, pelos 58 testes unitários (que compilam o CSS via `vitest css:true`) e pelo build. O favicon e o mascote nos headers **não foram vistos renderizados** — precisam de conferência ocular sua ou de uma máquina com `libnspr4` instalada.
