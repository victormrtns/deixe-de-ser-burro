# Stack local para integração e E2E

Os testes de navegador usam o frontend em `http://127.0.0.1:4173` e encaminham
`/api` para o backend em `http://127.0.0.1:8000`. Prepare a stack com a mesma
origem aceita pelo backend:

```bash
export POSTGRES_PASSWORD=entrelinhas
export PUBLIC_ORIGIN=http://127.0.0.1:4173
export AUTHOR_EMAIL=e2e@example.com
export AUTHOR_PASSWORD='correct horse'
docker compose up -d db
docker compose run --rm migrate
docker compose run --rm bootstrap-author
docker compose up -d backend
npm --prefix frontend run test:e2e
```

O bootstrap do autor é idempotente. `global-setup.ts` encerra cedo com uma
mensagem diagnóstica se `/api/health/ready` não estiver acessível pelo proxy.
As credenciais podem ser substituídas por `E2E_AUTHOR_EMAIL` e
`E2E_AUTHOR_PASSWORD` ao executar o Playwright.

## Assistente: modo falso primeiro

`AI_GATEWAY` aceita `disabled`, `fake` e `openai`. O padrão do repositório é
`disabled`, e é ele que vale em qualquer ambiente onde ninguém tenha decidido o
contrário. Para desenvolver e rodar os testes de navegador, use `fake`:

```bash
export POSTGRES_PASSWORD=entrelinhas
export PUBLIC_ORIGIN=http://127.0.0.1:4173
export AUTHOR_EMAIL=e2e@example.com
export AUTHOR_PASSWORD='correct horse'
export AI_GATEWAY=fake
docker compose up -d db
docker compose run --rm migrate
docker compose run --rm bootstrap-author
docker compose up -d backend
```

O `FakeModelGateway` emite a mesma sequência de eventos do contrato interno,
incluindo conclusão, interrupção, timeout, rate limit e saída inválida. Ele não
acessa a rede e não custa nada.

Com o assistente desligado (`AI_GATEWAY=disabled`) o produto continua inteiro:
editor, histórico de versões, leitura pública e publicação funcionam
normalmente. Só as capacidades de IA ficam indisponíveis. Isso é comportamento
esperado, não degradação a ser contornada.

## Assistente: modo OpenAI, autorizado e pontual

O modo `openai` existe para uma validação manual curta, com começo e fim na
mesma sessão. Ele não é modo de desenvolvimento.

`OPENAI_API_KEY` existe **apenas** como variável de ambiente do backend. Nunca
no banco, nunca em log, nunca no frontend, nunca em arquivo versionado, nunca em
`.env` commitado. `compose.yaml` já a repassa a partir do ambiente do shell.

1. **Conferir o orçamento antes de qualquer coisa.** Some o que já foi gasto e
   reservado até aqui:

```bash
docker compose exec db psql -U entrelinhas -d entrelinhas -c \
  "select coalesce(sum(coalesce(actual_usd_micros, reserved_usd_micros)), 0) / 1000000.0 as usd_usado from ai_usage_entries;"
```

2. **Carregar a chave sem ecoá-la e subir o backend em modo `openai`.** O `read -rs`
   não mostra o valor na tela nem o deixa no histórico do shell:

```bash
read -rs OPENAI_API_KEY && export OPENAI_API_KEY
export AI_GATEWAY=openai
docker compose up -d backend
```

3. **Enviar um único prompt.** Use o serviço `frontend`, que serve em
   `http://127.0.0.1:5173`; para isso `PUBLIC_ORIGIN` precisa ser
   `http://127.0.0.1:5173` no momento em que o backend sobe, e não a origem
   `4173` usada pelo Playwright:

```bash
export PUBLIC_ORIGIN=http://127.0.0.1:5173
docker compose up -d backend frontend
```

   Abra uma escrita autenticada e envie uma mensagem curta. Uma mensagem, uma
   tentativa, sem retry exploratório.

4. **Verificar o uso registrado e o custo observado:**

```bash
docker compose exec db psql -U entrelinhas -d entrelinhas -c \
  "select state, model, instruction_version, input_tokens, output_tokens, total_tokens, estimated_cost_usd_micros, latency_ms from generation_attempts order by created_at desc limit 1;"
docker compose logs --since 10m backend
```

Confira que a tentativa está `completed`, que os tokens vieram do provedor, que
o custo cabe na reserva e que os logs não contêm Markdown, mensagens, respostas
nem qualquer fragmento da chave.

5. **Voltar imediatamente para `disabled`.** Isto faz parte do procedimento, não
   é limpeza opcional:

```bash
export AI_GATEWAY=disabled
unset OPENAI_API_KEY
docker compose up -d backend
```

### Tetos de orçamento

- US$ 2,00 no total para esta fase (`AI_DEVELOPMENT_BUDGET_USD`).
- No máximo US$ 0,25 do total em validações manuais reais
  (`AI_MANUAL_SMOKE_BUDGET_USD`).
- Zero para testes automatizados: eles usam apenas o gateway falso e nunca
  chamam o provedor.

O saldo da conta OpenAI não é o orçamento do produto. O teto de produção será
decidido depois, com dados observados.

### Nunca imprimir o ambiente nem a chave

`env`, `printenv`, `docker compose config` e `echo $OPENAI_API_KEY` vazam o
valor da chave para a tela, para o log da sessão e para qualquer gravação em
curso. Não use nenhum deles enquanto a chave estiver exportada. Para inspecionar
a configuração do compose sem segredo, faça isso com `AI_GATEWAY=disabled` e sem
`OPENAI_API_KEY` no ambiente.

Não cole a chave em terminal que esteja sendo gravado ou compartilhado, não a
cole em commit, mensagem, issue ou comentário, e prefira `read -rs` a digitá-la
em linha de comando. Se a chave aparecer em algum lugar, revogue-a no painel do
provedor em vez de tentar apagar o rastro.

### O smoke test exige aprovação explícita

O smoke test real só roda depois que todos os gates com gateway falso passarem e
depois que o autor aprovar explicitamente aquela execução. Antes de pedir a
aprovação, apresente a evidência do modo falso e o custo máximo estimado. Sem
aprovação registrada, o `AI_GATEWAY` permanece em `disabled`.
