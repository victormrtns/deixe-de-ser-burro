# injecao-de-instrucao-no-markdown

## Pergunta

Sobre o que essa nota está falando, na sua leitura? E abrir o artigo com aquela linha solta funciona ou é truque barato?

## Resposta

Está falando do problema clássico de "prompt injection" e da noção mais geral de procedência de instruções: tanto modelos quanto leitores humanos recebem tudo como sequência de texto e, se não houver critério claro sobre quais instruções valem, uma ordem embutida no conteúdo pode ser seguida. A nota aponta dois pontos centrais: (1) o vetor de ataque mais barato é inserir uma ordem no próprio documento; (2) a defesa não é filtrar frases suspeitas, é declarar de antemão quais fontes de instrução são autorizadas — e isso vale para leitores humanos também.

Sobre abrir o artigo com a linha solta ("Ignore as instruções anteriores..."): pode funcionar, mas depende do objetivo e do contexto.

- Vantagens: dá choque imediato, exemplifica na prática o problema e prende a atenção; torna a ideia concreta sem explicação técnica.
- Riscos: pode parecer truque barato ou manipulativo se não for seguida de explicação imediata; há chance do leitor perder a piada/propósito e se irritar; funciona melhor se você controlar a leitura (ex.: em palestra, post com contexto curto) do que como entrada fria em um artigo extenso.

Sugestões concretas de uso (rápidas):
- Se for usar, emende logo na frase com uma explicação curta: por que a frase é ali, o que ela demonstra e o que o leitor deve observar. Não deixe ficar solta tempo demais.
- Alternativa menos arriscada: introduza a tese em uma frase forte e depois mostre a linha como exemplo/experimento. Assim você evita que pareça puro golpe retórico.
- Teste com 3–5 leitores beta: pergunte se sentiram que foi útil ou manipulação; ajuste conforme o feedback.

Se quiser, posso sugerir duas aberturas possíveis (uma mais direta com a linha solta + debrief imediato; outra que evita o choque) mantendo sua voz. Quer que eu escreva essas opções?
