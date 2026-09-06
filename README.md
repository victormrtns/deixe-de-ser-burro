<p align="center">
  <img src="brand/logo-icon.png" alt="" width="132">
</p>

<h1 align="center">deixedeserburro</h1>

<p align="center">
  <strong>Um caderno de leitura e escrita com assistência de IA.</strong><br>
  Organize livros, transforme notas em textos e publique o que quiser compartilhar — sem entregar o texto para a máquina escrever.
</p>

<p align="center">
  <img alt="Estágio: alfa" src="https://img.shields.io/badge/est%C3%A1gio-alfa-d93500">
  <img alt="React 19" src="https://img.shields.io/badge/React-19-0073d8">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python%203.12+-0073d8">
  <img alt="PostgreSQL 16" src="https://img.shields.io/badge/PostgreSQL-16-0073d8">
  <img alt="WCAG 2.2 AA" src="https://img.shields.io/badge/WCAG-2.2%20AA-00c978">
  <img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache%202.0-0073d8">
  <img alt="pt-BR" src="https://img.shields.io/badge/idioma-pt--BR-7e7e7d">
</p>

---

## O que é

Um livro termina, a leitura não. O deixedeserburro é onde ela continua: você cadastra o
que está lendo, escreve sobre trechos específicos, conversa com um assistente que
enxerga o seu texto, e publica o que valer a pena.

A diferença está em uma regra: **o assistente lê e responde, mas não escreve por você.**
Ele nunca altera o Markdown sozinho. O documento é seu, a conversa fica ao lado, e o que
vira público é uma versão congelada que você escolheu publicar.

O sistema tem dois lados. A **área privada** é um estúdio de autor único, autenticado. A
**área pública** é uma estante de leitura, sem login, que nunca carrega conversas,
prompts, transcrições ou identificadores internos — nem no bundle, nem nas respostas da
API.

## Começar em três comandos

Requer apenas **Docker com Docker Compose**.

```bash
cp .env.example .env                      # troque POSTGRES_PASSWORD
docker compose up -d db && docker compose run --rm migrate && docker compose run --rm bootstrap-author
docker compose up -d backend frontend
```

Abra <http://127.0.0.1:5173>. O passo de bootstrap pergunta e-mail e senha do autor no
terminal — há um autor por instalação, e o comando é idempotente.

O assistente começa **desligado**. Para desenvolver com respostas simuladas, sem chamada
externa e sem custo, use `AI_GATEWAY=fake`. Detalhes em [configuração do
assistente](#configuração-do-assistente).

## O que já funciona

| Área | Estado |
| --- | --- |
| **Biblioteca** | Livros com metadados e escritas associadas a cada leitura |
| **Editor Markdown** | Salvamento automático, histórico de versões, restauração e detecção de conflito |
| **Conversa contextual** | Respostas em streaming sobre a escrita atual, histórico persistido, memória por escrita e reserva de orçamento |
| **Publicação** | Artigo público com slug e conteúdo congelado; retirada e limpeza agendada com três dias de recuperação |
| **Site público** | Estante, artigos, livros e página sobre, sem autenticação e sem artefatos de trabalho |
| **Área privada** | Autenticação de autor único, com sessão em cookie |

Sugestões de edição com diff e aceite explícito, notas de áudio e fontes por link estão
planejadas, não construídas. O painel de sugestões que aparece no estúdio é maquete. Veja
o [roadmap de IA](ia/ROADMAP.md) e o [handoff de UI](docs/ui-handoff.md), que lista o que
falta com honestidade.

## Como está montado

```
┌─────────────────────────────────────────────────────────────┐
│  Navegador                                                  │
│                                                             │
│  /                    rotas públicas — estante e leitura    │
│  /studio              rotas privadas — biblioteca e estúdio │
│                                                             │
│  React 19 · SPA · SWR para cache e revalidação              │
└──────────────────────────┬──────────────────────────────────┘
                           │  /api  (mesma origem, proxy no dev)
┌──────────────────────────┴──────────────────────────────────┐
│  FastAPI                                                    │
│                                                             │
│  rotas públicas  ──▶  projeções congeladas, schema auditado │
│  rotas privadas  ──▶  livros, escritas, versões, conversa   │
│  gateway de IA   ──▶  disabled │ fake │ openai              │
└──────────────────────────┬──────────────────────────────────┘
                           │
              PostgreSQL 16 · migrações Alembic
```

A separação entre público e privado não é convenção, é verificada: um script de CI local
(`check_public_schema.py`) falha se um schema de rota pública referenciar campo privado, e
os testes de contrato em `backend/tests/contract/` cobrem privacidade de log, de resposta
pública e do assistente.

O Markdown é o documento canônico. O assistente recebe o texto atual como contexto e
devolve mensagem — nunca um patch aplicado sozinho.

## Tecnologias

| Camada | Escolhas |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, SWR, Radix UI |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy assíncrono |
| Persistência | PostgreSQL 16, migrações Alembic |
| Assistente | Gateway próprio com três adaptadores: desativado, simulado e OpenAI |
| Testes | pytest, Vitest, Testing Library, Playwright, axe-core |
| Ambiente local | Docker Compose, Node.js 22, uv |

Sem framework de CSS. A interface usa tokens declarados em
`frontend/src/styles/tokens.css`, derivados de [`design.md`](design.md).

## Instalação completa

### 1. Ambiente

```bash
cp .env.example .env
```

Troque `POSTGRES_PASSWORD=CHANGE_ME` por uma senha local e mantenha
`PUBLIC_ORIGIN=http://127.0.0.1:5173`. O Compose monta a conexão do banco a partir de
`POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`.

### 2. Banco e autor

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose run --rm bootstrap-author
```

O bootstrap aceita `AUTHOR_EMAIL` e `AUTHOR_PASSWORD` como variáveis, se preferir não
digitar.

### 3. Aplicação

```bash
docker compose up -d backend frontend
```

| Serviço | Endereço |
| --- | --- |
| Aplicação | <http://127.0.0.1:5173> |
| API | <http://127.0.0.1:8000> |
| Prontidão | <http://127.0.0.1:8000/api/health/ready> |

O frontend encaminha `/api` para o backend. Dados e arquivos ficam nos volumes `db_data`
e `app_files`; `docker compose down` preserva os dois.

```bash
docker compose logs -f backend frontend
docker compose down
```

## Configuração do assistente

| `AI_GATEWAY` | Comportamento |
| --- | --- |
| `disabled` | Padrão. A IA fica indisponível e o resto do produto continua inteiro. |
| `fake` | Respostas simuladas e determinísticas. Emite a mesma sequência de eventos do contrato real, incluindo interrupção, timeout e limite de taxa. Não acessa a rede e não custa nada. |
| `openai` | Adaptador real. Exige `OPENAI_API_KEY` no ambiente do backend. |

A chave e as chamadas ao provedor ficam no backend — nunca no banco, nunca em log, nunca
no frontend, nunca em arquivo versionado. `AI_MODEL`, limites de contexto e saída e
orçamento são configuráveis em [.env.example](.env.example).

A aplicação reserva orçamento antes de cada tentativa e registra o resultado. Os padrões
são US$ 2,00 para desenvolvimento e US$ 0,25 para validação manual. O
[guia da stack local](ops/dev-stack.md) descreve o procedimento de validação com o
provedor real, que é pontual e não é modo de desenvolvimento.

## Desenvolvimento

Para ferramentas fora dos containers: **Node.js 22**, **Python 3.12+** e **uv**.

### Frontend

```bash
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run test:unit
npm --prefix frontend run test:a11y        # axe-core, sem violações críticas ou sérias
npm --prefix frontend run build
npm --prefix frontend run verify:premium   # proíbe alert/confirm/prompt e fetch fora do adaptador
npm --prefix frontend run verify:bundles   # proíbe módulos privados pesados no bundle público
```

Para o E2E, instale o Chromium do Playwright e prepare a stack conforme
[ops/dev-stack.md](ops/dev-stack.md). O E2E usa a origem `http://127.0.0.1:4173`.

```bash
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run test:e2e
```

### Backend

Os testes de integração precisam de um PostgreSQL de testes alcançável; o banco do
Compose não publica porta no host por padrão.

```bash
cd backend
uv sync
export TEST_DATABASE_URL='postgresql+psycopg://USUARIO:SENHA@localhost:5432/entrelinhas_test'
uv run pytest
uv run ruff format --check . && uv run ruff check .
uv run mypy app
uv run python scripts/check_public_schema.py
```

## Estrutura

```text
backend/       API, domínio, migrações e testes
frontend/      estúdio, biblioteca, conversa e site público
brand/         arquivos finais da marca e guia de uso
docs/          especificações, planos, auditorias e handoffs
ia/            roadmap, estudos e casos de avaliação do assistente
ops/           execução local, implantação, backup e limpeza
```

## Contribuir

Antes de abrir um PR, leia o [contrato de experiência](UX-CONTRACT.md). Ele não é
sugestão: define os donos canônicos de cada capacidade de interface, o comportamento
esperado de cada operação e o alvo de acessibilidade. Três regras que rejeitam PR:

1. **Nenhum `<button>` declara o próprio estilo.** Toda ação é `PrimaryButton`,
   `NeutralButton`, `GhostButton`, `DangerButton` ou a classe `.text-action`.
2. **Cor não opera sozinha.** Status carrega o acento no fundo com texto em tinta,
   acompanhado de ícone ou rótulo.
3. **Rota pública não carrega módulo privado.** `verify:bundles` falha se carregar.

Os valores visuais vêm de [`design.md`](design.md), que é canônico para cor, tipografia e
linguagem visual — mas é uma referência extraída de fora, e os componentes que ele cita
não são o inventário deste produto. O inventário real está no contrato.

Rode a verificação completa antes de enviar. Todos os comandos da seção
[Desenvolvimento](#desenvolvimento) precisam passar.

## Documentação

| Documento | Para quê |
| --- | --- |
| [`UX-CONTRACT.md`](UX-CONTRACT.md) | Rotas, títulos, donos de UI, comportamento e acessibilidade |
| [`design.md`](design.md) | Cor, tipografia e linguagem visual — canônico |
| [`docs/ui-handoff.md`](docs/ui-handoff.md) | O que já foi corrigido na interface e o que segue sem desenho |
| [`docs/brand-audit.md`](docs/brand-audit.md) | Auditoria de marca e contraste |
| [`brand/README.md`](brand/README.md) | Logo, wordmark, favicon e faixas de tamanho |
| [`ia/ROADMAP.md`](ia/ROADMAP.md) | Roadmap do assistente |
| [`ops/dev-stack.md`](ops/dev-stack.md) | Stack local, E2E e validação do assistente |
| [`docs/handoffs/current.md`](docs/handoffs/current.md) | Estado e continuidade do projeto |


## Marca

Um burro curioso saindo de um livro aberto, com uma fita laranja marcando a página, dentro
de um selo. Traço pesado, papel e tinta — desenho, não mascote chapado.

Os arquivos finais estão em [`brand/`](brand/README.md): assinatura horizontal, mascote,
variações para fundo escuro, PNGs de 16 a 1024px e favicon. Os SVGs do nome usam contornos
e não dependem de fonte instalada.

O nome público é **deixedeserburro**. Identificadores técnicos — pacote, banco, cookie e
caminho de implantação — ainda usam `entrelinhas`, e isso é deliberado: renomear exige
migração e não afeta a execução.

**O nome e os arquivos de `brand/` não estão sob a licença do código.** Faça o fork à
vontade, mas dê a ele nome e identidade próprios antes de publicar: troque os arquivos de
`brand/`, o nome nos títulos de página e a assinatura do rodapé. Citar o projeto original
para descrever origem ou compatibilidade é uso razoável e não precisa de permissão.

## Licença

Código sob [Apache License 2.0](LICENSE). Você pode usar, modificar, distribuir e vender,
inclusive em produto fechado, mantendo o aviso de copyright e registrando o que mudou.

Escolhi Apache em vez de MIT por duas cláusulas que a MIT não tem: concessão expressa de
patentes, e a Seção 6, que nega permissão para usar o nome e a marca do projeto. Ver
[NOTICE](NOTICE) para o que a marca cobre.

## Princípios

O autor decide o que entra no texto e o que vira publicação. A IA participa com contexto,
limite de custo e resultado revisável — nunca com autonomia sobre o documento. Conteúdo
privado permanece separado do público por verificação automatizada, não por disciplina.
Conflito de versão é tratado explicitamente, nunca por merge silencioso.
