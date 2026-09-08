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
REQUESTED_FACIAL_ENABLED=""
PREVIOUS_SHA=""
PREVIOUS_FACIAL_ENABLED=""
MIGRATION_CHANGED=0
SCHEMA_ROLLBACK_UNSAFE=0
SHA_SWITCHED=0
FACIAL_ENV_CHANGED=0
FACIAL_DEPLOY_ENABLED="false"
readonly FACIAL_SERVICES=("face-search-worker" "face-index-worker" "face-maintenance-worker")

usage() {
  echo "Uso: deploy-homolog.sh --sha <sha-completo> [--public-base-url <https://...>] [--facial-enabled <true|false>]" >&2
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

read_facial_enabled() {
  local env_file="${1:-$ENV_FILE}" occurrences value
  occurrences="$(grep -c '^FACIAL_PROCESSING_ENABLED=' "$env_file" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração duplicada para FACIAL_PROCESSING_ENABLED"
  value="false"
  if [[ "$occurrences" -eq 1 ]]; then
    value="$(grep '^FACIAL_PROCESSING_ENABLED=' "$env_file")"
    value="${value#*=}"
  fi
  value="${value,,}"
  [[ "$value" == "true" || "$value" == "false" ]] || fail "FACIAL_PROCESSING_ENABLED deve ser true ou false"
  printf '%s\n' "$value"
}

set_facial_enabled() {
  local desired="$1" env_file="${2:-$ENV_FILE}"
  local current line temp_file replaced=0
  desired="${desired,,}"
  [[ "$desired" == "true" || "$desired" == "false" ]] || fail "estado facial solicitado deve ser true ou false"
  current="$(read_facial_enabled "$env_file")"
  if [[ "$current" == "$desired" ]]; then
    echo "FACIAL_PROCESSING_ENABLED já está persistido como $desired"
    return 0
  fi

  temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
  chmod 600 "$temp_file"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "FACIAL_PROCESSING_ENABLED="* ]]; then
      printf 'FACIAL_PROCESSING_ENABLED=%s\n' "$desired" >> "$temp_file"
      replaced=1
    else
      printf '%s\n' "$line" >> "$temp_file"
    fi
  done < "$env_file"
  if [[ "$replaced" -eq 0 ]]; then
    printf 'FACIAL_PROCESSING_ENABLED=%s\n' "$desired" >> "$temp_file"
  fi
  mv "$temp_file" "$env_file"
  chmod 600 "$env_file"
  echo "FACIAL_PROCESSING_ENABLED persistido como $desired em homologação"
}

verify_facial_deploy_state() {
  local env_file="${1:-$ENV_FILE}" expected service container status
  expected="$(read_facial_enabled "$env_file")"
  for service in "${FACIAL_SERVICES[@]}"; do
    # O script novo roda por stdin enquanto o checkout remoto ainda aponta para
    # a versão anterior. Consulte os labels Docker diretamente para que o
    # bootstrap não dependa de o Compose antigo já conhecer os serviços novos.
    container="$(
      docker ps --quiet \
        --filter "label=com.docker.compose.project=$PROJECT_NAME" \
        --filter "label=com.docker.compose.service=$service"
    )"
    if [[ "$expected" == "false" ]]; then
      [[ -z "$container" ]] || fail "$service deve permanecer ausente com flag=false"
      continue
    fi
    [[ -n "$container" ]] || fail "$service deve estar ativo com flag=true"
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] || fail "$service diverge do estado saudável esperado: $status"
  done
  if [[ "$expected" == "true" ]]; then
    for service in api worker "${FACIAL_SERVICES[@]}"; do
      compose exec -T "$service" python -c '
from app.facial.config import facial_settings_from_environment
assert facial_settings_from_environment(verify_runtime_assets=False).enabled
' || fail "$service diverge da configuração facial persistente"
    done
  fi
  echo "estado facial coerente confirmado: flag=$expected workers=$([[ "$expected" == "true" ]] && echo saudáveis || echo ausentes)"
}

ensure_pii_fingerprint_salt() {
  local env_file="${1:-$ENV_FILE}"
  local key="AUTH_PII_FINGERPRINT_SALT" line value occurrences salt temp_file replaced=0
  occurrences="$(grep -c "^${key}=" "$env_file" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração duplicada para $key"
  chmod 600 "$env_file"

  if [[ "$occurrences" -eq 1 ]]; then
    line="$(grep "^${key}=" "$env_file")"
    value="${line#*=}"
    if [[ -n "$value" ]]; then
      [[ "${#value}" -ge 32 ]] || fail "$key deve possuir ao menos 32 caracteres"
      return 0
    fi
  fi

  command -v openssl >/dev/null 2>&1 || fail "openssl é obrigatório para gerar $key"
  salt="$(openssl rand -hex 32)"
  [[ "${#salt}" -eq 64 ]] || fail "não foi possível gerar $key com entropia suficiente"
  temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
  chmod 600 "$temp_file"

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      printf '%s=%s\n' "$key" "$salt" >> "$temp_file"
      replaced=1
    else
      printf '%s\n' "$line" >> "$temp_file"
    fi
  done < "$env_file"
  if [[ "$replaced" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$salt" >> "$temp_file"
  fi
  mv "$temp_file" "$env_file"
  unset salt value line
  echo "$key configurado com segredo aleatório exclusivo de homologação"
}

ensure_gallery_capability_signing_key() {
  local env_file="${1:-$ENV_FILE}"
  local key="GALLERY_CAPABILITY_SIGNING_KEY"
  local fingerprint_key="AUTH_PII_FINGERPRINT_SALT"
  local line value occurrences signing_key temp_file replaced=0 fingerprint_value fingerprint_occurrences

  occurrences="$(grep -c "^${key}=" "$env_file" || true)"
  fingerprint_occurrences="$(grep -c "^${fingerprint_key}=" "$env_file" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração duplicada para $key"
  [[ "$fingerprint_occurrences" -eq 1 ]] || fail "$fingerprint_key deve estar configurado antes de $key"
  chmod 600 "$env_file"

  line="$(grep "^${fingerprint_key}=" "$env_file")"
  fingerprint_value="${line#*=}"
  [[ "${#fingerprint_value}" -ge 32 ]] || fail "$fingerprint_key deve possuir ao menos 32 caracteres"

  if [[ "$occurrences" -eq 1 ]]; then
    line="$(grep "^${key}=" "$env_file")"
    value="${line#*=}"
    if [[ -n "$value" ]]; then
      [[ "${#value}" -ge 32 ]] || fail "$key deve possuir ao menos 32 caracteres"
      [[ "$value" != "$fingerprint_value" ]] || fail "$key deve ser diferente de $fingerprint_key"
      unset value fingerprint_value line
      return 0
    fi
  fi

  command -v openssl >/dev/null 2>&1 || fail "openssl é obrigatório para gerar $key"
  signing_key="$(openssl rand -hex 32)"
  [[ "${#signing_key}" -eq 64 ]] || fail "não foi possível gerar $key com entropia suficiente"
  [[ "$signing_key" != "$fingerprint_value" ]] || fail "não foi possível gerar $key distinto de $fingerprint_key"
  temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
  chmod 600 "$temp_file"

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      printf '%s=%s\n' "$key" "$signing_key" >> "$temp_file"
      replaced=1
    else
      printf '%s\n' "$line" >> "$temp_file"
    fi
  done < "$env_file"
  if [[ "$replaced" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$signing_key" >> "$temp_file"
  fi
  mv "$temp_file" "$env_file"
  unset signing_key value fingerprint_value line
  echo "$key configurado com segredo aleatório exclusivo de homologação"
}

ensure_sensitive_payload_encryption_key() {
  local env_file="${1:-$ENV_FILE}"
  local key="EMAIL_PAYLOAD_ENCRYPTION_KEY" line value occurrences generated temp_file replaced=0
  occurrences="$(grep -c "^${key}=" "$env_file" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração duplicada para $key"
  chmod 600 "$env_file"

  if [[ "$occurrences" -eq 1 ]]; then
    line="$(grep "^${key}=" "$env_file")"
    value="${line#*=}"
    if [[ -n "$value" ]]; then
      PAYLOAD_KEY_VALUE="$value" python3 - <<'PY' || fail "$key deve codificar exatamente 32 bytes em base64 urlsafe"
import base64
import os

try:
    decoded = base64.urlsafe_b64decode(os.environ["PAYLOAD_KEY_VALUE"].encode("ascii"))
except (ValueError, UnicodeEncodeError):
    raise SystemExit(1)
raise SystemExit(0 if len(decoded) == 32 else 1)
PY
      unset value line
      return 0
    fi
  fi

  command -v openssl >/dev/null 2>&1 || fail "openssl é obrigatório para gerar $key"
  generated="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n\r')"
  [[ -n "$generated" ]] || fail "não foi possível gerar $key com entropia suficiente"
  PAYLOAD_KEY_VALUE="$generated" python3 - <<'PY' || fail "não foi possível validar $key gerada"
import base64
import os

decoded = base64.urlsafe_b64decode(os.environ["PAYLOAD_KEY_VALUE"].encode("ascii"))
raise SystemExit(0 if len(decoded) == 32 else 1)
PY
  temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
  chmod 600 "$temp_file"

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      printf '%s=%s\n' "$key" "$generated" >> "$temp_file"
      replaced=1
    else
      printf '%s\n' "$line" >> "$temp_file"
    fi
  done < "$env_file"
  if [[ "$replaced" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$generated" >> "$temp_file"
  fi
  mv "$temp_file" "$env_file"
  unset generated value line
  echo "$key configurada com segredo aleatório exclusivo de homologação"
}

ensure_public_app_origin() {
  local env_file="${1:-$ENV_FILE}"
  local public_url="${2:-$PUBLIC_BASE_URL}"
  local key="PUBLIC_APP_ORIGIN" normalized occurrences temp_file line replaced=0

  [[ -n "$public_url" ]] || fail "MARKINA_PUBLIC_BASE_URL é obrigatória para validar operações sensíveis"
  normalized="$({ PUBLIC_ORIGIN_VALUE="$public_url" python3 - <<'PY'
import os
from urllib.parse import urlsplit

raw = os.environ["PUBLIC_ORIGIN_VALUE"].strip()
parsed = urlsplit(raw)
if (
    parsed.scheme != "https"
    or not parsed.netloc
    or not parsed.hostname
    or parsed.username
    or parsed.password
    or parsed.query
    or parsed.fragment
    or parsed.path not in {"", "/"}
):
    raise SystemExit("origem pública inválida")
try:
    parsed.port
except ValueError as exc:
    raise SystemExit("porta da origem pública inválida") from exc
print(f"https://{parsed.netloc.rstrip('/')}".rstrip("/"))
PY
  } 2>/dev/null)" || fail "MARKINA_PUBLIC_BASE_URL não representa uma origem HTTPS válida"

  occurrences="$(grep -c "^${key}=" "$env_file" || true)"
  [[ "$occurrences" -le 1 ]] || fail "configuração duplicada para $key"
  temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
  chmod 600 "$temp_file"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      printf '%s=%s\n' "$key" "$normalized" >> "$temp_file"
      replaced=1
    else
      printf '%s\n' "$line" >> "$temp_file"
    fi
  done < "$env_file"
  if [[ "$replaced" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$normalized" >> "$temp_file"
  fi
  mv "$temp_file" "$env_file"
  chmod 600 "$env_file"
  echo "$key sincronizada com a origem pública autorizada de homologação"
}

record_predeploy_inventory() {
  echo "inventário Markina pré-deploy"
  df -hP "$PROJECT_ROOT"
  docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Names}} {{.Status}} {{.Ports}}'
  compose ps
  compose config --images
  docker volume ls --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Name}}'
  docker network ls --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Name}}'
  if command -v systemctl >/dev/null 2>&1; then
    systemctl list-units --type=service --all 'markina*' --no-legend --no-pager || true
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | awk 'NR == 1 || $4 ~ /(^|:)8080$/'
  fi
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
      --facial-enabled)
        REQUESTED_FACIAL_ENABLED="${2:-}"
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
  REQUESTED_FACIAL_ENABLED="${REQUESTED_FACIAL_ENABLED,,}"
  [[ -z "$REQUESTED_FACIAL_ENABLED" || "$REQUESTED_FACIAL_ENABLED" == "true" || "$REQUESTED_FACIAL_ENABLED" == "false" ]] || fail "--facial-enabled deve ser true ou false"
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
  PREVIOUS_FACIAL_ENABLED="$(read_facial_enabled)"
  FACIAL_DEPLOY_ENABLED="$PREVIOUS_FACIAL_ENABLED"
  verify_facial_deploy_state
  compose config --quiet
  record_predeploy_inventory
  ensure_pii_fingerprint_salt
  ensure_gallery_capability_signing_key
  ensure_sensitive_payload_encryption_key
  ensure_public_app_origin
  if [[ -n "$REQUESTED_FACIAL_ENABLED" ]]; then
    set_facial_enabled "$REQUESTED_FACIAL_ENABLED"
    FACIAL_DEPLOY_ENABLED="$REQUESTED_FACIAL_ENABLED"
    [[ "$FACIAL_DEPLOY_ENABLED" == "$PREVIOUS_FACIAL_ENABLED" ]] || FACIAL_ENV_CHANGED=1
  fi
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

report_container_state() {
  local service="$1" container="$2"
  [[ -n "$container" ]] || return 0
  docker inspect --format \
    'diagnóstico sanitizado: service='"$service"' status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} exit_code={{.State.ExitCode}} oom={{.State.OOMKilled}} restart_count={{.RestartCount}} state_error={{if .State.Error}}present{{else}}absent{{end}}' \
    "$container" || true
  docker logs --tail 80 "$container" 2>&1 \
    | sed -nE 's/^([A-Za-z_][A-Za-z0-9_.]*(Error|Exception)):.*/exception_class=\1/p' \
    | tail -n 5 \
    | while IFS= read -r exception_class; do
        printf 'diagnóstico sanitizado: service=%s %s\n' "$service" "$exception_class"
      done || true
}

wait_for_health() {
  local service container status attempt
  local services=(api web worker nginx)
  if [[ "$FACIAL_DEPLOY_ENABLED" == "true" ]]; then
    services+=("${FACIAL_SERVICES[@]}")
  fi
  for service in "${services[@]}"; do
    container="$(compose ps -q "$service")"
    [[ -n "$container" ]] || fail "serviço Markina ausente após deploy: $service"
    for attempt in $(seq 1 30); do
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
      [[ "$status" == "healthy" ]] && break
      sleep 2
    done
    if [[ "$status" != "healthy" ]]; then
      report_container_state "$service" "$container"
      fail "serviço Markina não ficou saudável: $service ($status)"
    fi
  done

  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
  if [[ -n "$PUBLIC_BASE_URL" ]]; then
    curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/healthz" >/dev/null
    curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_BASE_URL/api/health" >/dev/null
  fi
}

start_application_services() {
  compose up -d --build --no-deps api web worker
  if [[ "$FACIAL_DEPLOY_ENABLED" == "true" ]]; then
    compose up -d --build --no-deps "${FACIAL_SERVICES[@]}"
  fi
  compose up -d --force-recreate --no-deps nginx
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
  if [[ "$FACIAL_ENV_CHANGED" -eq 1 ]]; then
    set_facial_enabled "$PREVIOUS_FACIAL_ENABLED"
    FACIAL_DEPLOY_ENABLED="$PREVIOUS_FACIAL_ENABLED"
    if [[ "$SHA_SWITCHED" -eq 1 && "$PREVIOUS_FACIAL_ENABLED" == "false" ]]; then
      compose stop "${FACIAL_SERVICES[@]}" || true
    fi
  fi
  if [[ "$SHA_SWITCHED" -eq 1 && "$MIGRATION_CHANGED" -eq 0 && "$SCHEMA_ROLLBACK_UNSAFE" -eq 0 && -n "$PREVIOUS_SHA" ]]; then
    echo "falha antes de mudança de schema; restaurando somente código Markina para $PREVIOUS_SHA" >&2
    git switch --detach "$PREVIOUS_SHA"
    compose up -d --build --no-deps api web worker
    if [[ "$FACIAL_DEPLOY_ENABLED" == "true" ]]; then
      compose up -d --build --no-deps "${FACIAL_SERVICES[@]}"
    fi
    compose up -d --force-recreate --no-deps nginx
    verify_facial_deploy_state
    record_revision "last-rollback" "$PREVIOUS_SHA"
  else
    if [[ "$SHA_SWITCHED" -eq 1 && "$FACIAL_ENV_CHANGED" -eq 1 ]]; then
      compose up -d --build --no-deps api worker
      if [[ "$FACIAL_DEPLOY_ENABLED" == "true" ]]; then
        compose up -d --build --no-deps "${FACIAL_SERVICES[@]}"
      fi
      verify_facial_deploy_state
    fi
    echo "rollback automático de código não é seguro após mudança de schema; banco não foi restaurado" >&2
  fi
  exit "$exit_code"
}

main() {
  parse_arguments "$@"
  trap 'rollback_code_if_safe $?' ERR
  verify_target

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
  start_application_services
  wait_for_health
  verify_facial_deploy_state
  record_revision "last-healthy" "$DEPLOY_SHA"
  echo "deploy-homolog concluído para $DEPLOY_SHA"
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
  main "$@"
fi
