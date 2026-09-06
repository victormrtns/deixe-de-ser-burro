# Conteúdos de estudo da IA — Entrelinhas

## Como estudar

Este currículo acompanha o `ROADMAP.md`. O objetivo não é consumir cursos por
completo, mas aprender o necessário para tomar a próxima decisão do produto,
revisar a implementação e avaliar o resultado.

Para considerar um conteúdo aprendido, o autor deve conseguir:

1. explicar o conceito com palavras próprias;
2. relacioná-lo a uma decisão concreta do Entrelinhas;
3. reconhecer pelo menos uma falha ou uso incorreto;
4. produzir o exercício indicado;
5. revisar o teste que demonstra o comportamento.

Os itens estão na ordem recomendada. Conteúdos marcados como **adiar** não
devem consumir tempo até a fase indicada.

---

## Crawl — núcleo textual confiável

### Parte 1 — conversa contextual real

#### 1. Produtos, API e modelos

Estudar exatamente:

- diferença entre ChatGPT, plataforma de API, modelo e SDK;
- cobrança separada entre ChatGPT e API;
- chave por projeto e variável de ambiente;
- diferença entre nome móvel de modelo e snapshot versionado;
- entrada, saída, contexto e tokens de raciocínio;
- latência até o primeiro token e latência total.

Saber decidir:

- por que a aplicação chama a API pelo backend;
- por que o modelo é configuração, não regra espalhada pelo domínio;
- quando fixar um snapshot depois de concluir avaliações.

Exercício: desenhar as fronteiras `React → FastAPI → ModelGateway → OpenAI` e
marcar onde existem segredo, dados privados e cobrança.

Fontes:

- [Developer quickstart](https://platform.openai.com/docs/quickstart)
- [Modelos da API](https://developers.openai.com/api/docs/models)
- [Segurança de API keys](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)

#### 2. Anatomia da Responses API

Estudar exatamente:

- `POST /v1/responses`;
- `model`, `instructions`, `input` e `max_output_tokens`;
- texto de saída e estados `completed`, `failed`, `in_progress`, `cancelled` e
  `incomplete`;
- objeto `usage`: tokens de entrada, saída e total;
- `store`: diferença entre retenção no provedor e persistência própria;
- identificadores da resposta e metadados sem dados sensíveis;
- erros de autenticação, rate limit, timeout e indisponibilidade.

Saber decidir:

- quais dados são persistidos pelo Entrelinhas;
- se `store` ficará desabilitado inicialmente;
- quais erros podem ser tentados novamente.

Exercício: escrever, em pseudocódigo, uma chamada completa e a transformação da
resposta do provedor para um objeto do domínio.

Fonte: [Create a model response](https://developers.openai.com/api/reference/resources/responses/methods/create)

#### 3. Instruções e montagem de contexto

Estudar exatamente:

- instruções da aplicação versus pedido do autor versus conteúdo do Markdown;
- delimitação de conteúdo não confiável;
- instruções estáveis antes dos dados dinâmicos;
- contexto mínimo suficiente;
- orçamento de tokens de entrada e saída;
- truncamento explícito versus falha silenciosa;
- preservação de voz e declaração de incerteza;
- por que prompt não substitui validação e autorização no código.

Saber decidir:

- primeira política de contexto: Markdown atual, últimas mensagens e pedido;
- tamanho máximo de Markdown aceito nesta parte;
- comportamento quando o limite for ultrapassado.

Exercício: escrever a versão `v1` da instrução editorial com no máximo 12
linhas e separar claramente instruções, Markdown e pergunta do autor.

Fonte: [Prompt engineering](https://platform.openai.com/docs/guides/prompt-engineering)

#### 4. Streaming ponta a ponta

Estudar exatamente:

- Server-Sent Events e formato `text/event-stream`;
- eventos, deltas, sequência e evento terminal;
- buffering em proxy e cliente;
- cancelamento pelo navegador e propagação ao backend;
- resposta parcial preservada;
- reconexão versus nova tentativa;
- diferença entre repetir transporte e repetir geração cobrada.

Saber decidir:

- estados `pending`, `streaming`, `completed`, `interrupted` e `failed`;
- o que o autor vê ao interromper ou perder conexão;
- quando uma tentativa cria uma nova mensagem.

Exercício: desenhar a máquina de estados e uma linha do tempo com queda do
navegador após três deltas.

Fontes:

- [Streaming da Responses API](https://platform.openai.com/docs/guides/streaming-responses)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [MDN Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

#### 5. Persistência e consistência

Estudar exatamente:

- conversa, mensagem e tentativa de geração como entidades distintas;
- persistir a mensagem humana antes da chamada;
- estados e timestamps da tentativa;
- identificador do provedor separado do identificador interno;
- commit antes de trabalho externo demorado;
- idempotência, retry e duplicação;
- transações curtas e recuperação após reinício.

Saber decidir:

- unidade persistida e relações entre as entidades;
- conteúdo parcial que permanece após falha;
- chave usada para impedir envio duplicado.

Exercício: propor tabelas e invariantes em linguagem natural, sem escrever a
migração ainda.

Fontes:

- [SQLAlchemy — session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [PostgreSQL — transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

#### 6. Custo, limites e observabilidade

Estudar exatamente:

- preço por tokens de entrada, entrada em cache e saída;
- limite estimado antes da chamada e contabilização real depois dela;
- diferença entre teto de tokens e teto financeiro;
- orçamento reservado para operação em andamento;
- modelo, versão da instrução, tokens, latência e status como telemetria;
- logs sem Markdown, mensagem, chave ou resposta.

Saber decidir:

- teto de desenvolvimento de US$ 2;
- reserva máxima de US$ 0,25 para smoke tests da Parte 1;
- limite inicial de saída por resposta;
- comportamento do produto ao atingir o teto.

Exercício: estimar o custo de três cenários usando a página de preços e depois
comparar a estimativa com o `usage` de uma única chamada manual.

Fontes:

- [API pricing](https://openai.com/api/pricing/)
- [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini)

#### 7. Testes e avaliação inicial

Estudar exatamente:

- teste unitário determinístico do domínio;
- adaptador falso versus mock do SDK;
- teste de contrato do gateway;
- smoke test manual real;
- caso de avaliação, entrada, critérios e anotação humana;
- rubricas: fidelidade ao Markdown, utilidade, clareza, preservação de voz e
  explicitação de incerteza;
- por que igualdade textual não mede qualidade de uma resposta generativa.

Saber decidir:

- quais comportamentos não exigem chamada real;
- quais cinco perguntas representam o uso esperado;
- limiar mínimo para aceitar a primeira configuração.

Exercício: criar cinco casos com Markdown, pergunta, fatos obrigatórios, erros
proibidos e uma escala de 1 a 4 para cada rubrica.

Fonte: [Evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices)

#### Adiar nesta parte

- embeddings e banco vetorial;
- RAG;
- agentes e múltiplas ferramentas;
- fine-tuning;
- múltiplos provedores;
- áudio;
- leitura de links;
- sugestões que alteram o Markdown;
- LLM-as-judge automático.

#### Evidência para concluir a Parte 1

- diagrama de fronteiras;
- instrução editorial `v1`;
- máquina de estados;
- modelo conceitual de persistência;
- planilha ou cálculo simples de três custos;
- cinco casos de avaliação;
- capacidade de revisar os testes e explicar as decisões acima.

---

### Parte 2 — sugestões estruturadas e revisão humana

#### Conteúdos exatos

1. **Structured Outputs**
   - JSON Schema, campos obrigatórios, enums e limites;
   - validação no provedor e nova validação na fronteira do backend;
   - recusa, saída incompleta e incompatibilidade de schema.
2. **Modelo de sugestão**
   - versão-base do Markdown;
   - trecho-alvo e âncoras;
   - justificativa, conteúdo proposto e procedência;
   - estados `pending`, `accepted`, `rejected`, `superseded` e `conflict`.
3. **Representação de mudança**
   - texto final completo versus operações versus patch;
   - diff como visualização calculada localmente;
   - riscos de offsets instáveis e correspondência ambígua.
4. **Concorrência e idempotência**
   - compare-and-swap com `expectedVersion`;
   - aceite idempotente;
   - conflito quando o documento mudou;
   - nunca fazer merge silencioso.
5. **Human-in-the-loop**
   - decisão reversível;
   - pedir ajuste sem aplicar a sugestão anterior;
   - feedback explícito e histórico auditável.
6. **Avaliação editorial**
   - preservação de sentido e voz;
   - fatos adicionados sem fonte;
   - omissões, alterações excessivas e escopo da proposta.

Exercícios:

- desenhar o schema de sugestão antes de escrever código;
- comparar as três representações de mudança em dois exemplos reais;
- criar casos de conflito e duplo clique no aceite;
- montar dez exemplos de sugestões boas, ruins e ambíguas.

Fontes:

- [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [JSON Schema](https://json-schema.org/learn/getting-started-step-by-step)
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html)

Adiar: tool calling, agente autônomo e aplicação automática de mudanças.

---

### Parte 3 — links como fontes controladas

#### Conteúdos exatos

1. **Modelo de ameaça de URL**
   - SSRF;
   - esquemas permitidos;
   - resolução DNS e faixas privadas/reservadas;
   - redirects e revalidação de cada destino;
   - portas, timeouts, tamanho máximo e tipo de conteúdo.
2. **Aquisição e extração**
   - download controlado;
   - HTML versus conteúdo principal;
   - charset, título, canonical URL e data;
   - falhas e qualidade da extração.
3. **Procedência**
   - URL original, URL final e instante de captura;
   - trecho utilizado versus resumo gerado;
   - citação clicável e fonte selecionada pelo autor.
4. **Prompt injection indireta**
   - conteúdo externo como dado não confiável;
   - instruções encontradas na página não alteram política;
   - exfiltração, chamadas de ferramentas e delimitação de conteúdo.
5. **Grounding e atribuição**
   - resposta apoiada versus inferência;
   - citação correta versus fonte apenas relacionada;
   - detectar afirmação sem suporte.
6. **Avaliação adversarial**
   - páginas enormes, redirects, loop, HTML malformado;
   - texto que tenta substituir instruções;
   - fonte contraditória e fonte insuficiente.

Exercícios:

- construir uma tabela de URLs permitidas e bloqueadas;
- anotar três artigos reais, ligando afirmações aos trechos de suporte;
- escrever dez testes adversariais antes da implementação.

Fontes:

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [OpenAI safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)

Adiar: crawling amplo, busca geral na web, grafo de conhecimento e ingestão de
PDFs complexos.

---

### Parte 4 — consolidação do Crawl

#### Conteúdos exatos

1. **Memória de conversa**
   - janela recente e resumo acumulado;
   - fatos, decisões e perguntas abertas;
   - perda de informação e invalidação do resumo.
2. **Política de contexto**
   - seleção, ordenação, limites e truncamento;
   - estimativa de tokens antes da chamada;
   - prefixos estáveis e prompt caching.
3. **Dataset de avaliação**
   - casos simples, limítrofes, adversariais e regressões reais;
   - separação entre conjunto de desenvolvimento e conjunto de validação;
   - versionamento de entradas, rubricas, prompt e modelo.
4. **Comparação de configurações**
   - qualidade, custo, latência e taxa de falha;
   - comparação cega;
   - trade-off em vez de “melhor modelo” absoluto.
5. **Uso e operação**
   - agregação por escrita, operação, modelo e mês;
   - alertas perto do limite;
   - runbook para falha do provedor, rate limit e troca de modelo.

Exercícios:

- resumir uma conversa e listar o que foi perdido;
- rodar o mesmo conjunto de avaliação em duas configurações;
- escrever um relatório de decisão de uma página.

Fontes:

- [Prompt caching](https://platform.openai.com/docs/guides/prompt-caching)
- [Model optimization](https://platform.openai.com/docs/guides/model-optimization)
- [Evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices)

---

## Walk — multimodalidade e contexto durável

### Parte 1 — upload e armazenamento privado de áudio

Estudar:

- `multipart/form-data`, streaming de upload e backpressure;
- MIME declarado versus conteúdo detectado;
- limites de bytes e duração;
- nomes opacos, escrita atômica e metadados separados;
- autorização para servir e excluir arquivos;
- lifecycle e retenção de dados privados.

Exercício: threat model do upload e matriz de arquivos aceitos/rejeitados.

Fontes:

- [FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

### Parte 2 — transcrição assíncrona recuperável

Estudar:

- speech-to-text, idioma, timestamps e segmentação;
- qualidade versus compressão do áudio;
- trabalho persistido e worker;
- estados `queued`, `running`, `completed`, `failed` e `cancelled`;
- retry com backoff, limite de tentativas e erro permanente;
- semântica pelo menos uma vez e idempotência;
- claim de jobs com `FOR UPDATE SKIP LOCKED`;
- recuperação após reinício.

Exercício: máquina de estados e simulação de queda em cada transição.

Fontes:

- [Speech to text](https://platform.openai.com/docs/guides/speech-to-text)
- [PostgreSQL SELECT locking](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)

### Parte 3 — linha do tempo multimodal

Estudar:

- evento de áudio, transcrição e mensagem como tipos relacionados;
- ordenação por servidor e estabilidade de identidade;
- atualização de status sem duplicar eventos;
- acessibilidade de controles e transcrições;
- interrupção do processamento sem bloquear edição manual.

Exercício: desenhar uma conversa intercalando texto, áudio, retry e resposta.

### Parte 4 — resumo e memória durável

Estudar:

- memória episódica versus resumo;
- resumo incremental e checkpoints;
- fatos com procedência;
- invalidação quando mensagens são removidas;
- avaliação de cobertura e contradição;
- política de retenção após publicação.

Exercício: criar uma rubrica para medir se o resumo preservou decisões e
incertezas importantes.

### Parte 5 — recuperação de contexto

Estudar:

- busca lexical, embeddings e busca híbrida;
- chunking semântico e sobreposição;
- metadados e filtros por escrita/fonte;
- top-k, recall, precision e nDCG;
- reranking;
- diferença entre retrieval e geração.

Decisão obrigatória: somente introduzir embeddings se avaliações mostrarem que
janela recente + resumo + seleção explícita são insuficientes.

Exercício: montar manualmente dez consultas e os trechos que deveriam ser
recuperados antes de escolher tecnologia.

Fontes:

- [OpenAI embeddings](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL full text search](https://www.postgresql.org/docs/current/textsearch.html)

### Parte 6 — roteamento econômico de modelos

Estudar:

- classificação da tarefa por risco e complexidade;
- modelo pequeno para extração, resumo e classificação;
- modelo editorial para conversa e sugestão;
- fallback, timeout e indisponibilidade;
- avaliação por rota;
- custo esperado por tarefa e orçamento reservado.

Exercício: tabela `operação → requisitos → modelo candidato → limite → fallback`
baseada em resultados de avaliação.

### Parte 7 — avaliação multimodal e resiliência

Estudar:

- dataset pequeno de áudios reais consentidos;
- word error rate e suas limitações;
- preservação de nomes, citações e termos de livros;
- teste após reinício e processamento duplicado;
- rastreabilidade áudio → transcrição → sugestão.

Exercício: avaliar manualmente dez minutos de áudio representativo e registrar
erros que realmente afetam a escrita.

---

## Run — qualidade adaptativa e operação avançada

### Parte 1 — pipeline contínuo de avaliações

Estudar:

- dataset versionado e casos de regressão;
- eval determinística, avaliação humana e avaliação por modelo;
- calibração do juiz com humanos;
- falso senso de precisão em notas agregadas;
- execução offline em mudanças de prompt/modelo;
- critérios de promoção e rollback.

Exercício: definir um gate que bloqueia regressão grave sem exigir que toda
métrica melhore.

Fonte: [OpenAI evals](https://platform.openai.com/docs/guides/evals)

### Parte 2 — versionamento e experimentos

Estudar:

- versão de prompt, schema, modelo e política de contexto;
- reprodutibilidade e snapshots;
- comparação cega e ordem aleatória;
- tamanho de amostra e interpretação cuidadosa;
- A/B apenas quando houver tráfego e hipótese suficientes.

Exercício: template de relatório contendo hipótese, métrica, custo, resultado e
decisão.

### Parte 3 — LLM-as-judge com supervisão humana

Estudar:

- rubricas atomizadas;
- viés de posição, verbosidade e auto-preferência;
- exemplos âncora;
- concordância entre juiz e humano;
- amostragem periódica para recalibração;
- tarefas que não devem ser delegadas ao juiz.

Exercício: avaliar cegamente vinte pares, comparar humano e juiz e investigar
discordâncias.

### Parte 4 — retrieval e reranking avançados

Estudar:

- avaliação separada de recuperação e geração;
- busca híbrida;
- filtros e controle de acesso antes da busca;
- reranking e diversidade de resultados;
- citações ligadas ao trecho recuperado;
- custo e latência adicionais.

Exercício: relatório mostrando que a recuperação avançada melhora casos reais
antes de incorporá-la ao caminho padrão.

### Parte 5 — otimização de custo e latência

Estudar:

- prompt caching e prefixo estável;
- batching para tarefas não interativas;
- redução de contexto baseada em avaliações;
- modelos diferentes por operação;
- latência até primeiro token, duração total e timeout;
- custo por resultado aceito, não apenas por chamada.

Exercício: decompor custo mensal por operação e priorizar as duas maiores
fontes de desperdício.

### Parte 6 — observabilidade e SLOs

Estudar:

- tracing por operação sem registrar conteúdo privado;
- taxa de sucesso, cancelamento, retry e recusa;
- p50/p95 de latência;
- custo por escrita e por sugestão aceita;
- SLI, SLO e error budget;
- alertas acionáveis e runbooks.

Exercício: definir três SLOs e a ação operacional quando cada um falhar.

Fontes:

- [OpenTelemetry concepts](https://opentelemetry.io/docs/concepts/)
- [Google SRE — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

### Parte 7 — segurança, privacidade e governança

Estudar:

- threat modeling específico de LLM;
- prompt injection direta e indireta;
- autorização de ferramentas e least privilege;
- minimização de dados;
- retenção e exclusão verificável;
- auditoria de decisões e incident response;
- políticas de conteúdo e uso aplicáveis.

Exercício: threat model completo do fluxo autor → fonte → modelo → sugestão →
publicação, com mitigação e teste por ameaça.

Fontes:

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OpenAI safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)

### Parte 8 — operação adaptativa com controle editorial

Estudar:

- roteamento baseado em política explícita;
- fallback seguro e degradação graciosa;
- aprovação humana proporcional ao impacto;
- rollback de configuração;
- kill switch de IA sem derrubar editor e publicação;
- revisão periódica de custo, qualidade e retenção.

Exercício: simular provedor indisponível, orçamento esgotado, regressão de
qualidade e fonte maliciosa; documentar como o produto continua utilizável.

---

## Plano de hoje — quatro horas da Parte 1 do Crawl

Estas quatro horas são de **estudo ativo**: leitura seletiva, notas e
exercícios. Elas não incluem implementação. A sequência completa é:

```text
estudar → discutir arquitetura → aprovar especificação → planejar → implementar
```

Para hoje, use os tempos assim:

| Tempo | Conteúdo | Resultado esperado |
|---|---|---|
| 00:00–00:50 | Capítulo 1, seleção indicada abaixo | Caso de uso, fronteiras e três camadas |
| 00:50–01:50 | Capítulo 2, seleção indicada abaixo | Modelo mental probabilístico e configurações |
| 01:50–02:00 | Intervalo | — |
| 02:00–02:50 | Capítulo 3, seleção indicada abaixo | Cinco casos e rubrica de avaliação |
| 02:50–03:30 | Responses API e streaming | Diagrama técnico e fronteiras de segurança |
| 03:30–04:00 | Síntese aplicada | Cinco decisões para o design |

### Seleção do capítulo 1 — dentro dos primeiros 50 min

Ler: dos modelos de fundação à engenharia de IA, bots de conversa,
planejamento de aplicações, avaliação do caso de uso, expectativas, etapas,
manutenção, pilha de engenharia de IA, três camadas e comparação com engenharia
full-stack. Passar rapidamente pelos demais casos de uso.

### Seleção do capítulo 2 — 60 min

Ler: tamanho do modelo, amostragem, estratégias de amostragem, computação em
tempo de teste, saídas estruturadas e natureza probabilística. Adiar detalhes
de pós-treinamento e ajuste fino.

### Seleção do capítulo 3 — 50 min

Ler: desafios da avaliação, avaliação exata, exatidão funcional, IA como juiz,
limitações do juiz e desafios da avaliação comparativa. Adiar entropia,
perplexidade, embeddings e detalhes matemáticos.

### Responses API e streaming — 40 min

Ler o quickstart, a criação de Responses e o guia de streaming, focando em
`model`, `instructions`, `input`, `max_output_tokens`, `store`, estados,
`usage`, eventos e segurança da chave.

Entregar o diagrama `React → FastAPI → ModelGateway → OpenAI`, incluindo
PostgreSQL, e marcar segredo, dados privados, persistência e cobrança.

### Síntese — últimos 30 min

Responder às cinco perguntas do checkpoint no fim desta seção. Persistência
detalhada, transações, SSE e testes serão aprofundados durante o design e antes
de suas tarefas de implementação; não precisam ser dominados integralmente
hoje.

Checkpoint:

1. O que entra no contexto da primeira versão?
2. O que acontece quando o Markdown é grande demais?
3. Uma resposta interrompida é preservada?
4. Qual operação pode ser repetida sem duplicação?
5. Que evidência permitirá dizer que a Parte 1 está boa?

Depois das quatro horas:

1. revisar as respostas durante o brainstorming;
2. fechar e aprovar a especificação da Parte 1;
3. criar o plano de implementação test-first;
4. implementar com o adaptador falso;
5. fazer uma única validação real controlada ao final.
