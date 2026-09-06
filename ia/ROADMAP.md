# Roadmap de IA — Crawl, Walk, Run

## Propósito

Este roadmap guia o desenvolvimento da IA do deixedeserburro e o aprendizado do
autor em paralelo. Cada parte deve produzir uma capacidade real do produto,
uma decisão arquitetural documentada e evidências de qualidade.

O papel pretendido é **Product/AI Builder**: compreender modelos, contexto,
avaliação, segurança e custo o suficiente para dirigir o produto e revisar as
decisões técnicas, usando assistência de código para acelerar a implementação.

## Princípios permanentes

- Markdown é o documento canônico.
- A IA nunca altera o texto sem aceite explícito do autor.
- Conteúdo do autor, conteúdo externo e texto gerado precisam ter procedência
  distinguível.
- A chave e todas as chamadas de IA ficam exclusivamente no backend.
- Chamadas só acontecem por ação explícita; digitar e salvar não consomem IA.
- Testes automatizados usam um adaptador falso e não consomem API.
- Toda operação registra modelo, tokens, latência, resultado e custo estimado.
- Contexto é selecionado; o histórico inteiro não é enviado indefinidamente.
- Qualidade é medida com casos de avaliação, não somente por impressão.
- Uma abstração interna permite trocar modelo ou provedor sem contaminar o
  domínio, mas não serão implementados vários provedores antes da necessidade.

## Mapa das fases

```text
Crawl: núcleo textual confiável
   ↓
Walk: entradas multimodais e contexto durável
   ↓
Run: qualidade adaptativa, avaliações contínuas e operação avançada
```

## Crawl — núcleo textual confiável

Objetivo: conversar sobre uma escrita, usar links como fontes e transformar
uma conversa em sugestões revisáveis sem permitir edição autônoma do Markdown.

### Parte 1 — conversa contextual real

Entrega:

- endpoint autenticado associado a uma escrita;
- adaptador interno para a API de modelos;
- chamada pela Responses API;
- instrução editorial versionada;
- contexto inicial composto pelo Markdown atual e pela mensagem do autor;
- resposta exibida progressivamente;
- mensagens persistidas com estados de sucesso, interrupção e falha;
- registro de tokens, latência, modelo e custo estimado;
- limites pequenos de entrada e saída;
- bloqueio de novas chamadas ao alcançar o orçamento configurado;
- adaptador falso para testes e uma validação manual real controlada.

O primeiro modelo candidato é `gpt-5-mini`, por ser um trabalho editorial. Um
modelo menor poderá assumir posteriormente tarefas estreitas como extração,
classificação e resumo, após avaliação comparativa.

O que aprender:

1. Diferença entre modelo, API, SDK e produto ChatGPT.
2. Responses API: `instructions`, `input`, resposta, eventos de streaming e
   `usage`.
3. Tokens: entrada, saída, limite de contexto e por que contexto maior não
   significa contexto melhor.
4. Separação entre instruções estáveis, dados do documento e pedido do autor.
5. Streaming como protocolo: início, deltas, conclusão, interrupção e erro.
6. Fronteira de domínio: por que o módulo de conversa não deve depender
   diretamente do SDK do provedor.
7. Persistência: salvar a mensagem humana antes da geração e finalizar a
   resposta de forma recuperável.
8. Orçamento: contabilização por operação, teto de saída e bloqueio antes da
   chamada.
9. Testabilidade: adaptador falso determinístico versus teste manual real.
10. Avaliação inicial: conjunto pequeno de perguntas reais e critérios de
    utilidade, fidelidade ao texto, clareza e não alteração indevida.

Critério de conclusão:

> Em uma escrita autenticada, o autor envia uma pergunta sobre o Markdown,
> acompanha a resposta, recarrega a página sem perder a conversa e consegue
> identificar uso e custo. Falhas não alteram nem bloqueiam o documento.

### Parte 2 — sugestões estruturadas e revisão humana

Entrega:

- dois modos explícitos: conversar e propor alteração;
- saída estruturada validada por schema;
- sugestão referenciada a uma versão específica do Markdown;
- resumo, justificativa e alteração proposta;
- diff calculado pela aplicação, não inventado como fonte de verdade pelo
  modelo;
- aceitar, rejeitar e pedir ajuste;
- aplicação idempotente que cria uma nova versão;
- conflito visível quando o Markdown mudou desde a proposta.

O que aprender:

- Structured Outputs e JSON Schema;
- validação de fronteira e falhas de saída;
- optimistic concurrency e idempotência;
- representação de mudanças: texto completo, operações ou patch;
- human-in-the-loop e estados de uma sugestão;
- avaliações de fidelidade, preservação de voz e ausência de fatos inventados.

Critério de conclusão:

> A IA propõe uma mudança coerente, mas somente o aceite explícito e válido
> contra a versão-base cria uma nova versão do Markdown.

### Parte 3 — links como fontes controladas

Entrega:

- submissão de URL associada à conversa;
- validação contra SSRF e destinos internos;
- download com limites de tamanho, tempo e tipo;
- extração de título e conteúdo textual;
- resumo persistido com URL e procedência;
- seleção explícita das fontes usadas em cada resposta;
- citações que apontam para as fontes fornecidas;
- conteúdo externo tratado como dado não confiável, nunca como instrução.

O que aprender:

- SSRF, redirects, DNS/IP privados, timeouts e limites de download;
- extração de conteúdo e perda de informação;
- prompt injection indireta em páginas externas;
- grounding, atribuição e diferença entre citação e comprovação;
- contexto por referência versus copiar tudo para o prompt;
- testes adversariais para conteúdo externo.

Critério de conclusão:

> O autor adiciona um link, vê sua procedência e pode pedir uma resposta ou
> sugestão fundamentada nele, sem que instruções escondidas na página controlem
> o assistente.

### Parte 4 — fechar o Crawl

Entrega:

- resumo acumulado da conversa com mensagens recentes;
- política transparente de montagem e truncamento de contexto;
- suíte de avaliações versionada;
- comparação entre pelo menos dois modelos/configurações;
- painel simples de uso por escrita e mês;
- runbook de falhas, limites e troca de modelo;
- decisão baseada em evidência sobre o modelo padrão.

O Crawl termina quando o fluxo texto + links + sugestão revisável é confiável,
mensurável, retomável e barato.

## Walk — multimodalidade e contexto durável

Objetivo: permitir que áudio, texto e fontes convivam na mesma linha do tempo,
com processamento recuperável e contexto de longa duração.

Partes previstas:

1. Upload e gravação de áudio com armazenamento privado e validação.
2. Transcrição assíncrona com trabalhos persistidos, retry e idempotência.
3. Transcrição como evento da conversa e possível fonte de sugestão.
4. Resumo incremental com política de invalidação quando o texto muda.
5. Seleção e compressão de contexto por relevância, sem introduzir um banco
   vetorial automaticamente.
6. Roteamento econômico: modelo pequeno para tarefas mecânicas e modelo
   editorial para respostas e sugestões.
7. Avaliações multimodais e testes de recuperação após reinício.

O que estudar:

- upload seguro e armazenamento de objetos;
- speech-to-text, segmentação e timestamps;
- filas baseadas em PostgreSQL e semântica de retry;
- máquinas de estado e entrega pelo menos uma vez;
- sumarização incremental e perda de contexto;
- embeddings e busca semântica, aprendidos antes de decidir usá-los;
- roteamento de modelos por risco, custo e qualidade.

O Walk termina quando o autor pode intercalar áudio, texto e links, fechar a
aplicação, retomar o trabalho e produzir sugestões rastreáveis sem duplicação.

## Run — sistema editorial adaptativo e operável

Objetivo: elevar qualidade e eficiência usando evidência real de uso, sem
retirar o controle editorial do autor.

Partes previstas:

1. Pipeline contínuo de avaliações offline e amostragens de produção.
2. Versionamento e experimentação de prompts e modelos.
3. Avaliação por rubricas, comparações cegas e revisão humana periódica.
4. Recuperação avançada de trechos e fontes quando as avaliações justificarem.
5. Cache, batching e roteamento adaptativo orientados por métricas.
6. Observabilidade de qualidade, custo, latência e falhas por operação.
7. Detecção de regressões e rollback de configuração.
8. Políticas de retenção, exclusão e auditoria dos artefatos de IA.

O que estudar:

- desenho de evals e datasets representativos;
- LLM-as-judge com calibração humana e seus vieses;
- experimentos A/B e métricas de produto;
- retrieval, reranking e avaliação de recuperação;
- cache de prompts e otimização de custo por tarefa;
- tracing, SLOs e resposta a incidentes;
- threat modeling de aplicações com LLM;
- privacidade, retenção e governança de dados.

O Run não significa autonomia irrestrita. Significa que o sistema sabe escolher
recursos e detectar regressões, enquanto o autor continua soberano sobre o
Markdown e a publicação.

## Sessão de hoje — 4 horas de estudo ativo

As quatro horas são para **leitura seletiva, anotações e exercícios**. Elas
não incluem implementação. O código começa após o estudo mínimo, a conversa
arquitetural e a aprovação da especificação da Parte 1.

```text
estudo ativo
  → conversa e decisões de arquitetura
  → especificação aprovada
  → plano de implementação test-first
  → implementação e testes sem API
  → uma validação real controlada
```

Meta de hoje: conseguir explicar e revisar o design da Parte 1 antes de
implementar.

### Bloco 1 — 50 min: capítulo 1 do livro

Ler engenharia de IA, bots de conversa, planejamento de aplicações,
expectativas, manutenção e as três camadas da pilha.

Produzir, sem código:

- definir o caso de uso da Parte 1;
- listar o que é probabilístico e o que deve ser determinístico;
- desenhar as três camadas aplicadas ao deixedeserburro.

### Bloco 2 — 60 min: capítulo 2 do livro

Ler tamanho do modelo, amostragem, computação em tempo de teste, saídas
estruturadas e natureza probabilística. Adiar detalhes de ajuste fino.

Exercício:

- explicar por que duas respostas válidas podem ser diferentes;
- relacionar tamanho, qualidade, latência e custo;
- listar configurações que pertencem ao gateway do modelo.

### Intervalo — 10 min

### Bloco 3 — 50 min: capítulo 3 do livro

Ler desafios de avaliação, avaliação exata, exatidão funcional, IA como juiz,
limitações do juiz e avaliação comparativa. Adiar entropia, perplexidade e
embeddings.

Exercício:

- criar cinco perguntas reais;
- definir fatos obrigatórios e erros proibidos;
- criar uma rubrica de fidelidade, utilidade, clareza, voz e incerteza.

### Bloco 4 — 40 min: Responses API e streaming

Estudar `instructions`, `input`, `max_output_tokens`, `usage`, segurança da
chave, estados da resposta e eventos de streaming.

Exercício:

- desenhar `React → FastAPI → ModelGateway → OpenAI`, incluindo PostgreSQL;
- marcar segredo, dados privados, persistência e cobrança.

Fontes:

- [Developer quickstart](https://platform.openai.com/docs/quickstart)
- [Create a model response](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Streaming Responses API](https://platform.openai.com/docs/guides/streaming-responses)

### Bloco 5 — 30 min: síntese para a conversa de design

Responder por escrito:

1. Qual é a unidade persistida: conversa, mensagem, resposta ou evento?
2. Quais informações entram no contexto da primeira versão?
3. O que deve acontecer quando o Markdown exceder o limite configurado?
4. Como provar que uma resposta foi útil sem compará-la a uma frase exata?
5. Quais falhas podem ser tentadas novamente sem duplicar mensagens ou custo?

## Como usar este roadmap

Para cada parte:

1. estudar os conceitos indicados;
2. responder às decisões de produto e arquitetura;
3. escrever e aprovar uma especificação curta;
4. criar um plano de implementação test-first;
5. implementar com adaptadores falsos;
6. validar gates locais;
7. executar o menor smoke test real necessário;
8. registrar aprendizados, custo observado e decisão para a próxima parte.

Este arquivo contém direção e currículo. Especificações aprovadas continuam em
`docs/superpowers/specs/`, planos executáveis em `docs/superpowers/plans/` e o
estado retomável em `docs/handoffs/current.md`.
