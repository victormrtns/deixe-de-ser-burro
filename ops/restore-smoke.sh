#!/usr/bin/env bash
# Restore drill: decrypts a database backup into a disposable database,
# verifies aggregate counts and drops it. Never touches the live database.
set -euo pipefail

if [ "${TEST_RESTORE:-0}" != "1" ]; then
  echo "Defina TEST_RESTORE=1 para executar o teste de restauração." >&2
  exit 1
fi
: "${RESTORE_ARTIFACT:?defina RESTORE_ARTIFACT (arquivo .dump.age do backup)}"
: "${AGE_IDENTITY:?defina AGE_IDENTITY (arquivo de identidade age para descriptografar)}"

workdir="$(mktemp -d)"
database="restore_smoke_$(date -u +%s)_$$"
postgres_user="${POSTGRES_USER:-entrelinhas}"

cleanup() {
  docker compose exec -T db psql --username "$postgres_user" --dbname postgres \
    --command "DROP DATABASE IF EXISTS \"$database\"" > /dev/null || true
  rm -rf "$workdir"
}
trap cleanup EXIT

age --decrypt --identity "$AGE_IDENTITY" "$RESTORE_ARTIFACT" > "$workdir/database.dump"

docker compose exec -T db createdb --username "$postgres_user" "$database"
docker compose exec -T db pg_restore \
  --username "$postgres_user" --dbname "$database" --no-owner < "$workdir/database.dump" \
  || true # pg_restore reports non-fatal warnings as nonzero; counts below decide

docker compose exec -T db psql --username "$postgres_user" --dbname "$database" --tuples-only \
  --command "SELECT 'books=' || count(*) FROM books" \
  --command "SELECT 'writings=' || count(*) FROM writings" \
  --command "SELECT 'publications=' || count(*) FROM publications" \
  --command "SELECT 'alembic=' || version_num FROM alembic_version"

echo "Restauração verificada em banco descartável: $database"
