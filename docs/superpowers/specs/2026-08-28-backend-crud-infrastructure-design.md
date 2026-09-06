# Backend CRUD, infraestrutura e publicação — Especificação de design

## Contexto e objetivo

Esta fase cria o primeiro backend executável do deixedeserburro. Ela substitui os mocks dos fluxos de biblioteca, escrita, versionamento e publicação por uma API FastAPI persistida em PostgreSQL, executada localmente com Docker Compose e preparada para uma implantação simples em VPS.

O corte inclui publicação real porque o snapshot público, a separação entre dados privados e públicos e a janela de limpeza determinam o modelo de versões e as fronteiras dos módulos. A fase não implementa chat, transcrição, geração, sugestões de IA, controle de custo de IA nem processamento de links. Esses contratos podem continuar simulados no frontend até seus próprios ciclos de design e implementação.

## Decisões e princípios

- Monólito modular, com um único processo FastAPI e um único PostgreSQL.
- Módulos por capacidade de negócio, não um repositório CRUD genérico compartilhado.
- Markdown é canônico. Toda gravação aceita cria uma versão imutável recuperável.
- Escritas privadas usam identificadores internos; recursos públicos usam slugs e DTOs próprios.
- Publicar congela uma versão e nunca faz uma rota pública consultar o rascunho atual.
- Concorrência otimista impede que uma aba sobrescreva silenciosamente outra.
- Operações com efeito repetível recebem idempotência explícita.
- Banco, API e tarefas de manutenção usam horários UTC; datas são serializadas em ISO 8601 com timezone.
- Redis, Celery, S3 e integrações de IA permanecem fora desta fase.

## Escopo

### Incluído

- configuração do backend e do banco;
- health checks, migrações e dados iniciais opcionais de desenvolvimento;
- sessão do único autor e proteção de todas as rotas privadas;
- CRUD de livros e escritas;
- autosave com versões Markdown e restauração;
- publicação, despublicação durante a janela de segurança, cancelamento da limpeza e retorno a rascunho;
- seleção manual do artigo em destaque;
- landing, arquivo, artigos e livros públicos por projeções allowlisted;
- limpeza persistida e retomável do contexto privado após três dias;
- armazenamento local de capas, quando usado;
- logs estruturados, backup e testes do corte.

### Explicitamente adiado

- chamadas ou adaptadores de IA;
- chat, mensagens, links processados, áudio, transcrições e sugestões funcionais;
- medição e bloqueio de orçamento de IA;
- Redis, Celery, filas externas e workers distribuídos;
- armazenamento S3;
- múltiplos autores, leitores autenticados, comentários e busca pública;
- paginação do arquivo enquanto a coleção permanecer pequena. A resposta deve permitir adicionar cursor sem alterar os itens.

## Arquitetura e limites de módulos

O backend reside em `backend/` e preserva dependências direcionais: HTTP chama serviços de aplicação; serviços controlam regras e transações; persistência implementa portas internas. Modelos ORM nunca são retornados diretamente.

```text
backend/
├── pyproject.toml
├── alembic.ini
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
└── app/
    ├── main.py
    ├── config.py
    ├── db.py
    ├── errors.py
    ├── observability.py
    ├── auth/
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   └── persistence.py
    ├── library/
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   └── persistence.py
    ├── writings/
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   └── persistence.py
    ├── publishing/
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   ├── persistence.py
    │   └── cleanup.py
    ├── public_read/
    │   ├── router.py
    │   ├── queries.py
    │   └── schemas.py
    └── files/
        ├── service.py
        └── local.py
```

`library` possui livros. `writings` possui escritas e versões privadas. `publishing` controla snapshots, destaque e retenção. `public_read` é somente leitura e constrói respostas exclusivamente de snapshots publicados e metadados públicos. `files` oferece uma porta pequena para capas; o adaptador local pode ser trocado posteriormente sem mudar os módulos consumidores.

Não haverá uma camada `domain/` abstrata por módulo nesta fase. Regras ficam em serviços pequenos e tipos explícitos. Caso um módulo acumule lógica independente do framework, tipos de domínio podem ser extraídos sem alterar sua API pública.

## Modelo de dados

Todas as tabelas usam UUID como chave primária, timestamps UTC `created_at` e `updated_at` quando aplicável e foreign keys com índices. Slugs são strings normalizadas, únicas dentro do namespace público, mas não são chaves primárias.

### `author_accounts`

- `id`;
- `email`, único e normalizado;
- `password_hash`;
- `is_active`;
- timestamps.

Uma restrição/configuração de bootstrap garante apenas uma conta ativa no MVP. Não se codifica um autor fixo nas rotas.

### `author_sessions`

- `id`;
- `author_id`;
- `token_hash`, único;
- `expires_at`, `revoked_at`;
- `created_at`, `last_seen_at`.

O cookie contém um token opaco; somente o hash é persistido.

### `books`

- `id`;
- `title`, `author`;
- `private_cover_path`, opcional;
- timestamps.

`writing_count` não é persistido: é calculado em consultas privadas. Excluir livro só é permitido quando não houver escritas; a API retorna conflito e exige exclusão explícita das escritas primeiro.

### `writings`

- `id`, `book_id`;
- `title`, `source_range`;
- `markdown` atual;
- `version_number`, inteiro iniciado em `1`;
- `status`: `draft`, `cleanup_scheduled` ou `published`;
- timestamps.

`version_number` é o token de concorrência do documento, não a versão do esquema nem um contador de publicação.

### `writing_versions`

- `id`, `writing_id`;
- `version_number`, único por escrita;
- `markdown`, `title` e `source_range` como conteúdo recuperável;
- `reason`: `created`, `manual_save`, `restored` ou `published`;
- `created_at`.

A versão inicial é criada na mesma transação da escrita. Um save aceito atualiza `writings` e insere exatamente uma versão. Restaurar copia uma versão anterior para o estado atual e cria uma nova versão; o histórico nunca é reescrito.

### `publications`

- `id`, `writing_id`;
- `writing_version_id` congelada;
- `slug`, único;
- snapshot allowlisted: `title`, `markdown`, `excerpt`, `reading_minutes`, `published_at`;
- snapshot do livro público: `book_slug`, `book_title`, `book_author`, `public_cover_path` opcional;
- `state`: `published` ou `withdrawn`;
- `cleanup_due_at`, `cleanup_cancelled_at`, `cleanup_completed_at`;
- timestamps.

Há no máximo uma publicação ativa por escrita. O snapshot duplica deliberadamente os campos públicos necessários: mudanças posteriores no rascunho ou livro não alteram um artigo já publicado. Republicar após retirada cria nova publicação/snapshot; o slug pode ser reutilizado somente se não colidir com outra publicação ativa e o histórico interno continua identificado pelo UUID.

### `publication_topics`

- `publication_id`;
- `topic`;
- `position`.

Tópicos são definidos manualmente nesta fase. Nunca são derivados de conteúdo privado.

### `editorial_settings`

- linha singleton com `featured_publication_id` opcional;
- timestamps.

Se a publicação escolhida não estiver ativa, a landing usa a publicação ativa mais recente sem modificar a configuração.

### `idempotency_keys`

- `author_id`, `operation`, `key`, únicos em conjunto;
- `request_hash`;
- `response_status`, `response_body`;
- `resource_id` opcional;
- `expires_at`, `created_at`.

É usada inicialmente em criação de livro, criação de escrita e publicação. Repetir a chave com o mesmo payload retorna o resultado gravado; com payload diferente retorna `409`.

### Preparação para limpeza futura

Esta fase ainda não cria tabelas vazias de chat, áudio, transcrição ou sugestão. `publishing.cleanup` expõe uma interface de deleção por escrita e uma lista explícita de purgadores registrados. Por enquanto a execução marca a limpeza como concluída sem apagar o Markdown, as versões, o livro ou a publicação. Futuros módulos privados registram seus purgadores quando existirem. Isso evita schema especulativo sem perder a regra e o agendamento persistente.

## Autenticação do autor único

As rotas `/api/auth/session` criam e encerram uma sessão baseada em cookie `HttpOnly`, `Secure` em produção e `SameSite=Lax`. Senhas usam algoritmo moderno com salt, configurado pela biblioteca escolhida. O primeiro autor é criado por comando de bootstrap que lê credenciais de variáveis de ambiente ou prompt interativo; não existe senha padrão nem endpoint público de cadastro.

Todas as rotas `/api/*`, exceto `/api/health/*`, `/api/auth/session` e `/api/public/*`, exigem sessão válida. Requisições mutáveis baseadas em cookie exigem verificação de `Origin` contra a origem configurada; uma implantação cross-origin exigiria um token CSRF e fica fora do desenho local/same-origin. CORS é fechado por padrão.

## API e DTOs

Os nomes JSON seguem camelCase para compatibilidade com o frontend. Erros usam um envelope estável:

```json
{
  "error": {
    "code": "writing_version_conflict",
    "message": "A escrita foi alterada em outra sessão.",
    "details": { "currentVersion": 5 },
    "requestId": "..."
  }
}
```

### Sessão e operação

- `POST /api/auth/session` — autentica o autor.
- `DELETE /api/auth/session` — revoga a sessão atual.
- `GET /api/auth/session` — retorna `anonymous` ou o autor mínimo.
- `GET /api/health/live` — processo ativo; não consulta dependências.
- `GET /api/health/ready` — verifica banco e estado de migração.

### Livros privados

- `GET /api/books` — lista `BookSummary` com `writingCount`.
- `POST /api/books` — cria livro; aceita `Idempotency-Key`.
- `GET /api/books/{bookId}` — retorna detalhe privado.
- `PATCH /api/books/{bookId}` — altera metadados.
- `DELETE /api/books/{bookId}` — exclui somente livro vazio.
- `PUT /api/books/{bookId}/cover` e `DELETE /api/books/{bookId}/cover` — capa opcional, com limites de tipo e tamanho.

`BookSummary` preserva o contrato atual: `id`, `title`, `author`, `coverUrl?`, `writingCount`.

### Escritas e versões

- `GET /api/books/{bookId}/writings` — lista escritas do livro.
- `POST /api/books/{bookId}/writings` — cria escrita e versão inicial; aceita `Idempotency-Key`.
- `GET /api/writings/{writingId}` — detalhe privado.
- `PATCH /api/writings/{writingId}` — altera título/sourceRange usando `expectedVersion` e cria versão.
- `PUT /api/writings/{writingId}` — autosave do Markdown usando `expectedVersion`; mantém o contrato atual.
- `DELETE /api/writings/{writingId}` — permitido somente sem publicação ativa; apaga escrita e histórico privado em transação.
- `GET /api/writings/{writingId}/workspace` — DTO agregado compatível com o frontend; nesta fase listas de mensagens, áudio e sugestões ficam vazias.
- `GET /api/writings/{writingId}/versions` — histórico paginado por cursor.
- `GET /api/writings/{writingId}/versions/{versionNumber}` — versão específica.
- `POST /api/writings/{writingId}/versions/{versionNumber}/restore` — restaura usando `expectedVersion`.

`Writing` contém `id`, `bookId`, `title`, `markdown`, `sourceRange`, `status`, `version` e `updatedAt`. Em conflito, `409 writing_version_conflict` informa a versão corrente sem retornar Markdown que o cliente não solicitou.

### Publicação privada

- `POST /api/writings/{writingId}/publication` — congela a versão corrente; exige `Idempotency-Key`; retorna `slug`, `publishedAt` e `cleanupAt`.
- `GET /api/writings/{writingId}/publication` — estado e prazos da publicação ativa/mais recente.
- `POST /api/writings/{writingId}/publication/cancel-cleanup` — cancela somente a limpeza, mantendo o artigo público.
- `DELETE /api/writings/{writingId}/publication` — durante a janela, retira o artigo e volta a escrita para `draft`; depois da limpeza, a publicação pode ser retirada, mas dados privados já limpos não são recuperados.
- `PUT /api/editorial/featured-publication` — seleciona uma publicação ativa como destaque.
- `DELETE /api/editorial/featured-publication` — remove a escolha manual e restaura o fallback.

Publicar uma escrita já publicada com a mesma `Idempotency-Key` retorna o resultado anterior. Sem a chave correspondente, retorna `409 publication_already_active`; não cria snapshots duplicados.

### Leitura pública

- `GET /api/public/landing` — `PublicLanding`.
- `GET /api/public/articles` — lista de `PublicArticleSummary`, mais recentes primeiro.
- `GET /api/public/articles/{slug}` — artigo congelado completo.
- `GET /api/public/books` — livros com ao menos uma publicação ativa.
- `GET /api/public/books/{slug}` — livro público e seus artigos ativos.

`PublicArticleSummary`, `PublicBookSummary` e `PublicLanding` preservam os contratos tipados existentes. O detalhe do artigo adiciona somente `markdown`; o detalhe do livro adiciona a lista de `PublicArticleSummary`. Nenhum DTO público contém UUID interno, status de rascunho, número de versão privada, prazo de limpeza, timestamps de atividade privada ou coleções privadas.

## Concorrência, idempotência e transações

O autosave executa um `UPDATE writings ... WHERE id = ? AND version_number = expectedVersion`, incrementa a versão e insere `writing_versions` na mesma transação. Zero linhas atualizadas significa conflito. O frontend deve refazer a leitura e decidir como reconciliar; o servidor nunca faz merge implícito.

Criação e publicação guardam a chave idempotente na mesma transação do recurso. A transação bloqueia a escrita durante publicação, valida a versão/status, cria o snapshot, agenda `cleanup_due_at` e altera o status da escrita. Cancelamento e retirada também bloqueiam a publicação ativa, portanto clique repetido produz resultado estável ou um erro de estado conhecido.

Falhas esperadas usam códigos semânticos: `400 validation_error`, `401 authentication_required`, `403 origin_not_allowed`, `404 resource_not_found`, `409 version_conflict|state_conflict|idempotency_conflict`, `413 upload_too_large`, `415 unsupported_media_type` e `500 internal_error`. Exceções de banco não vazam SQL, caminhos ou detalhes internos.

## Publicação, retenção e limpeza

Publicar usa a versão corrente já persistida; não aceita Markdown no request. O snapshot e o prazo de três dias são criados atomicamente. O relógio do banco é a fonte do prazo.

Um comando/processo interno `cleanup-due-publications` busca publicações vencidas com `FOR UPDATE SKIP LOCKED`, executa os purgadores registrados e grava `cleanup_completed_at`. Ele é seguro para repetição e pode rodar no mesmo container por um scheduler simples ou, preferencialmente na VPS, por `systemd timer`/cron chamando um container one-shot. Reiniciar a aplicação não perde o agendamento porque o estado está no PostgreSQL.

Cancelar limpeza grava `cleanup_cancelled_at`; republicar não agenda outra limpeza até nova decisão explícita. Retirar durante a janela marca a publicação `withdrawn`, remove-a imediatamente das consultas públicas, cancela a limpeza e devolve a escrita a `draft`. Depois de uma limpeza concluída, retirar continua ocultando a publicação, mas não promete recuperar contexto já apagado.

Nesta fase sem contexto efêmero implementado, a limpeza confirma o agendamento e completa sem apagar versões Markdown. Essa semântica será testada e ampliada quando os módulos privados futuros existirem.

## Projeções públicas e privacidade

`public_read` não importa schemas privados nem serializa modelos ORM. Suas consultas selecionam uma lista fechada de colunas a partir de `publications`, `publication_topics` e snapshots públicos. Toda consulta inclui `state = 'published'`.

- destaque: publicação ativa configurada; fallback para maior `published_at`;
- recentes/arquivo: somente snapshots ativos;
- livros: agrupamento por `book_slug` de publicações ativas;
- contagem, artigo mais recente e tópicos: derivados exclusivamente dessas publicações;
- livro sem publicação ativa: inexistente publicamente;
- capa: somente a cópia pública imutável referenciada pelo snapshot e exposta por URL controlada.

Testes de contrato mantêm uma denylist adicional de nomes privados (`messages`, `audio`, `transcript`, `suggestion`, `cleanupAt`, UUIDs internos), mas a proteção primária é a allowlist dos DTOs.

## Arquivos locais

Capas são gravadas sob um diretório configurado fora da árvore de código. O banco guarda uma chave/caminho relativo, nunca caminho absoluto fornecido pelo cliente. Upload valida limite, MIME detectado pelo conteúdo e dimensões; gera nome opaco; grava arquivo temporário e usa rename atômico.

Publicar copia a capa corrente, quando houver, para uma chave pública imutável pertencente ao snapshot; substituir ou excluir a capa privada não quebra artigos congelados. Somente essas cópias associadas a snapshots ativos são servidas em rota pública. Arquivos privados exigem sessão. Retirar uma publicação torna sua capa inacessível imediatamente; a remoção física só ocorre quando nenhuma publicação a referencia. Exclusões e substituições conciliam banco e disco por uma rotina idempotente, e arquivos órfãos podem ser varridos por comando de manutenção. Volumes Docker persistem o diretório. A porta de armazenamento expõe `put`, `open`, `delete` e geração de URL, permitindo S3 futuro sem antecipá-lo.

## Infraestrutura local e VPS

O Compose raiz terá serviços `frontend`, `backend` e `db`, além de perfis/comandos one-shot para `migrate`, bootstrap do autor, backup e cleanup. PostgreSQL e arquivos usam volumes nomeados. Somente o frontend/reverse proxy é publicado externamente na VPS; backend e banco ficam em rede interna. Em desenvolvimento, a API pode ser publicada apenas em loopback.

Configuração vem de ambiente validado na inicialização. Segredos ficam em arquivo não versionado ou secret store da VPS. Há configurações separadas para URL do banco, origem pública, diretório de arquivos, cookie, duração da sessão, limites de upload e nível de log. A aplicação falha cedo quando produção usa segredo fraco, cookie inseguro ou origem ausente.

O fluxo de deploy simples é: obter imagem/checkout versionado, criar backup, executar migrações compatíveis, subir os serviços, verificar readiness e só então trocar/recarregar o proxy. Migrações destrutivas usam estratégia expand/contract em entregas separadas.

## Migrações e dados de desenvolvimento

Alembic é a única autoridade sobre o schema; `create_all` não roda na inicialização normal. Cada mudança de modelo acompanha migração revisável com downgrade quando seguro. Readiness falha se o banco não estiver no head esperado.

Fixtures de desenvolvimento são explícitas e idempotentes, nunca executadas em produção. Testes de integração aplicam as migrações desde um banco vazio e também verificam upgrade a partir da revisão anterior relevante.

## Observabilidade e backups

Logs JSON incluem timestamp, nível, serviço, ambiente, request ID, rota, método, status e duração. Identificadores de recurso podem aparecer quando necessários, mas Markdown, senha, cookie, token, conteúdo de arquivo e payloads privados nunca são logados. Respostas propagam `X-Request-ID`.

Métricas mínimas podem ser derivadas de logs: latência/erros HTTP, falhas de conexão, conflitos de versão, publicações, limpezas vencidas e falhas de cleanup. Readiness não deve executar consultas caras.

Na VPS, um `pg_dump` diário e backup do volume de arquivos são enviados a destino fora da máquina, criptografados e retidos por política configurável. Um teste de restauração documentado é executado periodicamente; backup sem restore testado não conta como recuperação. Antes de migrações potencialmente destrutivas é criado backup adicional. Logs e backups respeitam a retenção de material privado.

## Estratégia de testes

### Unidade

- transições de status da escrita/publicação;
- geração e colisão de slugs;
- cálculo de prazo de três dias;
- fallback do destaque;
- idempotência e hash de request;
- regras de restauração e incremento de versão;
- allowlists dos DTOs públicos.

### Integração com PostgreSQL real

- migrações desde banco vazio;
- constraints, cascatas e proibição de excluir livro não vazio;
- compare-and-swap do autosave com duas transações concorrentes;
- atomicidade entre escrita e versão;
- publicação concorrente cria um único snapshot;
- cancelamento/retirada versus cleanup concorrente;
- retomada de cleanup após interrupção;
- consultas públicas ignoram retirados, rascunhos e livros privados.

SQLite não substitui PostgreSQL nesses testes.

### Contrato HTTP

- formatos existentes de `Book`, `Writing`, `WorkspacePayload`, `PublishResult`, `PublicLanding`, `PublicArticleSummary` e `PublicBookSummary`;
- autenticação e proteção de mutações por origem;
- envelope e códigos de erro;
- `Idempotency-Key` repetida e conflitante;
- nenhum campo privado em todas as respostas públicas;
- artigo e livro por slug retornam `404` quando não publicados.

### Fluxo ponta a ponta do backend

1. autenticar;
2. criar livro e escrita;
3. salvar com versão esperada e observar conflito de uma versão antiga;
4. restaurar versão;
5. publicar e ler o snapshot sem autenticação;
6. editar o rascunho e confirmar que o artigo público não mudou;
7. cancelar limpeza ou retirar dentro da janela;
8. executar cleanup vencido de modo repetido;
9. confirmar que somente dados permitidos permanecem públicos.

### Infraestrutura

- Compose sobe de volumes vazios e readiness passa após migrações;
- reinício preserva banco, arquivos e agendamentos;
- backup restaura em ambiente descartável;
- backend e banco não ficam expostos publicamente na configuração de VPS.

## Critérios de aceite

1. O autor autenticado consegue administrar livros, escritas e versões sem arquivos manuais.
2. Dois saves concorrentes não causam perda silenciosa de conteúdo.
3. Publicar congela exatamente uma versão e retorna slug e prazo de limpeza.
4. Alterar o rascunho ou o livro após publicar não muda o snapshot público.
5. Rotas públicas exibem apenas publicações ativas e nunca retornam dados privados ou IDs internos.
6. Cancelamento, retirada e cleanup são persistentes, transacionais e seguros para repetição.
7. Containers podem reiniciar sem perder banco, capas ou agendamentos.
8. Migrações, testes de integração, contrato e restauração de backup são reproduzíveis.
9. Nenhum SDK, chave, chamada ou fluxo de IA é introduzido nesta fase.

## Assunções conservadoras registradas

- A aplicação privada e a API são servidas na mesma origem na primeira VPS.
- Uma publicação é um snapshot histórico; atualizá-la requer retirada e nova publicação, não mutação in-place.
- Excluir livro não apaga escritas implicitamente.
- Capas são o único arquivo funcional desta fase; áudio será projetado com seu módulo futuro.
- Tópicos públicos são opcionais e manuais até existir um fluxo aprovado para produzi-los.
- Cleanup é persistido desde já, ainda que não haja contexto efêmero para apagar nesta fase.
- O arquivo público começa sem paginação; a ordem é determinística por `publishedAt` e slug, permitindo cursor futuro.

## Sequenciamento posterior

Após aprovação deste documento, o próximo artefato será um plano de implementação separado. Ele deve decompor infraestrutura, schema/migrações, autenticação, biblioteca/escritas, versões, publicação/cleanup, projeções públicas e operação em tarefas testáveis. Nenhuma implementação é autorizada por esta especificação isoladamente.
