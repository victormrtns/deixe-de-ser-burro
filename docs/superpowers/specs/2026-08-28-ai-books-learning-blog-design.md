# Blog de Aprendizados com IA — Especificação do Produto

## Visão

Aplicação web pessoal para transformar anotações manuscritas sobre livros em artigos estruturados. O autor trabalha em um ciclo contínuo de áudios curtos, prompts de texto, links e edição manual. A IA transcreve, organiza, complementa e propõe mudanças, mas nunca altera o documento sem aprovação.

O produto possui uma área privada de autoria e uma área pública de leitura. Há um único autor; leitores não precisam de cadastro.

## Objetivo do MVP

Validar o fluxo completo em que o autor:

1. cadastra um livro;
2. cria uma ou mais escritas dentro dele;
3. intercala áudios de três a cinco minutos, prompts e edição manual;
4. revisa e aprova sugestões da IA;
5. fecha e retoma o rascunho sem perder contexto;
6. publica uma versão final para leitura pública.

## Escopo funcional

### Biblioteca e livros

A biblioteca comporta vários livros. Cada livro possui metadados básicos, capa opcional e várias escritas independentes. Uma escrita pode cobrir páginas, seções, um capítulo ou vários capítulos do livro.

No MVP, toda escrita pertence a exatamente um livro. Artigos livres ou que reúnam vários livros ficam fora do escopo inicial.

### Escritas e artigos

Uma escrita é a unidade privada de trabalho. Quando publicada, passa a ser apresentada como artigo. Cada escrita possui isoladamente:

- conteúdo Markdown e versões;
- conversas e mensagens;
- áudios e transcrições;
- links e resumos de referência;
- sugestões pendentes, aprovadas e rejeitadas;
- informações da publicação.

Publicar ou limpar uma escrita não afeta nenhuma outra escrita do mesmo livro.

### Editor

Markdown é o formato canônico. O editor oferece salvamento automático, histórico recuperável e preview com:

- Markdown;
- diagramas Mermaid;
- blocos de código;
- fórmulas LaTeX embutidas.

O autor pode alternar entre edição, preview e visualização lado a lado. Edições manuais e sugestões aprovadas criam versões recuperáveis.

### Loop de autoria assistida

O fluxo central de uma escrita é:

```text
Abrir rascunho
   ↓
Enviar áudio, prompt de texto ou link
   ↓
Transcrever, responder ou pesquisar
   ↓
Propor alteração no Markdown
   ↓
Comparar e aprovar, rejeitar ou pedir ajuste
   ↓
Continuar com outro áudio, prompt ou edição manual
```

As modalidades podem ser intercaladas livremente. O estado completo do rascunho permanece disponível entre sessões.

### Áudio e transcrição

O autor pode gravar no navegador ou enviar um arquivo de áudio. O uso esperado é inferior a cinco horas mensais, geralmente em clipes de três a cinco minutos.

Cada áudio passa pelos estados de envio, transcrição, análise, sugestão pronta ou erro. O original é preservado durante o rascunho. Falhas permitem nova tentativa sem perder o arquivo.

### Chat contextual

Cada escrita possui um chat principal. O contexto padrão inclui:

- Markdown atual;
- transcrições da escrita;
- referências vinculadas à conversa;
- mensagens recentes;
- resumo acumulado da conversa.

O histórico inteiro não deve ser reenviado a cada chamada. Conversas longas usam mensagens recentes e um resumo acumulado para controlar tokens.

Chats auxiliares são opcionais e de prioridade P1. Se implementados, terão contexto independente e somente gerarão custo quando usados.

### Links e conteúdo externo

Um link enviado no chat pode ser processado temporariamente. O sistema salva na própria conversa o título, a URL e um pequeno resumo; não cria grafo de conhecimento e não compartilha a referência automaticamente com outros chats.

A IA pode complementar as anotações com conhecimento externo. Citações e links são desejáveis, mas não obrigatórios. Complementos externos devem ser identificados como tal antes da aprovação.

### Sugestões e aprovação

A IA nunca modifica diretamente o Markdown. Cada proposta apresenta:

- comparação entre o texto atual e a alteração;
- trechos removidos e acrescentados;
- breve explicação da reorganização;
- ações para aceitar, rejeitar ou pedir ajuste.

Aceitar cria uma nova versão. Rejeitar preserva o documento. Pedir ajuste continua a conversa sem aplicar a proposta anterior. Reaplicar a mesma sugestão não pode criar alterações duplicadas.

### Publicação e retenção

Publicar cria uma versão pública congelada, separada do rascunho. A área pública nunca expõe chats, prompts, áudios, transcrições ou sugestões.

Depois da publicação, inicia-se um período de segurança de três dias. Durante esse prazo, o autor pode cancelar a limpeza ou voltar a escrita para rascunho. Encerrado o prazo, são excluídos:

- arquivos de áudio;
- chats e mensagens;
- transcrições auxiliares;
- referências e contexto de trabalho;
- sugestões de alteração.

Permanecem o livro, os metadados da escrita, o Markdown final e a versão publicada. A exclusão economiza principalmente armazenamento e reduz a exposição de material privado; não recupera custos de IA já incorridos.

## Experiência principal

A tela da escrita possui três regiões:

1. navegação e contexto do livro, da escrita e das conversas;
2. editor Markdown e preview;
3. assistente com chat, gravação, links e histórico.

As tarefas de áudio e IA exibem progresso e erros. Uma operação lenta não bloqueia edição manual. Sugestões são apresentadas em uma comparação explícita antes de qualquer alteração.

## Arquitetura

### Estratégia

O sistema será um monólito modular, executado localmente e posteriormente implantado em uma VPS simples.

```text
React
  ↓
FastAPI
  ├── PostgreSQL
  ├── armazenamento de arquivos
  └── APIs de IA
```

Docker Compose executará frontend, backend e banco. Os módulos internos serão:

- biblioteca;
- escritas;
- fontes e áudio;
- assistente;
- revisões;
- publicação;
- uso e custos.

As integrações de IA e armazenamento serão acessadas por interfaces internas substituíveis. Arquivos começam no disco da aplicação e podem migrar para armazenamento compatível com S3. Redis e Celery só serão introduzidos quando o volume justificar.

### Trabalhos assíncronos

Uploads, transcrições e gerações são representados por trabalhos persistidos no PostgreSQL. Um reinício da VPS não deve perder o trabalho nem aplicar a mesma alteração duas vezes. O processador retoma tarefas pendentes e registra tentativas e erros.

### Modelo conceitual

```text
Biblioteca
└── Livro
    └── Escrita / Artigo
        ├── versões Markdown
        ├── conversas
        │   ├── mensagens
        │   └── referências de links
        ├── áudios
        │   └── transcrições
        ├── sugestões
        ├── trabalhos assíncronos
        └── publicação
```

## Custos e limites

O teto operacional desejado é de R$ 50–70 por mês, incluindo VPS e IA. O sistema registra uso por escrita, operação e modelo, mostra estimativa mensal e permite configurar um limite.

Ao atingir o limite, tarefas de IA são bloqueadas, mas edição manual, leitura e publicação continuam disponíveis. Operações cotidianas usam um modelo econômico; revisões profundas podem usar um modelo superior somente por escolha explícita.

O orçamento considera até cinco horas de áudio por mês. O provedor e os modelos permanecem configuráveis para evitar acoplamento a preços específicos.

## Segurança e privacidade

- A área de autoria exige autenticação e suporta um único autor no MVP.
- Chaves de IA existem somente no backend.
- Uploads possuem limites de tipo e tamanho.
- URLs externas são validadas contra acesso a endereços internos e metadados da VPS.
- O Markdown público é sanitizado contra scripts e conteúdo ativo perigoso.
- Rotas públicas nunca retornam entidades privadas ou seus identificadores internos desnecessários.
- A limpeza pós-publicação é registrada e só ocorre após o prazo de segurança.

## Tratamento de falhas

- Falhas de upload preservam o estado do rascunho e permitem nova tentativa.
- Falhas de transcrição preservam o áudio original.
- Falhas de geração não alteram o Markdown.
- Trabalhos possuem proteção contra execução duplicada.
- Sugestões aprovadas possuem identificador idempotente.
- Reiniciar containers não perde trabalhos persistidos.
- O autor pode restaurar versões anteriores do Markdown.

## Backlog priorizado

### P0 — obrigatório para validar o MVP

1. **Infraestrutura local**
   - React, FastAPI, PostgreSQL e Docker Compose.
   - Migrações, configuração segura, logs e health checks.

2. **Biblioteca**
   - Criar, editar, listar e excluir livros.
   - Metadados básicos e capa opcional.
   - Criar várias escritas por livro.

3. **Editor Markdown**
   - Salvamento automático.
   - Preview de Markdown, Mermaid, código e fórmulas.
   - Histórico e restauração de versões.
   - Referência a capítulos, páginas ou seções cobertos.

4. **Chat principal**
   - Uma conversa principal por escrita.
   - Prompts contextuais e respostas em streaming.
   - Resumo de conversas longas.

5. **Áudio**
   - Gravação e upload.
   - Vários clipes intercalados com prompts.
   - Transcrição, estados de processamento e novas tentativas.

6. **Sugestões revisáveis**
   - Proposta estruturada de alteração.
   - Comparação antes/depois.
   - Aceitar, rejeitar e pedir ajuste.
   - Versionamento após aprovação.

7. **Autenticação e privacidade**
   - Área privada para o único autor.
   - Separação rigorosa entre dados privados e públicos.

8. **Publicação**
   - Versão pública congelada.
   - Página de leitura sem login.
   - Retorno a rascunho durante três dias.
   - Limpeza automática após o prazo.

9. **Controle de custo**
   - Uso por tarefa e estimativa mensal.
   - Limite configurável.
   - Escolha explícita para operações de maior qualidade e custo.

### P1 — após estabilidade do núcleo

- Referências de links com título, URL e resumo.
- Chats auxiliares.
- Exportação do Markdown.
- Busca na biblioteca.
- Upload de capas e refinamento da apresentação pública.

### Fora do MVP

- Vários autores.
- Aplicativo móvel nativo.
- Modo offline.
- Grafo de conhecimento entre conversas.
- Colaboração e comentários públicos.
- LaTeX como formato completo de documento.
- Redis, Celery e armazenamento S3.

## Critério de validação do MVP

O MVP está validado quando o autor consegue criar um livro e uma escrita, intercalar áudio e texto, revisar alterações, retomar o rascunho em outra sessão e publicar o resultado sem editar arquivos fora da aplicação.

## Estratégia de testes

- Testes unitários para versionamento, sugestões, publicação, retenção e limites de custo.
- Testes de integração para banco, processador de trabalhos e adaptadores de IA simulados.
- Testes ponta a ponta do fluxo de criação até publicação.
- Testes de recuperação após reinício dos containers.
- Testes de renderização e sanitização de Markdown, Mermaid e fórmulas.
- Testes de restauração de versões e cancelamento da limpeza.
- Testes de autorização garantindo que dados privados não apareçam em rotas públicas.

## Padrões de engenharia posteriores

Padrões detalhados de código, testes, QA e gates automatizados serão definidos pelo autor em uma especificação de engenharia própria antes da implementação. Essa separação permite transformar requisitos como lint, tipagem, cobertura, análise estática, testes de contrato e critérios de aceite em gates verificáveis sem misturá-los às decisões de produto deste documento.
