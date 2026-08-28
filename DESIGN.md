---
version: alpha
colors:
  canvas: "#fbfaf9"
  surface: "#ffffff"
  surfaceMuted: "#f2f0ed"
  ink: "#121212"
  text: "#343433"
  textMuted: "#6f6d69"
  border: "#e5d5c3"
  link: "#0086fc"
  annotation: "#ff3e00"
  pending: "#d48f00"
  success: "#007a4d"
  danger: "#c91d2e"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Inter, sans-serif"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
  code:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
rounded:
  small: "6px"
  card: "10px"
  control: "12px"
  pill: "9999px"
spacing:
  unit: "4px"
components:
  surface:
    border: "inset 0 0 0 1px #f2f0ed"
  focusRing:
    color: "#0086fc"
---

# Entrelinhas — identidade visual

## Overview

Entrelinhas é um caderno vivo de leitura: superfícies calmas de papel, marginalia visível e uma única ação forte em tinta. A área privada é um instrumento de escrita para um autor; a área pública é uma estante editorial para leitores. O produto deve parecer habitado por ideias em andamento, sem imitar um editor corporativo, um dashboard de métricas ou um scrapbook infantil.

A assinatura é o **trilho de marginalia**. Áudio, prompt, fonte e sugestão aceita aparecem como pequenas marcas coloridas alinhadas ao documento. A marca conecta o momento de pensar ao trecho escrito sem virar a única forma de acessar o evento. Ilustrações expressivas ficam restritas a estados vazios e capas públicas; o estúdio permanece silencioso e utilitário.

O sistema é híbrido: o produto privado privilegia clareza, densidade confortável e continuidade; as rotas públicas ganham mais escala tipográfica e espaço editorial, mantendo a mesma gramática de papel, tinta e anotações.

## Colors

`canvas` é o papel contínuo. `surface` recebe cartões e painéis; `surfaceMuted` cria agrupamento sem elevação. `ink` é reservado para a ação principal e títulos de maior peso. `link` indica navegação e foco; `annotation` marca pensamento e destaque, nunca um botão preenchido.

`pending`, `success` e `danger` são semânticos. Cor nunca opera sozinha: ícone, rótulo ou texto acompanha cada estado. Não usar gradientes. Não ampliar a paleta original dentro do estúdio; cores ilustrativas adicionais pertencem somente a capas e estados vazios.

## Typography

Bricolage Grotesque dá personalidade a títulos de página e chamadas editoriais. Inter sustenta leitura e controles. IBM Plex Mono identifica Markdown, metadados técnicos e pequenos rótulos do trilho. A escala parte de 12px para utilidade, 15–17px para interface e 32–64px para expressão editorial responsiva.

Títulos usam entrelinha compacta e tracking negativo leve. Texto corrido usa entrelinha de 1.55–1.7. Não usar caixa alta em parágrafos; micro-rótulos podem usar caixa alta com espaçamento somente quando funcionarem como indexação.

## Layout

O grid privado usa uma moldura de até 1440px com navegação de contexto, documento e assistente. Cada painel é dono do próprio scroll em desktop; em telas estreitas, o documento volta a ser o scroll principal e a navegação se transforma em controles compactos. A área pública usa coluna de leitura de 68ch e respiros amplos.

Espaçamento deriva da unidade de 4px, com ritmo recorrente de 8, 12, 16, 24, 32 e 48px. O trilho ocupa uma coluna estreita adjacente ao texto e nunca reduz a medida de leitura abaixo do confortável.

## Elevation & Depth

Superfícies estáticas são planas. Cartões usam a linha interna definida em `components.surface.border`; sombras externas aparecem somente em overlays e devem permanecer sutis. Profundidade vem de mudança tonal entre canvas, superfície e superfície atenuada.

## Shapes

Cartões usam 10px, controles 12px e pequenos marcadores 6px. Pílulas são reservadas a estados compactos, filtros e ações de alta frequência; não arredondar toda a interface por padrão. Capas e ilustrações podem usar formas orgânicas, mas o chrome do produto permanece geométrico.

## Components

- Ação primária: fundo `ink`, texto branco, sem gradiente, altura estável em estado ocupado.
- Ações neutras: superfície clara e linha interna; links permanecem links.
- Campos: rótulo persistente, ajuda/erro associados e foco azul visível.
- Toasts: região fixa e estável, tom semântico e mensagem curta; erros corrigíveis permanecem inline.
- Diálogos: superfície própria, título e descrição acessíveis, foco inicial seguro e restauração ao gatilho.
- Trilho de marginalia: marca + tipo + horário/trecho acessível; laranja é a marca editorial principal.
- Capas: composições abstratas inspiradas em sublinhados, páginas dobradas e notas, nunca mascotes genéricos.

## Do's and Don'ts

### Faça

- Use o trilho para revelar o processo de pensamento sem competir com o texto.
- Preserve uma ação escura dominante por região.
- Separe superfícies por tom e hairline, não por sombras grandes.
- Dê à leitura pública mais espaço e à autoria privada mais continuidade operacional.
- Respeite foco visível, contraste AA, movimento reduzido e geometrias estáveis.

### Não faça

- Não use gradientes, glassmorphism, brilho neon ou cartões flutuantes genéricos.
- Não transforme cores de capa em novos significados de status.
- Não use laranja como botão preenchido nem azul como decoração sem função.
- Não esconda scrollbars ou ações essenciais atrás de hover.
- Não espalhe ilustrações dentro do editor, chat ou revisão de sugestões.
