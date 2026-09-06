# Parte 1 do Crawl — conversa contextual real

## Estado

Design em construção. Este documento registra as decisões aprovadas durante o
brainstorming. Depois de fechar arquitetura, fluxo, contexto, erros, custo e
testes, as decisões serão consolidadas em uma especificação formal em
`docs/superpowers/specs/`.

## Caso de uso aprovado

O Entrelinhas é um sistema editorial assistido por IA, reativo às entradas do
autor. A IA recebe o Markdown e as mensagens da escrita; no futuro também
receberá links e áudio. Ela mantém o contexto automaticamente, incorpora
feedback explícito e pode responder ou propor alterações, mas nunca modifica o
documento sem aprovação.

A proposta de valor do produto depende da IA. Ainda assim, uma indisponibilidade
do provedor ou o esgotamento do orçamento bloqueia somente as capacidades de IA.
Editor, histórico, leitura e publicação continuam disponíveis.

## Escopo desta parte

A Parte 1 entrega conversa contextual real sobre o Markdown. Sugestões formais,
links e áudio pertencem às partes posteriores do roadmap.

Inclui:

- conversa associada a uma escrita autenticada;
- Markdown atual e memória local como contexto;
- respostas progressivas;
- persistência da conversa e de respostas parciais;
- registro de modelo, tokens, custo, latência e resultado;
- limite financeiro e limites de entrada e saída;
- adaptador falso nos testes e validação real mínima.

## Arquitetura aprovada

```text
Workspace da escrita
   │
   ├── mensagem do autor
   ▼
API autenticada de conversa
   │
   ├── carrega Markdown atual
   ├── carrega memória daquela escrita
   ├── carrega mensagens recentes
   ├── aplica instrução editorial versionada
   ▼
AssistantService
   │
   ├── verifica orçamento e limites
   ├── monta o contexto
   ├── persiste a tentativa
   ▼
ModelGateway
   │
   ├── OpenAI Responses API
   └── FakeModelGateway nos testes
   │
   ▼
stream de resposta
   │
   ├── persiste conteúdo recebido
   ├── registra tokens, custo e latência
   └── atualiza a memória da escrita
```

### Fronteiras dos módulos

- `conversations`: conversas e mensagens persistidas.
- `assistant`: regras de contexto, orçamento, geração e memória.
- `ai/providers/openai`: SDK e tradução dos eventos específicos da OpenAI.
- `usage`: tokens, custo estimado e bloqueio por orçamento.
- `writings`: proprietário exclusivo do Markdown e de suas versões.
- frontend: consome eventos do domínio do Entrelinhas, sem conhecer eventos
  específicos da OpenAI.

## Memória dinâmica aprovada

A memória é isolada por escrita. Feedback fornecido em uma escrita não altera
automaticamente o comportamento em outros livros ou textos.

A memória local pode conter:

- mensagens recentes;
- feedback textual do autor;
- decisões confirmadas;
- preferências locais, como tom ou estrutura;
- perguntas ainda abertas.

O autor não escreve resumos manualmente. O sistema deriva e atualiza a memória
a partir de interações relevantes. Isso não é treinamento nem fine-tuning do
modelo: aprender com feedback significa atualizar contexto persistido e
recuperável daquela escrita.

## Hierarquia de contexto aprovada

```text
regras fixas de segurança e soberania do autor
        ↓
linha editorial global do autor
        ↓
memória e preferências desta escrita
        ↓
Markdown e mensagens recentes
        ↓
pedido atual
```

As skills usadas pelo Codex durante o desenvolvimento podem inspirar a linha
editorial, mas não são dependência de runtime do Entrelinhas. O produto consome
um artefato editorial próprio, explícito e versionado.

### Regras fixas

As regras fixas pertencem à aplicação e não podem ser substituídas por conteúdo
do Markdown, mensagens, memória ou instruções editoriais. Incluem segurança,
privacidade e a proibição de alterar o documento sem aceite explícito.

### Linha editorial global

A linha editorial descreve preferências aplicáveis a todas as escritas, como:

- voz e nível de formalidade;
- preferência por concisão ou desenvolvimento ensaístico;
- tratamento de citações e referências;
- estruturas preferidas;
- clichês e vícios a evitar;
- limite para reorganização das ideias;
- distinção entre ideias do autor e complementos externos.

No Crawl, a fonte canônica inicial será um arquivo Markdown versionado no
repositório e carregado pelo backend. Uma interface para edição pode ser
adicionada posteriormente. O artefato não contém segredos, possui limite de
tamanho e deve ser coberto por casos de avaliação editorial.

### Preferências locais

A memória de uma escrita complementa a linha editorial e pode especializá-la
naquele contexto. Exemplo: uma preferência global por concisão pode coexistir
com a decisão local de preservar períodos longos em um ensaio específico. A
preferência local nunca afrouxa regras fixas de segurança ou soberania.

## Política inicial para documentos grandes

Na Parte 1, o Markdown é enviado integralmente quando estiver dentro do limite
configurado. Se ultrapassar esse limite, o backend rejeita a operação antes da
chamada ao provedor e a interface explica que o documento é grande demais para
o contexto atual.

Não haverá truncamento silencioso, resumo automático ou seleção automática de
trechos nesta parte. Portanto, uma operação bloqueada por tamanho não gera
custo e não produz resposta baseada em contexto incompleto.

Resumo acumulado e seleção de trechos continuam planejados para o fechamento
do Crawl, quando houver documentos e perguntas reais para avaliar perda de
informação. O limite numérico será definido durante o design de contexto e
orçamento, considerando o modelo escolhido e o teto de custo.

## Restrições permanentes

- A chave da OpenAI fica apenas no backend.
- Chamadas ocorrem somente por ação explícita do autor.
- A IA não altera o Markdown nesta parte.
- Testes automatizados não fazem chamadas cobradas.
- Conteúdo privado não aparece nos logs operacionais.
- O frontend não depende do SDK nem do protocolo do provedor.

## Persistência e fluxo aprovados

```text
Writing
└── Conversation (uma principal por escrita)
    ├── Message (autor ou assistente)
    ├── GenerationAttempt (cada chamada à IA)
    └── WritingMemory (memória dinâmica local)
```

- `Conversation` fornece identidade e continuidade à conversa.
- `Message` contém o conteúdo visível do autor ou do assistente.
- `GenerationAttempt` registra modelo, estado, tokens, custo, latência, erro
  seguro e identificador do provedor para cada chamada.
- `WritingMemory` contém preferências, decisões confirmadas e perguntas abertas
  daquela escrita.

Fluxo de envio:

1. Validar autenticação, tamanho do contexto e orçamento.
2. Persistir a mensagem do autor.
3. Criar uma tentativa em `pending`.
4. Montar o contexto segundo a hierarquia aprovada.
5. Iniciar a chamada e marcar a tentativa como `streaming`.
6. Transmitir e acumular os fragmentos da resposta.
7. Concluir a mensagem e registrar uso real.
8. Preservar conteúdo parcial como `interrupted` em caso de interrupção.
9. Atualizar a memória somente a partir de feedback explícito relevante.

Mensagem e tentativa são entidades separadas. Assim, uma nova tentativa pode
reutilizar a intenção do autor sem duplicar sua mensagem, enquanto cada chamada
potencialmente cobrada permanece individualmente auditável.

## Feedback e atualização de memória aprovados

Feedback de qualidade e instrução para memória são ações distintas:

- feedback como “gostei”, “não ajudou” ou uma reação avalia a qualidade da
  resposta, mas não cria uma regra editorial;
- uma instrução explícita como “lembrar nesta escrita”, “mantenha este tom” ou
  “não use esta expressão novamente” pode atualizar a memória local.

O sistema não transforma automaticamente comentários casuais em preferências
persistentes. Toda memória derivada deve permanecer vinculada à escrita e ter
procedência na mensagem que a originou.

## Interrupção e retry aprovados

- A resposta é apresentada progressivamente.
- Uma ação explícita de parar cancela a geração.
- Conteúdo já recebido permanece visível e marcado como `interrupted`.
- Uma falha de rede também preserva conteúdo parcial recuperável.
- Não há retry automático de geração, pois uma repetição pode criar outra
  cobrança.
- `Tentar novamente` é uma ação explícita do autor.
- A nova tentativa permanece ligada à mesma mensagem do autor.
- Cada tentativa registra separadamente modelo, tokens, custo e resultado.
- Somente respostas concluídas podem produzir atualizações de memória.

## Política inicial de custo aprovada

- O saldo disponível na conta do provedor não define o orçamento do produto.
- O desenvolvimento da Parte 1 possui teto interno de US$ 2.
- No máximo US$ 0,25 desse teto pode ser usado em validações manuais reais.
- Testes automatizados usam exclusivamente `FakeModelGateway` e custam zero.
- `gpt-5-mini` é o primeiro candidato editorial, sujeito às avaliações.
- Cada resposta começa com limite de até 800 tokens de saída, ou equivalente.
- Antes da chamada, o sistema reserva uma estimativa conservadora do custo.
- A chamada é bloqueada se a reserva ultrapassar o orçamento disponível.
- Depois da conclusão, a reserva é substituída pelo uso real informado pelo
  provedor.
- Estados de orçamento são `normal`, `near_limit` e `blocked`.
- O bloqueio de IA não afeta editor, histórico, leitura ou publicação.
- O teto de produção será decidido posteriormente com dados observados.
- Nenhuma chamada manual real será executada sem aviso explícito ao autor.

## Janela de conversa aprovada

O contexto de uma nova chamada contém a memória local persistida e os últimos
seis pares completos de mensagens da conversa, além do Markdown e das demais
camadas da hierarquia aprovada.

Respostas `interrupted` ou `failed` permanecem visíveis no histórico, mas não
entram automaticamente no contexto de uma nova chamada. A janela possui limite
adicional de entrada; seis pares não autorizam ultrapassar o orçamento total de
contexto.

## Política inicial de erros aprovada

Esta política pode ser refinada a partir dos primeiros testes, sem enfraquecer
as garantias de privacidade, custo e soberania:

- chave ausente: assistente indisponível sem afetar o editor;
- autenticação expirada: mensagem digitada preservada e novo login solicitado;
- Markdown grande demais: bloqueio antes da chamada;
- orçamento insuficiente: bloqueio antes da chamada;
- rate limit ou provedor indisponível: tentativa `failed` e retry manual;
- timeout: conteúdo parcial preservado como `interrupted`;
- resposta inválida: não concluir a mensagem nem atualizar a memória;
- falha ao persistir: não iniciar a chamada externa;
- erro interno: mensagem segura para o autor e logs técnicos sem conteúdo
  privado;
- nenhuma falha altera o Markdown.
