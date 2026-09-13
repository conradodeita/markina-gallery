#!/usr/bin/env bash
# Inventário/limpeza restritos ao banco e volumes da Markina Gallery em homologação.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"
readonly WITHOUT_BACKUP_CONFIRMATION="DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP"

MODE=""
CONFIRMATION=""
WITHOUT_BACKUP=false

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
    --without-backup) WITHOUT_BACKUP=true; shift ;;
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
  [[ "$WITHOUT_BACKUP" == "false" && -z "$CONFIRMATION" ]] || \
    fail "inventário não aceita confirmação nem modo sem backup"
  compose run --rm --no-deps -e APP_ENV=homolog api \
    python -m app.homolog_cleanup --mode inventory
  exit 0
fi

if [[ "$WITHOUT_BACKUP" == "true" ]]; then
  [[ "$CONFIRMATION" == "$WITHOUT_BACKUP_CONFIRMATION" ]] || \
    fail "confirmação literal inválida para limpeza sem backup"
else
  [[ "$CONFIRMATION" == "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS" ]] || \
    fail "confirmação literal inválida"
fi

paused_services=(api worker)
if grep -Fxq 'FACIAL_PROCESSING_ENABLED=true' "$ENV_FILE"; then
  paused_services+=(face-index-worker face-search-worker face-maintenance-worker)
fi

restore_services() {
  compose up -d --no-deps "${paused_services[@]}" >/dev/null
}
trap restore_services EXIT
compose stop "${paused_services[@]}"
pre_inventory="$(compose run --rm --no-deps -e APP_ENV=homolog api \
  python -m app.homolog_cleanup --mode inventory)"
printf 'inventário anterior: %s\n' "$pre_inventory"

if [[ "$WITHOUT_BACKUP" == "true" ]]; then
  echo "limpeza sem novo backup autorizada pelo token exclusivo"
else
  mkdir -p "$BACKUP_DIR"
  backup_file="$BACKUP_DIR/pre-cleanup-$(date -u +%Y%m%dT%H%M%SZ).dump"
  compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_file"
  echo "backup lógico exclusivo da Markina criado antes da limpeza"
fi

compose run --rm --no-deps -e APP_ENV=homolog api python -m app.homolog_cleanup \
  --mode execute --confirmation "$CONFIRMATION"
compose exec -T redis redis-cli FLUSHDB >/dev/null
restore_services
trap - EXIT
compose restart nginx >/dev/null
services_to_check=(nginx web "${paused_services[@]}")
for service in "${services_to_check[@]}"; do
  container="$(compose ps -q "$service")"
  [[ -n "$container" ]] || fail "serviço Markina ausente após limpeza: $service"
  status="unknown"
  for _attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || fail "serviço Markina não ficou saudável: $service ($status)"
done
curl --fail --silent --show-error --max-time 15 \
  http://127.0.0.1:8080/api/health >/dev/null || \
  fail "rota HTTP da Markina não ficou saudável após a manutenção"
post_inventory="$(compose run --rm --no-deps -e APP_ENV=homolog api \
  python -m app.homolog_cleanup --mode inventory)"
printf 'inventário posterior: %s\n' "$post_inventory"
PRE_INVENTORY="$pre_inventory" POST_INVENTORY="$post_inventory" python3 - <<'PY'
import json
import os

before = json.loads(os.environ["PRE_INVENTORY"])
after = json.loads(os.environ["POST_INVENTORY"])
if any(after["database"].values()):
    raise SystemExit("contagens operacionais não foram zeradas")
if any(value for root in after["media"].values() for value in root.values()):
    raise SystemExit("mídia operacional não foi zerada")
if before["preserved"] != after["preserved"]:
    raise SystemExit("admin, sessões/fatores ou preferências não foram preservados")
print("preservação administrativa e preferências: verificada")
PY
facial_flag="$(sed -n 's/^FACIAL_PROCESSING_ENABLED=//p' "$ENV_FILE" | tail -n 1)"
[[ "$facial_flag" == "true" || "$facial_flag" == "false" ]] || \
  fail "FACIAL_PROCESSING_ENABLED ausente ou inválido"
echo "coerência facial: FACIAL_PROCESSING_ENABLED=$facial_flag"
echo "limpeza de dados sintéticos da Markina concluída"
