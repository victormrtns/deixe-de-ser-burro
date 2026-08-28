# Landing pública e conversa multimodal — Especificação de design

## Contexto

O frontend atual valida a fundação visual e os principais fluxos privados, mas a rota pública inicial ainda funciona como uma listagem mínima. A próxima entrega transforma essa rota em uma entrada editorial completa para artigos publicados e corrige a separação visual indevida entre chat e áudio no workspace.

Este documento complementa a especificação principal em `docs/superpowers/specs/2026-08-28-ai-books-learning-blog-design.md`. Permanecem válidos o sistema visual de `DESIGN.md`, o comportamento de `UX-CONTRACT.md` e a separação rigorosa entre material privado e publicação.

## Objetivos

1. Criar uma landing pública editorial que ajude qualquer leitor, sem autenticação, a descobrir artigos e navegar pelos livros que já originaram publicações.
2. Preservar o caráter autoral do Entrelinhas sem apresentar o produto como SaaS, ferramenta de IA, dashboard ou feed de notícias.
3. Unificar texto, áudio e links no mesmo fluxo cronológico de conversa da escrita.
4. Preparar contratos de frontend claros para a futura implementação P0 do backend.

## Fora de escopo

- Newsletter, cadastro de leitores, comentários ou perfis públicos.
- Exposição pública de livros sem artigo publicado.
- Progresso privado de leitura, rascunhos, conversas, áudios ou transcrições.
- Busca sem suporte do backend; o controle poderá aparecer somente quando houver contrato funcional.
- Edições temáticas e curadoria por coleções, que permanecem uma evolução futura.
- Chats auxiliares ou conhecimento compartilhado entre escritas.

## Direção editorial aprovada

A landing segue a direção **Estante em movimento**. A página combina um artigo principal escolhido pelo autor, artigos recentes, livros com publicações e um arquivo navegável. A experiência deve parecer uma pequena publicação independente: forte hierarquia tipográfica, imagens editoriais derivadas do universo de livros e marginalia, superfícies claras e navegação discreta.

O artigo principal é selecionado manualmente. Quando não houver uma seleção válida, o artigo publicado mais recente ocupa o destaque. A escolha editorial nunca altera datas, ordem do arquivo ou estado de publicação.

## Arquitetura da landing

### Cabeçalho público

O cabeçalho contém a marca Entrelinhas e somente destinos que existem e funcionam:

- `Artigos`, apontando para o arquivo público;
- `Livros`, apontando para a estante publicada;
- `Sobre`, com uma explicação curta da publicação;
- busca apenas quando o contrato de busca pública estiver implementado.

Não há ação de login em destaque, chamada comercial, métricas, orçamento ou menção à IA. O acesso do autor pode permanecer em uma rota conhecida sem ocupar a hierarquia pública.

### Artigo em destaque

O primeiro módulo apresenta:

- tipo editorial, como `Ensaio em destaque`;
- título, resumo e tempo estimado de leitura;
- livro e autor que originaram a escrita;
- data de publicação;
- imagem editorial ou capa derivada de página, sublinhado, dobra ou anotação;
- ação `Ler ensaio`.

O módulo aceita ausência de imagem sem produzir espaço quebrado. A alternativa usa composição tipográfica e marginalia, nunca um placeholder genérico.

### Artigos recentes

A página mostra até cinco artigos recentes, excluindo duplicação visual do destaque quando isso empobrecer a variedade. Cada entrada apresenta título, resumo curto, livro de origem, tempo de leitura e data. Imagens são opcionais; a hierarquia textual continua funcional sem elas.

### Estante publicada

Um livro aparece publicamente somente quando possui pelo menos um artigo publicado. O estado privado de leitura jamais participa desse critério.

Cada card de livro apresenta:

- capa ou composição editorial equivalente;
- título e autor;
- quantidade de artigos publicados;
- título do artigo publicado mais recente;
- até três temas derivados exclusivamente dos artigos públicos;
- ação `Explorar artigos`.

O rótulo opcional `Novos artigos` depende de publicação recente e não de atividade privada. A seção se chama `Estante publicada` ou `Artigos por livro`; não usa `Livros em leitura`.

Em telas largas, a estante usa uma grade editorial com capas de proporção estável. Em telas estreitas, os cards formam uma lista vertical completa; nenhuma informação ou ação fica disponível somente por hover.

### Arquivo

O arquivo apresenta todos os artigos publicados em ordem decrescente de publicação. O MVP pode renderizar a coleção completa quando pequena. Antes de uma coleção grande, o backend deve definir paginação ou cursor; a landing não inventará paginação apenas no cliente.

Cada entrada mantém título, livro, data e tempo de leitura. O arquivo oferece navegação para o artigo e para a página pública do livro.

### Sobre

Uma faixa curta explica que Entrelinhas é uma publicação independente de ensaios nascidos de livros, notas e estudo. O texto não promete frequência, comunidade ou recursos ainda inexistentes.

## Rotas públicas

- `/` — landing editorial.
- `/artigos` — arquivo completo de artigos publicados.
- `/artigos/:slug` — leitura congelada do artigo.
- `/livros` — todos os livros com pelo menos um artigo publicado.
- `/livros/:slug` — metadados públicos do livro e seus artigos publicados.
- `/sobre` — apresentação curta da publicação.

Rotas públicas consomem somente contratos públicos. Identificadores internos, estados de rascunho e entidades privadas não entram nas respostas nem no bundle público.

## Estados da landing

### Carregando

Reservar a geometria dos módulos com indicadores estáveis. Não usar uma grade de skeletons genérica que simule conteúdo inexistente.

### Sem publicações

A landing apresenta a identidade e uma mensagem honesta de que os primeiros ensaios ainda estão sendo preparados. Não mostra estante, arquivo vazio ou controles sem função.

### Erro total

Preservar cabeçalho e identidade, explicar que os textos não puderam ser carregados e oferecer `Tentar novamente`. Não substituir toda a página por um erro técnico.

### Erro parcial

Se destaque ou estante falhar separadamente, manter os módulos públicos válidos e apresentar recuperação localizada. Um erro de imagem nunca impede acesso ao artigo.

## Contratos públicos de dados

O frontend precisa de projeções públicas, separadas dos tipos privados:

```ts
interface PublicArticleSummary {
  slug: string
  title: string
  excerpt: string
  publishedAt: string
  readingMinutes: number
  coverImageUrl?: string
  sourceBook: {
    slug: string
    title: string
    author: string
  }
}

interface PublicBookSummary {
  slug: string
  title: string
  author: string
  coverImageUrl?: string
  publishedArticleCount: number
  latestArticle: Pick<PublicArticleSummary, 'slug' | 'title' | 'publishedAt'>
  publicTopics: string[]
}

interface PublicLanding {
  featuredArticle: PublicArticleSummary | null
  recentArticles: PublicArticleSummary[]
  publishedBooks: PublicBookSummary[]
}
```

O backend é responsável por filtrar publicação, escolher o fallback do destaque, calcular contagens e impedir que temas ou metadados privados apareçam nessas projeções.

## Conversa multimodal unificada

### Princípio

Cada escrita possui um chat principal. Texto, áudio e links são formas diferentes de criar uma mensagem nessa mesma conversa, não módulos independentes do workspace.

### Compositor

O rodapé do chat contém:

- campo de texto principal;
- ação de anexar link;
- ação de gravar ou enviar áudio;
- ação `Enviar`;
- estado de geração com `Parar geração`.

Áudio e link abrem estados de composição vinculados ao mesmo compositor. Eles não criam cabeçalhos, cartões promocionais ou painéis paralelos competindo com a conversa.

### Linha do tempo

As mensagens aparecem em ordem de criação e discriminam seu tipo:

- prompt de texto;
- link com título, domínio e resumo quando disponível;
- áudio com duração, estado de upload e reprodução local quando permitida;
- transcrição associada ao áudio;
- resposta da IA;
- sugestão de alteração vinculada à resposta que a originou.

O áudio mantém uma identidade visual própria dentro da mensagem, mas pertence à mesma lista, ao mesmo scroll e ao mesmo contexto. A transcrição pode ser expandida sem retirar o leitor da conversa.

## Direção aprovada do workspace: Documento soberano

Cada escrita é um ambiente isolado. O documento Markdown em desenvolvimento é o artefato principal e ocupa aproximadamente 60–65% da largura útil em desktop quando o assistente está aberto. Biblioteca e assistente são ferramentas contextuais recolhíveis; o documento continua completamente utilizável quando ambas estão fechadas.

### Contexto esquerdo

O trilho esquerdo se restringe ao livro ativo e contém somente:

- título e autor do livro;
- escritas pertencentes ao livro;
- acesso às versões da escrita atual;
- estado de publicação;
- retorno à biblioteca.

Não há navegação de dashboard, métricas ou destinos globais competindo com a escrita. Trocar de escrita troca integralmente documento, conversa, áudios, referências, sugestões e versões.

### Documento central

O documento mantém título, fonte, autor, metadados discretos, salvamento, versões e modos `Editar`, `Visualizar` e `Dividir`. Um controle de foco recolhe as superfícies laterais sem alterar o conteúdo ou perder o estado do editor.

A marginalia continua vinculando eventos ao processo de escrita, mas não reduz a legibilidade nem se torna requisito para acessar a conversa. O documento permanece editável durante upload, transcrição, streaming e revisão de sugestões.

### Assistente direito

O trilho direito contém a única conversa da escrita e pode ser recolhido. Texto, link, áudio, transcrição, resposta e sugestão aparecem na mesma ordem cronológica. Não existe destino separado chamado `Áudios`.

Uma sugestão é aberta em comparação explícita. A interface informa que aceitar cria uma nova versão; rejeitar ou fechar preserva o Markdown atual. O compositor multimodal permanece ancorado no fim da conversa com ações de texto, link, microfone/upload e envio/parada.

### Responsividade do workspace

Em telas estreitas, documento e conversa se tornam destinos alternáveis dentro da mesma escrita; o documento é o destino inicial. Navegação do livro abre como superfície temporária acessível, restaura foco ao fechar e não cria scroll concorrente com o documento. Áudio permanece dentro do compositor da conversa no mobile.

### Estados e recuperação

- Permissão de microfone negada oferece upload de arquivo no próprio compositor.
- Falha de upload preserva o arquivo local enquanto a página continuar aberta e oferece nova tentativa.
- Falha de transcrição mantém a mensagem de áudio e oferece reprocessamento.
- Cancelar geração preserva a resposta parcial.
- Enviar texto durante upload ou transcrição é permitido quando o backend suportar trabalhos independentes.
- A mesma ação não pode criar duas mensagens ou dois trabalhos por clique repetido.
- O compositor respeita IME, foco, teclado, busy states e geometria estável.

## Relação com o backend P0

A implementação de frontend continua usando contratos tipados e mocks, mas os contratos desta especificação se tornam a fronteira para:

- consultas públicas de landing, arquivo, livro e artigo;
- seleção manual do artigo em destaque;
- criação multimodal de mensagens;
- upload de áudio e acompanhamento de transcrição;
- associação de links, respostas e sugestões à conversa principal.

O plano do backend deve preservar idempotência, autorização, isolamento por escrita e projeções públicas mínimas.

## Acessibilidade e responsividade

- WCAG 2.2 AA permanece o alvo.
- Títulos e landmarks formam hierarquia honesta.
- Cards usam links semânticos; não há containers clicáveis com ações aninhadas ambíguas.
- Capas têm texto alternativo contextual ou são decorativas quando não acrescentam informação.
- Foco visível, redução de movimento e contraste seguem os tokens existentes.
- A landing funciona a 320 px e com zoom de 200% sem scroll horizontal da página.
- O compositor multimodal é operável por teclado e anuncia upload, transcrição, streaming, falha e conclusão em regiões apropriadas.

## Estratégia de testes

### Unidade e componentes

- fallback do artigo em destaque;
- livro sem artigo publicado nunca aparece;
- contagens e temas usam apenas dados públicos;
- landing vazia, parcial, carregando e com erro;
- compositor envia texto, link e áudio para a mesma conversa;
- retries não duplicam mensagens ou trabalhos;
- áudio negado, upload falho, transcrição falha e geração cancelada.

### Integração

- contratos públicos não contêm campos privados;
- navegação landing → livro → artigo;
- retorno ao arquivo preserva posição e filtros quando existirem;
- mensagens multimodais mantêm ordem e associação após refetch.

### Navegador e visual

- landing em desktop e mobile;
- conteúdo com e sem capas;
- títulos, autores e resumos longos;
- teclado, foco, reduced motion e zoom;
- comparação visual com a direção Estante em movimento aprovada;
- conversa com texto, áudio, transcrição, link e resposta na mesma linha do tempo.

## Critérios de aceite

1. A rota `/` apresenta artigo destacado, recentes, estante publicada e acesso ao arquivo usando dados públicos.
2. Nenhum livro sem artigo publicado aparece nas rotas públicas.
3. A landing não menciona IA nem expõe atividade privada.
4. Leitores conseguem navegar por artigo e por livro sem autenticação.
5. Texto, áudio e links são criados e exibidos dentro do mesmo chat principal da escrita.
6. Falhas de mídia não bloqueiam edição manual nem outras mensagens.
7. A implementação mantém o design system existente e corresponde à direção visual aprovada em desktop e mobile.
8. O workspace segue a direção Documento soberano: documento central prioritário, contexto esquerdo recolhível e uma conversa multimodal recolhível à direita.
