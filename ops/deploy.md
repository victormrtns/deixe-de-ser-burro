# Deploy e recuperação na VPS

O diretório da aplicação na VPS é `/opt/entrelinhas` (checkout versionado). Só o
frontend/reverse proxy é exposto publicamente; `backend` e `db` ficam na rede
interna do Compose. TLS termina no proxy (Caddy ou nginx + certbot).

## Segredos

- `.env` fica em `/opt/entrelinhas/.env`, fora do Git, com permissão `600`.
- `POSTGRES_PASSWORD` forte; `COOKIE_SECURE=true`; `ENVIRONMENT=production`
  (a aplicação recusa produção com cookie inseguro).
- Chaves `age` (backup) ficam apenas na VPS e no cofre pessoal do autor.

## Ordem de deploy

## 1. Backup pré-deploy

```bash
BACKUP_REMOTE=... AGE_RECIPIENT=... ops/backup-postgres.sh
BACKUP_REMOTE=... AGE_RECIPIENT=... ops/backup-files.sh
```

Antes de migração potencialmente destrutiva, crie um backup adicional.
Migrações destrutivas usam expand/contract em entregas separadas.

## 2. Migração

```bash
git fetch && git checkout <tag>
docker compose build --pull
docker compose run --rm migrate
```

## 3. Subir os serviços

```bash
docker compose up -d db backend frontend
```

## 4. Readiness e troca do proxy

```bash
curl -fsS http://127.0.0.1:8000/api/health/ready
```

Só recarregue/troque o proxy depois do readiness responder
`{"status":"ready","database":"ok","migration":"head"}`.

## Rollback

1. `git checkout <tag-anterior>` e `docker compose up -d --build`.
2. Se a migração precisar reverter: `docker compose run --rm migrate` com o
   Alembic da tag anterior (downgrade só quando seguro) ou restaure o backup.

## Rotina operacional

- Backups diários via cron/systemd chamando os dois scripts de backup.
- Limpeza de publicações: instale `ops/cleanup.service` e `ops/cleanup.timer`
  em `/etc/systemd/system/` e habilite com `systemctl enable --now cleanup.timer`.
  `Persistent=true` recupera janelas perdidas por downtime.
- Drill de restauração periódico (mensal):
  `TEST_RESTORE=1 RESTORE_ARTIFACT=... AGE_IDENTITY=... ops/restore-smoke.sh`.
  Backup sem restore testado não conta como recuperação.

## Retenção e privacidade

Backups criptografados podem reter material privado (Markdown, capas) até a
expiração da política de retenção do destino; a limpeza pós-publicação não
alcança backups já enviados. Dimensione a retenção com isso em mente.
