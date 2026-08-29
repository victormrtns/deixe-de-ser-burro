#!/usr/bin/env bash
# Daily encrypted backup of the app_files volume (covers), shipped off-host.
# Requires: age, sha256sum, scp, and a running compose stack.
set -euo pipefail

: "${BACKUP_REMOTE:?defina BACKUP_REMOTE (destino scp fora da máquina, ex.: user@host:/backups)}"
: "${AGE_RECIPIENT:?defina AGE_RECIPIENT (chave pública age para criptografia)}"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact="$workdir/entrelinhas-files-$stamp.tar.age"

# Deterministic tar (sorted names, pinned mtime) so equal content hashes equal.
docker compose run --rm --no-deps -T backend \
  tar --create --sort=name --mtime='UTC 2020-01-01' --directory /data/files . \
  | age --recipient "$AGE_RECIPIENT" > "$artifact"

(cd "$workdir" && sha256sum "$(basename "$artifact")" > "$artifact.sha256")

scp -q "$artifact" "$artifact.sha256" "$BACKUP_REMOTE"

echo "Backup enviado: $(basename "$artifact")"
cat "$artifact.sha256"
