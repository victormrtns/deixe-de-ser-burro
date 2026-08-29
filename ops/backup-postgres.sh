#!/usr/bin/env bash
# Daily encrypted PostgreSQL backup shipped off-host.
# Requires: age, sha256sum, scp, and a running compose stack.
set -euo pipefail

: "${BACKUP_REMOTE:?defina BACKUP_REMOTE (destino scp fora da máquina, ex.: user@host:/backups)}"
: "${AGE_RECIPIENT:?defina AGE_RECIPIENT (chave pública age para criptografia)}"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact="$workdir/entrelinhas-db-$stamp.dump.age"

docker compose exec -T db pg_dump \
  --format=custom \
  --username "${POSTGRES_USER:-entrelinhas}" \
  "${POSTGRES_DB:-entrelinhas}" \
  | age --recipient "$AGE_RECIPIENT" > "$artifact"

(cd "$workdir" && sha256sum "$(basename "$artifact")" > "$artifact.sha256")

scp -q "$artifact" "$artifact.sha256" "$BACKUP_REMOTE"

echo "Backup enviado: $(basename "$artifact")"
cat "$artifact.sha256"
