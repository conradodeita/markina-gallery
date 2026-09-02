#!/usr/bin/env bash
# Inventário/limpeza restritos ao banco e volumes da Markina Gallery em homologação.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"

MODE=""
CONFIRMATION=""

fail() {
  echo "maintain-homolog-data: $*" >&2
  return 1
}

compose() {
  # O script chega ao host por `bash -s`; nenhum subprocesso pode consumir
  # o restante da própria rotina pela entrada padrão compartilhada.
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@" </dev/null
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
    *) fail "argumento não permitido: $1" ;;
  esac
done

[[ "$MODE" == "inventory" || "$MODE" == "execute" ]] || fail "modo deve ser inventory ou execute"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
[[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "configuração exclusiva da Markina ausente"
compose config --quiet
echo "topologia: projeto=$PROJECT_NAME entrada=127.0.0.1:8080 subdomínio=markina-homolog.duckdns.org"
compose ps

if [[ "$MODE" == "inventory" ]]; then
  compose run --rm --no-deps -e APP_ENV=homolog api \
    python -m app.homolog_cleanup --mode inventory
  exit 0
fi

[[ "$CONFIRMATION" == "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS" ]] || fail "confirmação literal inválida"

mkdir -p "$BACKUP_DIR"
backup_file="$BACKUP_DIR/pre-cleanup-$(date -u +%Y%m%dT%H%M%SZ).dump"
compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_file"
echo "backup lógico exclusivo da Markina criado antes da limpeza"

restore_services() {
  compose up -d --no-deps api worker >/dev/null
}
trap restore_services EXIT
compose stop api worker
compose run --rm --no-deps -e APP_ENV=homolog api python -m app.homolog_cleanup \
  --mode execute --confirmation "$CONFIRMATION"
compose exec -T redis redis-cli FLUSHDB >/dev/null
restore_services
trap - EXIT
for service in api worker; do
  container="$(compose ps -q "$service")"
  status="unknown"
  for _attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || fail "serviço Markina não ficou saudável: $service ($status)"
done
compose run --rm --no-deps -e APP_ENV=homolog api \
  python -m app.homolog_cleanup --mode inventory
echo "limpeza de dados sintéticos da Markina concluída"
