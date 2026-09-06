# Plano de estudo — Parte 2 do Crawl (sugestões estruturadas e revisão humana)

## Para que serve este documento

`ia/CONTEUDOS.md:227-273` lista os conteúdos exatos da Parte 2. Este plano não
repete a lista: ele transforma cada item em uma pergunta concreta que já existe
neste repositório, indica o que ler, propõe um exercício que produz artefato
verificável e fixa o teste de compreensão.

A regra de `ia/CONTEUDOS.md:9-15` continua valendo: um conteúdo só está aprendido
quando o autor explica com palavras próprias, liga a uma decisão do Entrelinhas,
reconhece uma falha típica, produz o exercício e revisa o teste correspondente.

O plano é enviesado de propósito para os modos de falha que este projeto vai
encontrar de verdade:

- recusa, truncamento no meio do JSON e saída válida-por-schema mas errada por
  semântica;
- por que o modelo não pode ser a fonte de verdade do diff;
- por que uma âncora textual instável corrompe o documento em silêncio.

Tempo total estimado: **19 a 25 horas**, distribuídas em oito tópicos.

## Ordem e dependências

```text
T1 Structured Outputs e o subconjunto real de JSON Schema
   │
   ├──► T2 Validação de fronteira e modos de falha da saída
   │        │
   │        └──► T3 Representação da mudança (texto, operações, patch)
   │                 │
   │                 ├──► T4 Diff calculado pela aplicação (difflib)
   │                 │
   │                 └──► T5 Optimistic concurrency (CAS + MVCC)
   │                          │
   │                          └──► T6 Idempotência de uma operação versionada
   │                                   │
   │                                   └──► T7 Human-in-the-loop e estados
   │
   └──────────────────────────────────────► T8 Avaliação editorial da Parte 2
```

Quais tópicos liberam quais fases de `ia/PARTE-2-PLANO-IMPLEMENTACAO.md`:

| Tópico | Libera |
| --- | --- |
| T3 (decisão do formato) | Fase 1 — dados e contrato |
| T1, T2, T3 | Fase 2 — geração estruturada |
| T5, T6, T7 | Fase 3 — revisão, aceite e conflito |
| T4, T7 | Fase 4 — frontend real |
| T8 | Fase 5 — avaliação |

T3 é o único tópico que precisa estar fechado **antes de qualquer código**,
porque a escolha de representação determina a tabela, o schema e a rota.

---

## T1 — Structured Outputs e o subconjunto de JSON Schema realmente aceito

**Tempo:** 3 h

### A pergunta real

Não é "o que é JSON Schema". É: *qual subconjunto de JSON Schema o modo estrito
da Responses API aceita, e o que acontece com as palavras-chave que ele ignora?*

O erro que custa caro é escrever um schema com `minLength`, `maxLength`,
`pattern` e `default`, achar que o provedor está garantindo esses limites e
descobrir em produção que ou o pedido é rejeitado com 400, ou as palavras-chave
foram simplesmente ignoradas — e a validação que o autor achava terceirizada
nunca existiu.

### Por que importa neste código

`backend/app/assistant/openai_gateway.py:46-54` monta hoje a chamada com
`model`, `instructions`, `input`, `max_output_tokens`, `store=False` e
`stream=True`. Nenhum campo de formato. Para a Parte 2 entra um `text.format` do
tipo `json_schema`, e esse é o único ponto do backend que conhece o vocabulário
do provedor — `backend/app/assistant/gateway.py:46-49` define o `Protocol` com
uma única capacidade e `openai_gateway.py:37` documenta que os tipos do SDK
param ali.

Consequência prática: se o schema for rejeitado pelo provedor, o erro chega como
`APIError` e vira `ai_unavailable` em `openai_gateway.py:26-33` — uma mensagem
genérica que esconde um bug de schema do desenvolvedor. Saber o subconjunto
aceito evita transformar erro de programação em "assistente indisponível".

### O que ler

1. [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
   — inteiro, com atenção às seções de *supported schemas* e *limitations*.
   Anotar literalmente: quais palavras-chave são suportadas, que
   `additionalProperties: false` é obrigatório em todo objeto, e que **todo
   campo declarado em `properties` precisa aparecer em `required`** (opcional se
   expressa com `anyOf` incluindo `null`, não omitindo do `required`).
2. [JSON Schema — getting started](https://json-schema.org/learn/getting-started-step-by-step)
   — apenas `type`, `properties`, `required`, `enum`, `additionalProperties`,
   `items`. Ignorar o resto: o resto não passa no modo estrito.
3. `backend/app/schemas.py:1-8` — o `ApiModel` do projeto converte snake_case
   Python para camelCase JSON. Decidir conscientemente se o schema **do
   provedor** segue essa convenção ou usa nomes em português, e por quê.

### Exercício

Escrever à mão, em um arquivo de rascunho, o schema da sugestão editorial do
Entrelinhas, com no máximo cinco campos, e ao lado de cada campo uma linha
dizendo o que ele impede que o modelo faça. Depois riscar todo campo que não
impede nada. O que sobrar é o schema da implementação.

### Você entendeu quando consegue responder

- Por que `minLength` não pertence ao schema enviado ao provedor, mas pertence
  ao modelo Pydantic da fronteira?
- O que o modo estrito garante exatamente (forma) e o que ele não garante
  (conteúdo)?
- Por que um campo opcional em modo estrito se escreve com `anyOf [tipo, null]`
  e não removendo o nome de `required`?

---

## T2 — Validação de fronteira e modos de falha da saída

**Tempo:** 3 h — o tópico mais importante do plano

### A pergunta real

*Quais são todas as formas de a saída chegar errada, e qual delas o schema não
cobre?*

Há quatro, em ordem crescente de perigo:

1. **Recusa** — o modelo devolve uma recusa em vez do objeto. O schema não é
   violado; simplesmente não há objeto.
2. **Truncamento** — a resposta bate no teto de tokens de saída e para no meio
   do JSON. O que chega é uma string sintaticamente inválida.
3. **Válido por schema, errado por semântica** — todos os campos presentes e
   tipados, mas o `trecho_alvo` não existe no documento, ou existe duas vezes, ou
   a "proposta" é idêntica ao original, ou a justificativa não descreve a
   mudança.
4. **Válido, coerente e falso** — o texto proposto introduz um fato, uma citação
   ou um número que não está no Markdown. Nenhuma validação de código detecta
   isso; é matéria de avaliação (T8) e de instrução editorial.

Os dois primeiros são problemas de protocolo, o terceiro é validação de
aplicação, o quarto é avaliação humana. Confundir as três camadas é o erro
clássico.

### Por que importa neste código

`backend/app/assistant/openai_gateway.py:69-83` trata `response.completed` e
`response.incomplete` **do mesmo jeito**: ambos fecham o stream emitindo o
`usage` final. Isso é correto para a Parte 1 (uma resposta em prosa truncada
ainda é útil e fica marcada), mas é insuficiente para a Parte 2: uma resposta
truncada é um JSON quebrado, e o backend precisa saber que a causa foi o teto de
tokens, não uma alucinação de formato. Sem essa distinção, o autor recebe "o
assistente devolveu uma resposta inválida" quando a ação correta seria aumentar
`ai_max_output_tokens` (`backend/app/config.py:41`, hoje 800).

`backend/app/assistant/service.py:226-227` já mostra o padrão de rigor esperado:
se o stream termina sem `usage`, o gateway erra explicitamente com
`provider_protocol_error`. A validação da saída estruturada tem que ter a mesma
disciplina.

E `backend/app/assistant/context.py:20-32` (`FIXED_RULES`) é o motivo pelo qual
a recusa é um caso real e não teórico: as regras fixas mandam o assistente dizer
que falta evidência em vez de inventar. Um pedido de alteração sobre um trecho
inexistente é exatamente o tipo de pedido que um modelo bem instruído recusa.

### O que ler

1. A seção *Refusals* do guia de Structured Outputs, e a estrutura do
   `refusal` content part na Responses API.
2. `backend/app/assistant/openai_gateway.py:42-87` inteiro, uma vez, perguntando
   a cada `elif`: "que evento eu perderia se este ramo não existisse?".
3. `backend/tests/unit/test_openai_gateway.py` — 11 KB de testes de sequência de
   eventos, incluindo protocolos inválidos. É o modelo do que os testes da Parte
   2 precisam provar.
4. Documentação de `json.JSONDecodeError` e de `pydantic.ValidationError`:
   entender que a primeira separa "não é JSON" de "é JSON mas não é o objeto".

### Exercício

Escrever uma tabela de seis linhas — as quatro falhas acima mais "tudo certo" e
"provedor indisponível" — com quatro colunas: *como o backend detecta*, *código
de erro devolvido*, *estado do `GenerationAttempt`*, *o que o autor vê*. A
tabela precisa mostrar que **nenhuma linha altera o Markdown**, que é a regra de
`ia/ROADMAP.md:17`.

### Você entendeu quando consegue responder

- Como distinguir, no código, truncamento de JSON malformado — e por que a
  distinção muda a ação do operador?
- Por que uma saída válida por schema com `trecho_alvo` inexistente é **erro de
  aplicação**, e não erro do provedor?
- Onde uma saída inválida deve deixar rastro para auditoria sem violar o
  contrato de privacidade provado em
  `backend/tests/contract/test_assistant_privacy.py:99-112`?

---

## T3 — Representação da mudança: texto completo, operações ou patch

**Tempo:** 3 h — decide a arquitetura, precisa fechar antes de código

### A pergunta real

*O que exatamente o modelo devolve quando propõe uma alteração?* Três famílias:

| Representação | O modelo devolve | Custo de saída | Falha característica |
| --- | --- | --- | --- |
| Texto final completo | o Markdown inteiro reescrito | proporcional ao documento | reescreve o que não foi pedido; impossível revisar |
| Operações com offsets | `{start, end, texto}` | mínimo | o modelo não conta caracteres; offset errado corrompe em silêncio |
| Patch / diff unificado | `@@ -12,7 +12,9 @@ ...` | médio | o modelo inventa o diff — proibido por `ia/ROADMAP.md:96-97` |
| Substituição ancorada | trecho literal + trecho proposto | proporcional ao trecho | âncora ausente ou ambígua — **detectável** |

A quarta linha não está no roadmap com esse nome, mas é a leitura correta de
"trecho-alvo e âncoras" em `ia/CONTEUDOS.md:236`.

### Por que importa neste código

Três restrições do repositório eliminam três das quatro opções sem discussão:

- **Texto completo está fora por orçamento.** `backend/app/config.py:41` fixa
  `ai_max_output_tokens = 800` e `backend/app/assistant/budget.py:67-73` precifica
  o pior caso com esse teto antes de qualquer chamada. Uma escrita de 20 mil
  caracteres não cabe em 800 tokens de saída. Aumentar o teto para caber o
  documento inteiro multiplicaria o custo de cada proposta pelo tamanho do texto.
- **Offsets estão fora por segurança.** `backend/app/writings/models.py:41`
  guarda o Markdown como `Text` livre; não há tokenização, não há parágrafos
  identificados, não há nada estável para indexar. Um offset errado de dois
  caracteres corta uma palavra ao meio e o `compare_and_swap` de
  `backend/app/writings/persistence.py:47-60` aplica sem reclamar — a versão
  corrompida vira histórico imutável em `writing_versions`.
- **Patch está fora por decisão explícita do produto.**
  `ia/ROADMAP.md:96-97` diz que o diff é calculado pela aplicação e não inventado
  como fonte de verdade pelo modelo. Aceitar um patch do modelo é exatamente
  fazer o contrário.

Sobra a substituição ancorada, e ela tem a propriedade que as outras não têm: a
falha é **verificável em uma linha de Python**. Se
`base_markdown.count(trecho_alvo) != 1`, a proposta é rejeitada antes de chegar
ao autor. Uma âncora ausente é um erro barato; um offset errado é corrupção
silenciosa.

### O que ler

1. `backend/app/writings/models.py:23-72` — as duas tabelas que definem o que é
   uma "versão do Markdown" e por que `writing_versions` é imutável.
2. `backend/app/writings/service.py:180-199` (`_apply_versioned_change`) — o
   único caminho pelo qual o Markdown muda hoje.
3. `ia/CONTEUDOS.md:234-241` — os itens 2 e 3 da lista oficial, relidos depois
   da tabela acima.
4. Qualquer descrição do formato de patch do `git apply` **apenas** para
   entender por que um patch precisa de contexto exato e falha de forma
   confusa quando o contexto não bate. Não implementar nada disso.

### Exercício

O exercício do currículo (`ia/CONTEUDOS.md:250`): pegar duas escritas reais e,
para cada uma, escrever à mão a mesma alteração nas três representações. Contar
os caracteres de cada uma. Depois, para cada representação, descrever a
corrupção específica que um erro de um caractere produz. O documento resultante
é a justificativa da decisão de arquitetura e entra em
`ia/PARTE-2-PLANO-IMPLEMENTACAO.md` como referência.

### Você entendeu quando consegue responder

- Por que "o modelo devolve o documento inteiro reescrito" é ao mesmo tempo a
  opção mais simples de implementar e a pior para o produto?
- Qual é a diferença entre uma âncora ambígua e uma âncora ausente, e por que as
  duas precisam de códigos distintos?
- Se o autor editar o Markdown entre a proposta e o aceite, o que acontece com a
  âncora — e por que isso já é resolvido pela versão-base, sem tocar na âncora?

---

## T4 — O diff é uma visualização, calculada pela aplicação

**Tempo:** 2 h

### A pergunta real

*Se o modelo devolve trecho-alvo e trecho-proposto, quem produz o realce
palavra a palavra que o autor vê, e com quê?*

E a pergunta subordinada, que é a lazy: *precisa de realce, ou dois blocos lado
a lado já resolvem?*

### Por que importa neste código

`frontend/src/features/suggestions/SuggestionDiff.tsx:2` já renderiza
`suggestion.before` dentro de `<del>` e `suggestion.after` dentro de `<ins>`, e
`suggestions.css:1` já estiliza os dois. Ou seja: **o produto já decidiu que a
visualização é bloco-contra-bloco**, e nesse desenho o backend não precisa
calcular diff nenhum — `before` é o trecho-alvo, `after` é o trecho proposto.

O realce palavra a palavra é uma melhoria de revisão, não um requisito. Se ele
for feito, a ferramenta certa é `difflib.SequenceMatcher` da biblioteca padrão,
sobre tokens separados por espaço:

```python
opcodes = difflib.SequenceMatcher(None, alvo.split(), proposto.split()).get_opcodes()
```

Por que `SequenceMatcher` e não os vizinhos do mesmo módulo:

- `difflib.unified_diff` e `difflib.ndiff` trabalham por **linha**. Em prosa,
  um parágrafo inteiro é uma linha só: o diff resultante diz "linha removida,
  linha adicionada" e não informa nada. Granularidade errada.
- `difflib.HtmlDiff` gera tabela HTML pronta — o backend não produz HTML e o
  frontend tem seu próprio CSS. Fora de escopo.

Por que nenhuma dependência nova: `diff-match-patch` e similares existem para
fazer *patching* tolerante a falhas, que é justamente o que este produto não
quer (o merge silencioso é proibido por `UX-CONTRACT.md:46`). Pagar uma
dependência para obter a capacidade que se decidiu não usar é o pior negócio
possível.

### O que ler

1. Documentação de `difflib.SequenceMatcher`, em especial `get_opcodes()` e a
   heurística de *autojunk* — que precisa ser desligada (`autojunk=False`) em
   textos com muitas repetições, senão o resultado fica estranho.
2. `frontend/src/features/suggestions/SuggestionDiff.tsx` e
   `suggestions.css` — para ver o que já existe antes de propor mais.

### Exercício

Escrever um script de 15 linhas que recebe dois parágrafos, imprime os opcodes e
depois imprime o texto com `[-removido-]` e `{+adicionado+}`. Rodar em dois
pares reais: um com troca de uma palavra, outro com reordenação de frases. Ver
com os próprios olhos que reordenação produz um diff péssimo — e concluir se o
produto quer aceitar sugestões de reordenação nesta parte.

### Você entendeu quando consegue responder

- Por que o diff nunca pode ser fonte de verdade da aplicação, mesmo quando é
  calculado pela aplicação?
- Qual é a granularidade certa para prosa, e por que a granularidade de linha
  falha aqui?
- O realce palavra a palavra é requisito da Parte 2 ou melhoria? (Resposta:
  melhoria — `ia/ROADMAP.md:96` exige apenas que o cálculo seja da aplicação.)

---

## T5 — Optimistic concurrency: o que um CAS garante de verdade

**Tempo:** 3 h

### A pergunta real

*Por que `UPDATE ... WHERE version_number = :esperada` é suficiente, e em que
condição ele deixaria de ser?*

### Por que importa neste código

O mecanismo já existe e é bom.
`backend/app/writings/persistence.py:47-60` faz um único `UPDATE ... WHERE id = :id
AND version_number = :esperada ... RETURNING`, e
`backend/app/writings/service.py:188-196` transforma zero linhas afetadas em
`AppError("writing_version_conflict", ..., 409, {"currentVersion": current})`.
`backend/tests/integration/test_writing_concurrency.py:32` (`test_simultaneous_saves_commit_exactly_one_new_version`)
já prova que dois salvamentos simultâneos produzem exatamente uma versão nova.

A Parte 2 **não pode reimplementar isso**. A pergunta de estudo é o inverso: o
que já está garantido, para não construir garantia duplicada?

O ponto conceitual: em `READ COMMITTED`, dois `UPDATE` concorrentes sobre a
mesma linha serializam-se pelo lock de linha; o segundo reavalia o predicado
depois que o primeiro commita, vê `version_number` já incrementado, não casa e
afeta zero linhas. É por isso que o CAS funciona **sem** `SELECT ... FOR UPDATE`
e sem nível de isolamento mais alto. Compare com
`backend/app/assistant/budget.py:107`, onde há um `pg_advisory_xact_lock`
explícito — ali é necessário porque a decisão depende de um **agregado** sobre
várias linhas (`SELECT sum(...)`), e agregado não tem linha para travar.

Reconhecer essa diferença — predicado sobre uma linha versus agregado sobre
muitas — é o conteúdo de "PostgreSQL explicit locking" citado em
`ia/CONTEUDOS.md:257`.

### O que ler

1. [PostgreSQL — Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
   e o capítulo *Transaction Isolation*, focando em: comportamento de `UPDATE`
   concorrente em `READ COMMITTED`, o que é *lost update* e por que o CAS o
   impede.
2. `backend/app/writings/persistence.py:47-67` e
   `backend/app/writings/service.py:180-199`, linha a linha.
3. `backend/tests/integration/test_writing_concurrency.py` inteiro — os quatro
   testes cobrem salvamento simultâneo, restauração que anexa versão, restauração
   com versão velha e versão inexistente.
4. `backend/app/assistant/budget.py:96-120`, para contrastar.

### Exercício

Com dois `psql` abertos no banco de desenvolvimento (porta 5452 deste worktree),
reproduzir à mão a corrida: `BEGIN` nos dois, `UPDATE writings SET markdown = ...,
version_number = version_number + 1 WHERE id = ... AND version_number = 3` nos
dois, commitar o primeiro, observar o segundo devolver `UPDATE 0`. Escrever em
três linhas o que aconteceria se o predicado fosse só `WHERE id = ...`.

### Você entendeu quando consegue responder

- Por que a sugestão precisa fixar a versão-base **na criação** e não só no
  aceite?
- Por que o aceite não precisa de `SELECT ... FOR UPDATE` sobre `writings`?
- Por que uma restauração de versão (`writings/service.py:155-168`) **não**
  devolve o documento a um estado anterior do ponto de vista do CAS, e o que
  isso significa para uma sugestão pendente?

---

## T6 — Idempotência de uma operação que cria versão

**Tempo:** 2 h

### A pergunta real

*Duplo clique em "Aceitar alteração" pode criar duas versões?* E a versão
adulta da pergunta: *idempotência e CAS resolvem o mesmo problema ou problemas
diferentes?*

Resolvem problemas diferentes e os dois são necessários:

- **CAS** protege contra *dois autores* (ou duas abas) editando o mesmo
  documento a partir de estados distintos. Resultado correto: 409.
- **Idempotência** protege contra *a mesma intenção* chegando duas vezes por
  retry de rede ou duplo clique. Resultado correto: a mesma resposta da primeira
  vez, sem novo efeito.

Se só houvesse CAS, o duplo clique daria 409 — tecnicamente seguro, mas mentindo
para o autor, que veria "conflito" onde não houve conflito nenhum.

### Por que importa neste código

`backend/app/idempotency/service.py:34-74` já implementa `execute_idempotent`
com chave `(author_id, operation, key)` (unicidade em
`backend/app/idempotency/models.py:31-34`), hash canônico do pedido, resposta
armazenada e janela de 24 h (`service.py:19`). O contrato crítico está no
docstring de `service.py:43-48`: **a ação não pode commitar por conta própria**,
porque o registro da chave é commitado na mesma transação; quem perde a corrida
faz rollback do trabalho duplicado e recebe a resposta do vencedor.

Isso colide com `backend/app/writings/service.py:198`, onde
`_apply_versioned_change` commita internamente. Entender essa colisão é o ponto
do tópico: o aceite de sugestão precisa do CAS **dentro** da ação idempotente,
logo `_apply_versioned_change` não pode mais commitar sozinho.

`backend/app/assistant/service.py:416-468` mostra o padrão já usado para uma
operação cara: envolver a persistência da intenção em `execute_idempotent` e, em
`service.py:496-513`, detectar que a tentativa devolvida já saiu de `pending`
para nunca pagar duas vezes pela mesma chamada.

### O que ler

1. `backend/app/idempotency/service.py` inteiro — 108 linhas, vale ler todas.
2. `backend/app/writings/service.py:31-66` (criação com chave opcional) e
   `180-199` (mudança versionada que commita).
3. `backend/app/assistant/service.py:416-483` e `486-514`.
4. `backend/tests/unit/test_idempotency.py` e as partes de
   `test_assistant_conversation.py` sobre repetição de chave
   (`test_repeating_an_idempotency_key_does_not_call_the_gateway_twice`).

### Exercício

Desenhar, em uma folha, a sequência completa de duas requisições de aceite
simultâneas com a **mesma** `Idempotency-Key`, marcando: quem pega o lock da
linha da chave, quem executa o CAS, quem faz rollback, o que cada uma devolve, e
quantas linhas existem em `writing_versions` no final. Depois refazer o desenho
com chaves **diferentes** e verificar que o resultado correto muda de "resposta
repetida" para "409 conflito".

### Você entendeu quando consegue responder

- Por que `execute_idempotent` exige que a ação não commite?
- Qual é o resultado esperado de duplo clique com a mesma chave, e com chaves
  diferentes — e por que os dois estão certos?
- Por que a resposta armazenada precisa incluir a versão criada, e não só o id
  da sugestão?

---

## T7 — Human-in-the-loop: estados de uma sugestão e reversibilidade

**Tempo:** 2,5 h

### A pergunta real

*Quais estados de uma sugestão são fatos guardados e quais são conclusões
calculadas?* Guardar um estado que pode ser derivado obriga a manter um
processo que o atualiza — e processo que atualiza estado é processo que
esquece de atualizar.

`ia/CONTEUDOS.md:238` lista `pending`, `accepted`, `rejected`, `superseded` e
`conflict`. Duas dessas cinco merecem interrogação:

- **`superseded`** é derivável: uma sugestão pendente está obsoleta exatamente
  quando `sugestao.versao_base < writing.version_number`. Guardar exigiria varrer
  as sugestões pendentes a cada salvamento do documento.
- **`conflict`** não é estado da sugestão, é resultado de uma tentativa de
  aceite. A mesma sugestão pode ser tentada duas vezes; o "conflito" pertence à
  tentativa, não ao objeto.

E falta um estado que o roadmap exige e a lista não tem: `ia/ROADMAP.md:98` pede
"pedir ajuste". Pedir ajuste produz uma sugestão nova; a antiga precisa de um
destino que não seja `rejected` (o autor não rejeitou a ideia, pediu outra
versão dela).

### Por que importa neste código

`frontend/src/features/suggestions/SuggestionProvider.tsx:5` já declara
`'pending' | 'applying' | 'accepted' | 'rejected' | 'conflict'` como estado de
**componente**, e `SuggestionProvider.tsx:10` decide conflito comparando
`error.message === 'conflict'` — uma string inventada pelo mock. O backend real
devolve `ApiError` com `.code` (`frontend/src/services/httpApi.ts:4-18`), e o
código é `writing_version_conflict`
(`backend/app/writings/service.py:192`). O componente está errado contra o
envelope real, e vai continuar errado até alguém separar "estado da UI" de
"estado persistido".

`frontend/src/services/contracts.ts:3` declara apenas
`'pending' | 'accepted' | 'rejected'` — três estados para uma máquina que precisa
de mais.

`UX-CONTRACT.md:41` fixa o comportamento esperado do aceite: pendente = ações do
diff bloqueadas; sucesso = nova versão visível; falha = recarregar versão
canônica. E `UX-CONTRACT.md:46` fixa a regra que nenhuma implementação pode
violar: **nunca fazer merge silencioso**.

### O que ler

1. `frontend/src/features/suggestions/` inteiro — são sete arquivos minúsculos,
   ler todos leva dez minutos e evita reconstruir o que existe.
2. `UX-CONTRACT.md:36-48` (ledger de comportamento).
3. `backend/app/assistant/models.py:23-27` — como este projeto declara conjuntos
   de estados: tuplas em Python, `CheckConstraint` no banco
   (`models.py:52-60`) e `Literal` no schema (`app/assistant/schemas.py:11-14`).
   Três lugares, sempre em sincronia.

### Exercício

Desenhar a máquina de estados como grafo: nós, arestas rotuladas com a ação, e
para cada aresta uma linha dizendo o que muda no banco. Marcar em cor diferente
todo nó que é **derivado** e toda aresta que é **erro** e não transição. O
desenho tem que responder sem ambiguidade: o que acontece com a sugestão A
quando o autor pede ajuste e nasce a sugestão B?

### Você entendeu quando consegue responder

- Qual é a diferença entre "obsoleta" (o documento andou) e "rejeitada" (o autor
  não quis)?
- Por que "conflito" não é um estado guardado?
- Pedir ajuste rejeita a sugestão anterior ou não? (Recomendação registrada em
  `ia/PARTE-2-PLANO-IMPLEMENTACAO.md`: não rejeita — a anterior vira `replaced`
  e o vínculo `parent_suggestion_id` preserva a genealogia auditável.)

---

## T8 — Avaliação: fidelidade, preservação de voz e ausência de fatos inventados

**Tempo:** 2,5 h (mais o tempo da rodada real, que é orçamento e não estudo)

### A pergunta real

*A rubrica da Parte 1 serve para julgar uma sugestão, ou uma sugestão exige
dimensões que uma resposta em prosa não exige?*

Exige. Uma resposta em prosa é lida e descartada; uma sugestão vira texto
canônico do autor se aceita. Três dimensões novas aparecem:

1. **Ancoragem** — o `trecho_alvo` é de fato o trecho de que o autor falou? Uma
   sugestão que altera o parágrafo errado pode ser tecnicamente boa e ainda
   assim inaceitável.
2. **Escopo** — a proposta muda só o que precisava mudar? Uma sugestão que
   aproveita a viagem para "melhorar" outras três frases viola o limite de
   reorganização de `backend/app/assistant/editorial.md:32-35`.
3. **Reversibilidade honesta** — a `justificativa` descreve a mudança que a
   proposta faz de verdade? Um resumo que promete uma coisa e um trecho que faz
   outra é a falha mais difícil de pegar em revisão rápida, porque o autor lê o
   resumo e clica.

As cinco dimensões da Parte 1 continuam (`ia/evals/parte-1-rubrica.md`), com uma
mudança de peso: **preservação de voz deixa de ser uma dimensão entre cinco e
passa a ser eliminatória**, junto com fidelidade. Uma sugestão que higieniza o
estilo do autor e é aceita destrói o ativo que o produto existe para proteger.

### Por que importa neste código

`ia/evals/parte-1-rubrica.md` já define o formato: cinco dimensões de 1 a 4,
gate de média mínima 3 por dimensão mais nenhum caso com fidelidade abaixo de 3,
tabela de registro da configuração avaliada (modelo, `instruction-version`,
política de contexto), e a regra de que igualdade textual não é critério.
`ia/evals/parte-1-casos.json` define o formato dos casos: `id`, `markdown`,
`question`, `required_facts`, `forbidden_claims`, `notes`.

A Parte 2 precisa de campos a mais no caso — a versão-base e o trecho que uma
sugestão correta deveria ancorar — mas **a forma do arquivo não deve mudar**,
para que as duas suítes sejam lidas do mesmo jeito.

O caso `injecao-de-instrucao-no-markdown` de `ia/evals/parte-1-casos.json` fica
mais perigoso na Parte 2: na Parte 1 obedecer à injeção produzia uma resposta
ruim; na Parte 2 produziria uma **proposta de alteração** do documento inteiro,
a um clique de virar versão canônica. Esse caso precisa ser refeito no modo
proposta.

### O que ler

1. `ia/evals/parte-1-rubrica.md` inteiro, de novo, agora perguntando "qual
   dessas dimensões muda de peso quando a saída é aplicável?".
2. `ia/evals/parte-1-casos.json` — os cinco casos, em especial
   `preservacao-de-voz-seneca-paragrafo-final` (que já é quase um caso de
   sugestão) e `injecao-de-instrucao-no-markdown`.
3. [Evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices).
4. `backend/app/assistant/editorial.md` inteiro — a linha editorial é metade da
   configuração avaliada.

### Exercício

O exercício do currículo (`ia/CONTEUDOS.md:253`): montar dez exemplos de
sugestões — boas, ruins e ambíguas — sobre Markdown real do autor, **antes** de
qualquer chamada ao modelo, escrevendo as sugestões à mão. Pontuar as dez com a
rubrica. Se duas sugestões manifestamente diferentes recebem a mesma nota, a
rubrica está grossa demais e precisa de mais um nível ou de outra dimensão.

Produto do exercício: `ia/evals/parte-2-casos.json` e
`ia/evals/parte-2-rubrica.md`.

### Você entendeu quando consegue responder

- Por que "fato inventado" numa sugestão é pior do que numa resposta?
- Por que preservação de voz vira eliminatória na Parte 2?
- Como pontuar uma sugestão que melhora o texto mas ancora no parágrafo errado?
- Por que a suíte da Parte 2 não pode ser pontuada por outro modelo nesta fase?
  (LLM-as-judge está adiado — `ia/CONTEUDOS.md:212`.)

---

## O que este plano deliberadamente não estuda

Alinhado com `ia/CONTEUDOS.md:271` e com o roadmap:

- **tool calling e function calling** — a sugestão é uma saída estruturada, não
  uma ferramenta que o modelo invoca;
- **agente autônomo e aplicação automática** — contraria `ia/ROADMAP.md:17`;
- **leitura de links** — Parte 3 (`ia/ROADMAP.md:116-138`);
- **áudio e transcrição** — Walk (`ia/CONTEUDOS.md:363-403`);
- **embeddings, RAG e banco vetorial** — nada na Parte 2 recupera trecho por
  similaridade; a âncora é literal;
- **LLM-as-judge automático** — Parte 4 ou depois;
- **múltiplos provedores** — `ia/ROADMAP.md:26-27` proíbe antecipar.

## Cronograma sugerido

| Bloco | Tópicos | Tempo | Entregável |
| --- | --- | --- | --- |
| 1 | T3 | 3 h | decisão de representação escrita e justificada |
| 2 | T1 + T2 | 6 h | schema em rascunho + tabela de seis modos de falha |
| 3 | T5 + T6 | 5 h | desenho das duas corridas (CAS e idempotência) |
| 4 | T7 | 2,5 h | grafo da máquina de estados |
| 5 | T4 | 2 h | script de opcodes rodado em dois pares reais |
| 6 | T8 | 2,5 h | `parte-2-casos.json` e `parte-2-rubrica.md` |

Blocos 1 a 3 são pré-requisito de código. Blocos 4 e 5 podem correr em paralelo
com a Fase 1 da implementação. O bloco 6 fecha a parte.
