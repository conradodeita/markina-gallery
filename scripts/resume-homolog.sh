#!/usr/bin/env bash
# Retoma somente os contêineres existentes da aplicação Markina em homologação.
# Migration, reconstrução, recreação e infraestrutura externa ficam fora deste fluxo.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly LOCAL_PUBLIC_BASE_URL="http://127.0.0.1:8080"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REQUIRED_SERVICES=(api web worker nginx)
readonly FACIAL_SERVICES=(face-search-worker face-index-worker face-maintenance-worker)

PUBLIC_BASE_URL=""
PREVIEW_WORKER_ACTIVE=0

usage() {
  echo "Uso: resume-homolog.sh --public-base-url <https://host>" >&2
}

fail() {
  echo "resume-homolog: $*" >&2
  return 1
}

compose() {
  local extra=()
  [[ -f "$STATE_DIR/branding.compose.yml" ]] && extra=(-f "$STATE_DIR/branding.compose.yml")
  if [[ "$PREVIEW_WORKER_ACTIVE" -eq 1 ]]; then
    extra+=(-f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment)
  fi
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile facial "${extra[@]}" "$@"
}

read_facial_enabled() {
  local occurrences value
  occurrences="$(grep -c '^FACIAL_PROCESSING_ENABLED=' "$ENV_FILE" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração FACIAL_PROCESSING_ENABLED duplicada"
  value="false"
  if [[ "$occurrences" -eq 1 ]]; then
    value="$(grep '^FACIAL_PROCESSING_ENABLED=' "$ENV_FILE")"
    value="${value#*=}"
    value="${value,,}"
  fi
  [[ "$value" == true || "$value" == false ]] || fail "FACIAL_PROCESSING_ENABLED inválida"
  printf '%s\n' "$value"
}

discover_services() {
  local facial_enabled service existing container
  SERVICES=("${REQUIRED_SERVICES[@]}")
  facial_enabled="$(read_facial_enabled)"
  if [[ "$facial_enabled" == true ]]; then
    SERVICES+=("${FACIAL_SERVICES[@]}")
  fi

  existing="$(docker ps --all --quiet \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --filter 'label=com.docker.compose.service=preview-adjustment-worker')"
  if [[ -n "$existing" ]]; then
    PREVIEW_WORKER_ACTIVE=1
    SERVICES+=(preview-adjustment-worker)
  fi

  for service in "${SERVICES[@]}"; do
    container="$(compose ps --all --quiet "$service")"
    if [[ -z "$container" ]]; then
      fail "contêiner existente ausente para serviço requerido: $service"
      return 1
    fi
  done
}

require_healthy_dependency() {
  local service="$1" container status
  container="$(compose ps --quiet "$service")"
  [[ -n "$container" ]] || fail "serviço de infraestrutura Markina não está em execução: $service"
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
  [[ "$status" == healthy ]] || fail "infraestrutura Markina não está saudável: $service ($status)"
}

read_database_revision() {
  local container revision
  container="$(compose ps --quiet db)"
  [[ -n "$container" ]] || fail "contêiner PostgreSQL Markina ausente"
  revision="$(docker exec "$container" sh -ec \
    'psql -X -A -t -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version"')"
  revision="${revision//$'\r'/}"
  revision="${revision//$'\n'/}"
  [[ -n "$revision" ]] || fail "revisão Alembic não encontrada no banco Markina"
  printf '%s\n' "$revision"
}

verify_schema_revision() {
  local revision
  revision="$(read_database_revision)"
  python3 "$SCRIPT_DIR/assert_homolog_schema_head.py" \
    --directory "$SCRIPT_DIR/../backend/migrations/versions" \
    --revision "$revision"
}

start_application_services() {
  compose up -d --no-deps --no-recreate "${SERVICES[@]}"
}

wait_for_health() {
  local deadline service container status
  deadline=$((SECONDS + 180))
  for service in "${SERVICES[@]}"; do
    container="$(compose ps --quiet "$service")"
    [[ -n "$container" ]] || fail "serviço ausente após retomada: $service"
    status="unknown"
    while (( SECONDS < deadline )); do
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
      [[ "$status" == healthy ]] && break
      sleep 1
    done
    [[ "$status" == healthy ]] || fail "serviço não ficou saudável: $service ($status)"
  done

  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$LOCAL_PUBLIC_BASE_URL/healthz" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$LOCAL_PUBLIC_BASE_URL/api/health" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/healthz" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/api/health" >/dev/null
}

main() {
  [[ "$PWD" == "$PROJECT_ROOT" ]] || fail "execute somente em $PROJECT_ROOT"
  [[ -f "$ENV_FILE" ]] || fail "arquivo Compose de homologação ausente"

  while (($#)); do
    case "$1" in
      --public-base-url)
        (($# >= 2)) || { usage; return 2; }
        PUBLIC_BASE_URL="${2%/}"
        shift 2
        ;;
      -h|--help)
        usage
        return 0
        ;;
      *)
        usage
        return 2
        ;;
    esac
  done
  [[ "$PUBLIC_BASE_URL" =~ ^https://[^/]+$ ]] || fail "informe a origem HTTPS pública, sem caminho"

  discover_services
  require_healthy_dependency db
  require_healthy_dependency redis
  verify_schema_revision
  echo "preflight aprovado: projeto=$PROJECT_NAME serviços=${SERVICES[*]} schema=compatível"

  start_application_services
  wait_for_health
  echo "retomada aprovada: serviços saudáveis e healthchecks locais/públicos HTTP 200; nenhuma migration executada"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
