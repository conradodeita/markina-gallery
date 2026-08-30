#!/usr/bin/env bash
# Entrega contínua restrita à Markina Gallery em homologação.
# Este script é executado no servidor por GitHub Actions e nunca aceita outro projeto.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"
readonly EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:?MARKINA_EXPECTED_REPOSITORY é obrigatório}"

DEPLOY_SHA=""
PUBLIC_BASE_URL="${MARKINA_PUBLIC_BASE_URL:-}"
PREVIOUS_SHA=""
MIGRATION_CHANGED=0
SCHEMA_ROLLBACK_UNSAFE=0
SHA_SWITCHED=0

usage() {
  echo "Uso: deploy-homolog.sh --sha <sha-completo> [--public-base-url <https://...>]" >&2
}

fail() {
  echo "deploy-homolog: $*" >&2
  return 1
}

compose() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

verify_clean_checkout() {
  [[ -z "$(git status --porcelain)" ]] || fail "checkout remoto possui alterações locais; reconciliação humana necessária"
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --sha)
        DEPLOY_SHA="${2:-}"
        shift 2
        ;;
      --public-base-url)
        PUBLIC_BASE_URL="${2:-}"
        shift 2
        ;;
      *)
        usage
        fail "argumento não permitido: $1"
        ;;
    esac
  done

  [[ "$DEPLOY_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "o SHA deve ter 40 caracteres hexadecimais minúsculos"
  [[ -z "$PUBLIC_BASE_URL" || "$PUBLIC_BASE_URL" =~ ^https://[^[:space:]]+$ ]] || fail "a URL pública deve usar HTTPS"
}

verify_target() {
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "o deploy só pode executar em $PROJECT_ROOT"
  [[ -f "$COMPOSE_FILE" ]] || fail "arquivo Compose esperado não encontrado"
  [[ -f "$ENV_FILE" ]] || fail "arquivo de ambiente de homologação não encontrado"
  [[ "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail "o diretório não é o checkout esperado"
  verify_clean_checkout

  local origin_url
  origin_url="$(git remote get-url origin)"
  [[ "$origin_url" =~ github\.com[:/]${EXPECTED_REPOSITORY//\//\/}(\.git)?$ ]] || fail "origin não aponta para o repositório GitHub esperado"

  mkdir -p "$STATE_DIR" "$BACKUP_DIR"
  compose config --quiet
}

record_revision() {
  local label="$1"
  local sha="$2"
  printf '%s\n' "$sha" > "$STATE_DIR/$label.sha"
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" "$sha" >> "$STATE_DIR/history.log"
}

current_revision() {
  compose run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r' | tail -n 1
}

apply_target_migrations() {
  local previous_revision="$1" next_revision

  # A imagem do serviço migrate pode pertencer ao SHA anteriormente publicado.
  # Reconstrua-a após selecionar o alvo para que o Alembic enxergue exatamente
  # as revisions do commit que será iniciado nos demais serviços.
  compose build migrate || {
    fail "não foi possível construir a migration do SHA alvo"
    return 1
  }

  # Depois que Alembic começa, uma falha pode significar schema parcialmente
  # alterado. O rollback automático de código fica bloqueado até comprovarmos
  # que a revisão permaneceu exatamente igual à anterior.
  SCHEMA_ROLLBACK_UNSAFE=1
  compose run --rm --no-deps migrate || {
    fail "migration do SHA alvo falhou; banco preservado para revisão humana"
    return 1
  }
  next_revision="$(current_revision)" || {
    fail "não foi possível confirmar a revisão após a migration"
    return 1
  }
  [[ -n "$next_revision" && "$next_revision" == *"(head)"* ]] || {
    fail "migration não alcançou o head do SHA alvo"
    return 1
  }
  echo "migration Markina: ${previous_revision:-sem revisão} -> $next_revision"
  if [[ "$next_revision" != "$previous_revision" ]]; then
    MIGRATION_CHANGED=1
  else
    SCHEMA_ROLLBACK_UNSAFE=0
  fi
}

create_backup() {
  local timestamp backup_file manifest_file
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup_file="$BACKUP_DIR/predeploy-${timestamp}-${DEPLOY_SHA:0:12}.dump"
  manifest_file="$BACKUP_DIR/predeploy-${timestamp}-${DEPLOY_SHA:0:12}.manifest.txt"

  compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_file"
  {
    printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'previous_sha=%s\n' "$PREVIOUS_SHA"
    printf 'target_sha=%s\n' "$DEPLOY_SHA"
    printf 'database_backup=%s\n' "$backup_file"
  } > "$manifest_file"
  echo "backup lógico exclusivo da Markina criado"
}

wait_for_health() {
  local service container status attempt
  for service in api web worker nginx; do
    container="$(compose ps -q "$service")"
    [[ -n "$container" ]] || fail "serviço Markina ausente após deploy: $service"
    for attempt in $(seq 1 30); do
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
      [[ "$status" == "healthy" ]] && break
      sleep 2
    done
    [[ "$status" == "healthy" ]] || fail "serviço Markina não ficou saudável: $service ($status)"
  done

  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
  if [[ -n "$PUBLIC_BASE_URL" ]]; then
    curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/healthz" >/dev/null
    curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/api/health" >/dev/null
  fi
}

whatsapp_real_is_active() {
  compose config --services | grep -Fxq evolution-api
}

start_whatsapp_infrastructure_if_active() {
  if ! whatsapp_real_is_active; then
    echo "WhatsApp real inativo; sandbox preservado"
    return 0
  fi
  compose up -d evolution-db evolution-redis evolution-api
  local service container status attempt
  for service in evolution-db evolution-redis evolution-api; do
    container="$(compose ps -q "$service")"
    [[ -n "$container" ]] || fail "serviço WhatsApp Markina ausente: $service"
    status="unknown"
    for attempt in $(seq 1 60); do
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
      [[ "$status" == "healthy" ]] && break
      sleep 2
    done
    [[ "$status" == "healthy" ]] || fail "serviço WhatsApp Markina não ficou saudável: $service ($status)"
  done
}

rollback_code_if_safe() {
  local exit_code="$1"
  trap - ERR
  if [[ "$SHA_SWITCHED" -eq 1 && "$MIGRATION_CHANGED" -eq 0 && "$SCHEMA_ROLLBACK_UNSAFE" -eq 0 && -n "$PREVIOUS_SHA" ]]; then
    echo "falha antes de mudança de schema; restaurando somente código Markina para $PREVIOUS_SHA" >&2
    git switch --detach "$PREVIOUS_SHA"
    compose up -d --build --no-deps api web worker
    compose up -d --force-recreate --no-deps nginx
    record_revision "last-rollback" "$PREVIOUS_SHA"
  else
    echo "rollback automático de código não é seguro após mudança de schema; banco não foi restaurado" >&2
  fi
  exit "$exit_code"
}

main() {
  parse_arguments "$@"
  verify_target
  trap 'rollback_code_if_safe $?' ERR

  git fetch --quiet origin develop
  git fetch --quiet origin "$DEPLOY_SHA"
  git cat-file -e "${DEPLOY_SHA}^{commit}"
  git merge-base --is-ancestor "$DEPLOY_SHA" origin/develop || fail "o SHA não pertence a origin/develop"

  PREVIOUS_SHA="$(git rev-parse HEAD)"
  record_revision "previous" "$PREVIOUS_SHA"
  create_backup

  local previous_revision
  previous_revision="$(current_revision)"
  git switch --detach "$DEPLOY_SHA"
  SHA_SWITCHED=1
  apply_target_migrations "$previous_revision"

  start_whatsapp_infrastructure_if_active
  compose up -d --build --no-deps api web worker
  compose up -d --force-recreate --no-deps nginx
  wait_for_health
  record_revision "last-healthy" "$DEPLOY_SHA"
  echo "deploy-homolog concluído para $DEPLOY_SHA"
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
  main "$@"
fi
