<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo-inverse.svg">
    <img src="brand/logo.svg" alt="deixedeserburro" width="640">
  </picture>
</p>

# deixedeserburro

Um caderno de leitura e escrita com assistência de IA. Organize livros, transforme suas notas em textos e publique o que quiser compartilhar — mantendo o controle sobre cada palavra.

O projeto atende um autor privado e leitores públicos. O Markdown é o documento canônico; a conversa com a IA acontece ao lado da escrita. Na implementação atual, o assistente responde sobre o texto, mas não o modifica.

## Funcionalidades

- **Biblioteca:** cadastro de livros, capas e metadados, com escritas associadas a cada livro.
- **Editor Markdown:** edição manual, histórico de versões, restauração e detecção de conflitos entre salvamentos.
- **Conversa contextual:** respostas progressivas sobre a escrita atual, histórico persistido, memória por escrita e controle de orçamento.
- **Publicação:** artigos públicos com slug e conteúdo congelado na publicação, além de controles de retirada e limpeza.
- **Área privada:** autenticação de um único autor por sessão. Rascunhos e conversas ficam separados das projeções públicas.

Sugestões de edição com diff e aceite explícito, fontes por links e entradas multimodais fazem parte da evolução planejada. Consulte o [roadmap de IA](ia/ROADMAP.md).

## Tecnologias

| Camada | Tecnologias |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, SWR e CodeMirror |
| Backend | Python 3.12+, FastAPI, Pydantic e SQLAlchemy assíncrono |
| Persistência | PostgreSQL 16 e migrações Alembic |
| Assistente | Gateway interno com adaptadores desativado, simulado e OpenAI |
| Testes | pytest, Vitest, Testing Library, Playwright e axe |
| Ambiente local | Docker Compose, Node.js 22 e uv |

## Executar localmente

Para executar toda a stack em containers, instale **Docker com Docker Compose**. Node.js e Python locais são necessários apenas se você executar ferramentas fora dos containers.

### 1. Configurar o ambiente

Na raiz do repositório:

```bash
cp .env.example .env
```

Edite `.env`, substitua `POSTGRES_PASSWORD=CHANGE_ME` por uma senha local e mantenha `PUBLIC_ORIGIN=http://127.0.0.1:5173` para esta configuração. O Compose monta a conexão do banco a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`.

O assistente começa desligado, com `AI_GATEWAY=disabled`. Para desenvolver com respostas simuladas sem chamadas externas, use `AI_GATEWAY=fake`.

### 2. Preparar banco e autor

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose run --rm bootstrap-author
```

O bootstrap solicita e-mail e senha no terminal. Também aceita as variáveis `AUTHOR_EMAIL` e `AUTHOR_PASSWORD`. Há apenas um autor por instalação; o bootstrap é idempotente.

### 3. Iniciar a aplicação

```bash
docker compose up -d backend frontend
```

| Serviço | Endereço |
| --- | --- |
| Aplicação | http://127.0.0.1:5173 |
| API | http://127.0.0.1:8000 |
| Prontidão do backend | http://127.0.0.1:8000/api/health/ready |

O frontend encaminha `/api` para o backend. Os dados do PostgreSQL e os arquivos enviados ficam nos volumes `db_data` e `app_files`.

Para acompanhar logs ou parar os serviços:

```bash
docker compose logs -f backend frontend
docker compose down
```

`docker compose down` preserva os volumes de dados.

## Configuração do assistente

| `AI_GATEWAY` | Comportamento |
| --- | --- |
| `disabled` | Padrão. A IA fica indisponível; as funções editoriais continuam disponíveis. |
| `fake` | Respostas simuladas e determinísticas para desenvolvimento e testes. |
| `openai` | Usa o adaptador real e exige `OPENAI_API_KEY` no ambiente do backend. |

A chave e as chamadas ao provedor ficam no backend. `AI_MODEL`, limites de contexto/saída e orçamento são configuráveis; os valores estão em [.env.example](.env.example).

A aplicação reserva orçamento antes de uma tentativa e registra seu resultado. Os padrões configurados são US$ 2,00 para desenvolvimento e US$ 0,25 para o orçamento de smoke manual. O modo simulado não consome API.

O [guia da stack local](ops/dev-stack.md) descreve a configuração e a validação do assistente. A presença do adaptador real no código não substitui sua validação com o provedor.

## Desenvolvimento e verificações

Para ferramentas locais, use **Node.js 22**, **Python 3.12+** e **uv**.

### Frontend

Execute a partir da raiz do repositório:

```bash
npm --prefix frontend ci
npm --prefix frontend run test:unit
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run test:a11y
npm --prefix frontend run build
npm --prefix frontend run verify:premium
npm --prefix frontend run verify:bundles
```

Para os testes de navegador, instale o Chromium do Playwright e prepare a stack conforme [ops/dev-stack.md](ops/dev-stack.md). O E2E usa a origem `http://127.0.0.1:4173`, diferente da porta de desenvolvimento acima.

```bash
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run test:e2e
```

### Backend

Os testes de integração precisam de um PostgreSQL de testes alcançável. Configure `TEST_DATABASE_URL` com uma conexão própria para testes; o banco do Compose não publica uma porta no host por padrão.

```bash
cd backend
uv sync
export TEST_DATABASE_URL='postgresql+psycopg://USUARIO:SENHA@localhost:5432/entrelinhas_test'
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run python scripts/check_public_schema.py
```

O verificador de schemas impede que as rotas públicas exponham os campos privados fiscalizados pelo projeto. Os testes automatizados do assistente usam o gateway falso.

## Organização do repositório

```text
backend/       API, domínio, migrações e testes
frontend/      editor, biblioteca, conversa e site público
brand/         arquivos finais da marca e guia de uso
docs/          especificações, planos, padrões e handoffs
ia/            roadmap, estudos e casos de avaliação de IA
ops/           guias de execução, implantação e operação
```

## Identidade visual

A marca é um burro curioso com um livro aberto e um marcador laranja. Papel, tinta e anotação conectam o mascote à identidade do produto.

Os arquivos finais estão em [brand](brand/README.md): assinatura horizontal, mascote, variações para fundo escuro, PNGs e favicon. Os SVGs do nome usam contornos e não dependem de fontes instaladas.

O nome público é **deixedeserburro**. Identificadores técnicos como pacotes, banco e cookie ainda usam `entrelinhas`; isso não exige renomeação para executar o projeto.

## Documentação

- [Contexto e continuidade do projeto](docs/handoffs/current.md)
- [Identidade visual da interface](DESIGN.md)
- [Contrato de experiência](UX-CONTRACT.md)
- [Roadmap de IA](ia/ROADMAP.md)
- [Stack local e testes de navegador](ops/dev-stack.md)
- [Guia da marca](brand/README.md)

## Princípios

O autor decide o que entra no texto e o que vira publicação. A IA participa da escrita com contexto, limites de custo e resultados revisáveis. Conteúdo privado permanece separado do conteúdo público, e conflitos de versão devem ser tratados explicitamente.
