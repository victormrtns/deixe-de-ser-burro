# Handoff — Books Blog AI / Entrelinhas

## Objetivo da próxima sessão

Retomar este projeto com o fluxo Superpowers. Ler a especificação aprovada e o plano de frontend existente antes de fazer perguntas ou alterar arquivos. A próxima etapa provável é incorporar os padrões de código, testes, QA e gates de validação fornecidos pelo autor, revisar o plano caso esses padrões exijam mudanças e escolher o fluxo de execução.

## Estado atual

- O brainstorming de produto e arquitetura foi concluído e aprovado.
- O produto é uma aplicação pessoal para transformar anotações manuscritas sobre livros em artigos Markdown por meio de um ciclo de áudios curtos, prompts, edição manual, sugestões de IA, revisão e publicação.
- Especificação do produto:
  - `docs/superpowers/specs/2026-08-28-ai-books-learning-blog-design.md`
- Plano de identidade visual e frontend:
  - `docs/superpowers/plans/2026-08-28-visual-identity-frontend.md`
- O plano de frontend possui 12 tarefas e 65 passos, já verificados estruturalmente.
- Referências visuais existentes:
  - `design.md`
  - `tailwind.css`
- Skills React fornecidas pelo autor:
  - `docs/patterns/vercel-composition-patterns/`
  - `docs/patterns/vercel-react-best-practices/`
- Nenhuma implementação foi iniciada e nenhuma dependência foi instalada.
- `git status` não reconheceu a pasta como um repositório Git válido; não há commits da especificação ou do plano.

## Decisões principais

- Stack: React, Python/FastAPI, PostgreSQL e Docker Compose; deploy futuro em VPS simples.
- Desenvolvimento local primeiro, com arquitetura preparada para uso online.
- Teto operacional de R$ 50–70/mês para VPS e IA, considerando cerca de cinco horas de áudio mensais.
- Um autor privado e leitores públicos sem autenticação.
- Hierarquia: biblioteca → vários livros → várias escritas/artigos por livro.
- Conversas, áudios, transcrições, links, sugestões e versões pertencem a uma escrita específica.
- Markdown é o formato canônico, com Mermaid, código e LaTeX no preview.
- O autor intercala áudios curtos, prompts, links e edição manual continuamente.
- A IA nunca altera o Markdown diretamente; toda mudança passa por comparação e aprovação.
- O contexto padrão do chat inclui a escrita, suas transcrições, referências, mensagens recentes e resumo acumulado.
- Um chat principal é obrigatório; chats auxiliares são P1 opcional.
- Links podem ser processados temporariamente; título, URL e resumo ficam associados à conversa.
- Publicar congela uma versão pública. O contexto privado é removido após três dias de recuperação.
- Frontend planejado como React 19 + TypeScript + Vite, usando contratos tipados e MSW antes do backend.
- A identidade adapta a referência creme/papel para leitura e marginalia. `Entrelinhas` é apenas o nome de trabalho atual.
- Componentes usam composição, compound components, providers focados e variantes explícitas.
- Performance: SWR, imports diretos, code splitting, preview deferido e separação entre bundles públicos e privados.
- Acessibilidade: WCAG 2.2 AA.

## Decisões pendentes

- Receber e aplicar os padrões de código, testes, QA e gates automatizados do autor.
- Confirmar ou substituir o nome de trabalho `Entrelinhas` antes da identidade visual final.
- Escolher a execução:
  1. subagent-driven development, com revisão entre tarefas; ou
  2. execução inline, com checkpoints.
- Estabelecer um repositório/branch Git válido antes de seguir os passos de commit.

## Primeiras ações recomendadas

1. Ler integralmente a especificação e o plano indicados acima.
2. Ler os novos padrões de engenharia fornecidos pelo autor.
3. Comparar esses padrões com as restrições globais e os gates da Tarefa 12 do plano.
4. Atualizar o plano apenas onde necessário; não repetir o brainstorming já aprovado.
5. Pedir aprovação para alterações materiais em identidade, arquitetura, privacidade, retenção ou fluxo.
6. Confirmar o estado do Git e escolher o fluxo de execução do Superpowers.

## Skills sugeridas

- `superpowers:using-superpowers`
- `superpowers:receiving-code-review`, se os padrões vierem como feedback sobre o plano
- `superpowers:writing-plans`, somente se o plano precisar ser revisado
- `superpowers:subagent-driven-development` ou `superpowers:executing-plans`, conforme a execução escolhida
- `superpowers:test-driven-development`
- `superpowers:verification-before-completion`
- `frontend-design`
- `frontend-design-premium:frontend-design-premium`
- `vercel-composition-patterns`
- `vercel-react-best-practices`

## Prompt para retomada

Leia `docs/handoffs/current.md`, depois leia integralmente a especificação do produto e o plano de frontend referenciados nele. Use o Superpowers e continue do estado aprovado, sem repetir o discovery. Primeiro incorpore os padrões de código, testes, QA e gates que eu fornecer; depois reconcilie o plano de frontend e solicite minha aprovação para qualquer mudança material antes da implementação.
