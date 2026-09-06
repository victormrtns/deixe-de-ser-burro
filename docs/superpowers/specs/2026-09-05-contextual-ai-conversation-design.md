# Conversa contextual real — Especificação de design

## Contexto

O deixedeserburro já possui autenticação, biblioteca, escritas com Markdown
versionado, publicação e leitura pública. Chat, áudio, sugestões e uso de IA
ainda são demonstrativos no frontend e não possuem implementação real no
backend.

Esta fase é a Parte 1 do Crawl de IA. Ela substitui somente a conversa
demonstrativa por uma conversa textual real e contextualizada. Sugestões que
podem alterar o Markdown, links e áudio permanecem em fases posteriores.

A proposta de valor do produto depende da IA, mas o provedor não pode se tornar
um ponto único de falha para capacidades já existentes. Indisponibilidade,
configuração ausente ou orçamento esgotado bloqueiam o assistente, não o
editor, histórico, leitura ou publicação.

## Objetivos

1. Permitir que o autor converse com a IA sobre o Markdown da escrita atual.
2. Exibir a resposta progressivamente e preservar resultados parciais.
3. Persistir conversa, mensagens, tentativas, memória local e uso.
4. Incorporar linha editorial global e feedback explícito por escrita.
5. Manter domínio e frontend independentes do protocolo da OpenAI.
6. Controlar contexto e custo antes de cada chamada.
7. Validar comportamento com gateway falso antes de qualquer chamada cobrada.

## Fora de escopo

- propostas estruturadas de alteração e aplicação de diff;
- aceite, rejeição ou ajuste de sugestões;
- links, busca externa, RAG ou embeddings;
- áudio e transcrição;
- memória compartilhada entre escritas;
- fine-tuning ou treinamento com feedback;
- múltiplos provedores;
- retry automático;
- seleção inteligente de trechos de Markdown;
- resumo de conversas longas.

## Princípios

- O Markdown continua canônico e sob controle do módulo `writings`.
- A Parte 1 não altera o Markdown.
- Toda chamada é iniciada por ação explícita do autor.
- Dados externos ao sistema probabilístico são validados por código.
- Conteúdo privado não aparece em logs operacionais.
- Testes automatizados não consomem API.
- Toda tentativa potencialmente cobrada é auditável separadamente.

## Arquitetura

```text
Workspace da escrita
   │
   ├── mensagem do autor
   ▼
API autenticada de conversa
   │
   ├── carrega Markdown atual
   ├── carrega memória da escrita
   ├── carrega mensagens recentes
   └── carrega instrução editorial versionada
   ▼
AssistantService
   │
   ├── valida contexto e orçamento
   ├── persiste mensagem e tentativa
   └── monta entrada independente de provedor
   ▼
ModelGateway
   ├── OpenAI Responses API em runtime habilitado
   └── FakeModelGateway nos testes
   │
   ▼
eventos de domínio em streaming
   │
   ├── atualizam a interface
   ├── persistem conteúdo recebido
   └── finalizam uso, custo e estado
```

### Fronteiras

- `conversations`: conversas, mensagens e leitura do histórico.
- `assistant`: montagem de contexto, orquestração, tentativas e memória.
- `ai`: contrato `ModelGateway` e tipos independentes de provedor.
- `ai/providers/openai`: cliente OpenAI e tradução para eventos do domínio.
- `usage`: reserva, contabilização e bloqueio por orçamento.
- `writings`: Markdown e versões, consumidos somente para leitura nesta fase.
- frontend: consome contratos e eventos do deixedeserburro, sem importar tipos ou
  nomes de eventos da OpenAI.

Não será criada uma abstração genérica para todos os provedores. O contrato
interno cobrirá apenas as capacidades usadas: texto, streaming, cancelamento e
uso. Isso permite substituição futura sem antecipar APIs inexistentes.

## Modelo conceitual

```text
Writing
└── Conversation (uma principal por escrita)
    ├── Message
    ├── GenerationAttempt
    └── WritingMemory
```

### Conversation

Existe no máximo uma conversa principal por escrita nesta fase. Ela possui
identidade interna, `writing_id` e timestamps.

### Message

Representa conteúdo visível. Possui conversa, papel `author` ou `assistant`,
conteúdo, estado e timestamps. Estados de mensagem do assistente são
`streaming`, `completed` ou `interrupted`. Mensagens do autor são persistidas
antes da chamada externa.

### GenerationAttempt

Representa cada chamada potencialmente cobrada. Possui a mensagem do autor que
a originou, mensagem de resposta, número da tentativa, modelo, versão da
instrução, estado, identificador do provedor, tokens de entrada/saída/total,
custo estimado, latência, código de erro seguro e timestamps.

Estados são `pending`, `streaming`, `completed`, `interrupted` e `failed`.
Somente uma transição válida pode finalizar uma tentativa. Retry explícito cria
outra tentativa ligada à mesma mensagem do autor; não duplica a mensagem.

### WritingMemory

Contém memória estruturada e local à escrita: preferências editoriais locais,
decisões confirmadas e perguntas abertas. Cada item mantém procedência na
mensagem que o originou. A memória não é treinamento do modelo e não atravessa
automaticamente a fronteira entre escritas.

## Hierarquia de contexto

```text
regras fixas de segurança e soberania
        ↓
linha editorial global versionada
        ↓
memória local da escrita
        ↓
Markdown e seis pares completos recentes
        ↓
pedido atual
```

Camadas inferiores não podem sobrescrever regras superiores. Conteúdo do
Markdown e mensagens é tratado como dado, não como instrução da aplicação.

### Regras fixas

Ficam no código versionado e incluem privacidade, segurança, escopo da operação
e a proibição de alterar o documento sem aceite explícito.

### Linha editorial global

Skills e instruções pessoais usadas no desenvolvimento podem inspirar o
conteúdo, mas não são dependência de runtime. A fonte canônica inicial é um
arquivo Markdown próprio e versionado no repositório, carregado pelo backend,
sem segredos e com limite de tamanho.

A linha editorial descreve voz, formalidade, estrutura, tratamento de citações,
vícios a evitar, limite de reorganização e distinção entre ideias do autor e
complementos externos. Uma interface de edição fica fora desta parte.

### Memória local

Feedback casual, como gostei ou não gostei, pode ser registrado para avaliação,
mas não vira preferência. A memória muda somente a partir de feedback explícito
como “lembrar nesta escrita” ou “neste texto, mantenha este tom”. Preferências
locais podem especializar a linha global, mas não enfraquecem regras fixas.

Nesta parte, a ação explícita persiste diretamente um item de memória
estruturado a partir do texto confirmado pelo autor; ela não dispara outra
chamada de IA. Extração automática de preferências fica fora do escopo.

Somente respostas concluídas podem originar uma atualização de memória. A
atualização mantém vínculo com a mensagem de procedência e é reversível no
banco, ainda que uma interface completa de gestão não faça parte desta fase.

### Histórico recente

Entram no contexto no máximo os últimos seis pares completos de autor e
assistente. Respostas `interrupted` ou `failed` permanecem visíveis, mas não
entram automaticamente em novas chamadas. A quantidade de pares não supera o
limite total de entrada.

### Markdown grande demais

O Markdown atual entra completo. Se a composição ultrapassar o limite de
entrada configurado, a operação é bloqueada antes da persistência da mensagem e
da reserva de orçamento. Não há truncamento, seleção ou resumo silencioso. A
interface explica o limite e nenhuma chamada externa ocorre.

## Fluxo de envio

1. O frontend envia escrita, conteúdo da mensagem e chave idempotente da
   intenção.
2. O backend autentica e autoriza acesso à escrita.
3. O serviço carrega e valida todas as camadas de contexto.
4. O serviço estima o custo máximo e tenta reservar orçamento.
5. Em uma transação curta, persiste a mensagem do autor e a tentativa
   `pending`, respeitando idempotência.
6. O serviço abre o streaming com o gateway e marca a tentativa `streaming`.
7. Deltas de texto são traduzidos para eventos do domínio, enviados ao cliente
   e persistidos em lotes no máximo a cada segundo ou 4 KiB, o que ocorrer
   primeiro. O evento terminal força a persistência do lote restante.
8. Em conclusão, o serviço persiste a mensagem final, uso real e latência,
   substitui a reserva e marca a tentativa `completed`.
9. Em cancelamento ou perda de conexão depois de haver conteúdo, preserva a
   resposta parcial como `interrupted` e finaliza a contabilidade disponível.
10. Em falha sem resposta útil, marca a tentativa `failed` e libera ou ajusta a
    reserva conforme haja uso informado.

Falha de persistência anterior à chamada impede que a chamada comece. Escritas
no documento continuam independentes durante todo o fluxo.

## Contrato de streaming

O transporte usa `POST` autenticado com resposta `text/event-stream`, consumida
pelo frontend com `fetch` e leitura incremental do corpo. Os eventos públicos
do deixedeserburro são:

- `generation.started`: tentativa aceita e identificada;
- `response.delta`: fragmento textual ordenado;
- `response.completed`: conteúdo concluído e uso registrado;
- `response.interrupted`: conteúdo parcial preservado;
- `response.failed`: erro seguro e indicação de retry manual.

Cada evento possui versão de schema, identificador da tentativa e número de
sequência. O adaptador OpenAI é responsável por traduzir eventos do provedor.
O frontend ignora eventos de versões desconhecidas sem corromper a conversa.

Parar é uma ação explícita. Não há reconexão que reinicie uma geração nem retry
automático. `Tentar novamente` cria uma nova tentativa auditável.

## Provedor e configuração

- Integração pela Responses API.
- Chave somente em variável de ambiente do backend.
- `gpt-5-mini` como primeiro candidato, não como decisão permanente.
- `max_output_tokens` inicial de 800.
- `store=false` nas chamadas da Responses API; o deixedeserburro mantém sua própria
  persistência.
- Timeouts explícitos e erros do SDK traduzidos para códigos internos.

O `FakeModelGateway` emite a mesma sequência de eventos do contrato interno,
incluindo cenários de conclusão, interrupção, timeout, rate limit e saída
inválida.

## Orçamento e uso

O saldo da conta OpenAI não é o orçamento do produto.

- teto interno do desenvolvimento da Parte 1: US$ 2;
- máximo reservado para validações manuais reais: US$ 0,25;
- custo de testes automatizados: zero;
- estados: `normal`, `near_limit` e `blocked`;
- estimativa conservadora e reserva antes da chamada;
- substituição da reserva pelo uso real ao finalizar;
- bloqueio se a reserva ultrapassar o disponível;
- ausência de retry automático;
- nenhuma chamada manual real sem aviso explícito ao autor.

O registro de uso inclui escrita, operação, tentativa, modelo, tokens, custo,
latência e estado. Logs de observabilidade usam apenas identificadores opacos e
métricas; nunca Markdown, mensagens, respostas ou chave.

O orçamento definitivo de produção será decidido com dados observados, não com
o saldo atual nem com valores fictícios da interface.

## Erros e recuperação

- chave ausente: assistente indisponível; demais capacidades intactas;
- autenticação expirada: preservar rascunho da mensagem e solicitar login;
- contexto grande demais: bloquear antes da chamada;
- orçamento insuficiente: bloquear antes da chamada;
- rate limit ou indisponibilidade: tentativa `failed` e retry manual;
- timeout com conteúdo: preservar como `interrupted`;
- resposta inválida: não concluir nem atualizar memória;
- persistência indisponível: não iniciar chamada externa;
- erro interno: mensagem segura e logs sem conteúdo privado;
- toda falha deixa o Markdown inalterado.

Erros exibidos informam se retry é seguro e se uma nova chamada pode gerar
custo. Toasts não são o único canal de erros recuperáveis.

## Segurança e privacidade

- Todas as rotas são autenticadas e autorizadas pela escrita.
- A chave nunca chega ao frontend, banco ou logs.
- Entradas possuem limites de caracteres/bytes e validação de schema.
- Contexto de uma escrita nunca inclui dados de outra.
- Identificadores enviados ao provedor não contêm dados pessoais ou títulos.
- Mensagens e Markdown não entram em telemetria operacional.
- Instruções contidas no Markdown não substituem regras da aplicação.
- Rotas públicas nunca expõem conversa, memória, tentativas ou uso.

## Testes

### Unidade — gateway falso, custo zero

- ordem e delimitação das camadas de contexto;
- limite total e rejeição de Markdown grande;
- janela de seis pares completos;
- exclusão de respostas interrompidas e falhas do contexto;
- reserva, conciliação e bloqueio de orçamento;
- transições válidas de tentativa;
- feedback casual versus memória explícita;
- isolamento da memória por escrita.

### Integração — PostgreSQL e gateway falso, custo zero

- autenticação e autorização;
- idempotência do envio;
- persistência antes da geração;
- sequência e ordenação de eventos;
- conclusão, cancelamento, timeout e retry manual;
- resposta parcial após recarregar;
- recuperação após reinício;
- nenhuma chamada quando banco, contexto ou orçamento falha;
- isolamento entre duas escritas.

### Frontend — API falsa, custo zero

- resposta progressiva;
- ação de parar;
- estados falho e interrompido;
- retry explícito;
- histórico após recarga;
- mensagem digitada preservada após expiração de sessão;
- editor utilizável durante geração e falhas;
- nenhum dado fictício de custo.

### Avaliação editorial humana

O conjunto inicial possui cinco casos reais. Cada caso define Markdown,
pergunta, fatos obrigatórios e erros proibidos. A rubrica de 1 a 4 mede:

- fidelidade ao Markdown;
- utilidade;
- clareza;
- preservação de voz;
- explicitação de incerteza.

A configuração candidata precisa de média mínima 3 em cada dimensão.
Fidelidade abaixo de 3 em qualquer caso reprova a configuração,
independentemente da média geral. Igualdade textual não é critério.

### Smoke test real

Somente após todos os gates falsos passarem, uma chamada curta valida conexão,
streaming, persistência, uso e custo. A execução requer aviso explícito ao
autor, nunca ultrapassa a reserva de US$ 0,25 e registra o valor observado.

E2E visual com Chromium só será declarado quando o navegador realmente iniciar
no ambiente. Testes unitários ou de integração não substituem essa evidência.

## Critérios de aceite

1. O autor conversa sobre o Markdown atual em uma escrita autenticada.
2. A resposta aparece progressivamente e a conversa sobrevive à recarga.
3. Cancelamento e falha preservam conteúdo parcial sem alterar o Markdown.
4. Retry explícito não duplica a mensagem do autor e cria tentativa separada.
5. Contexto respeita hierarquia, isolamento, seis pares e limite total.
6. Feedback explícito atualiza somente a memória daquela escrita.
7. Toda tentativa registra estado, modelo, uso, custo e latência disponíveis.
8. Contexto ou orçamento inválido impede chamada externa.
9. Testes automatizados não acessam a OpenAI.
10. Editor, histórico, leitura e publicação funcionam sem a IA.
11. Nenhum artefato privado aparece em rotas públicas ou logs operacionais.
12. O smoke test real só ocorre com aviso e dentro da reserva aprovada.
