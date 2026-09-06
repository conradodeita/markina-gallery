#!/usr/bin/env bash
# Operação explícita do piloto facial sintético da Markina Gallery em homologação.
# Este script nunca aceita outro projeto, não publica portas e não toca em recursos de terceiros.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:?MARKINA_EXPECTED_REPOSITORY é obrigatório}"

MODE=""
CONFIRMATION=""
EXPECTED_SHA=""
ENV_BACKUP=""
ACTIVATION_STARTED=0
PAUSE_STARTED=0

usage() {
  echo "Uso: manage-homolog-facial.sh --mode inventory|pause-synthetic|activate-synthetic [--confirmation <token>] [--sha <sha-completo>]" >&2
}

fail() {
  echo "manage-homolog-facial: $*" >&2
  return 1
}

compose() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

compose_facial() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile facial "$@"
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        MODE="${2:-}"
        shift 2
        ;;
      --confirmation)
        CONFIRMATION="${2:-}"
        shift 2
        ;;
      --sha)
        EXPECTED_SHA="${2:-}"
        shift 2
        ;;
      *)
        usage
        fail "argumento não permitido: $1"
        ;;
    esac
  done

  [[ "$MODE" == "inventory" || "$MODE" == "pause-synthetic" || "$MODE" == "activate-synthetic" ]] || {
    usage
    fail "modo não permitido"
  }
  if [[ -n "$EXPECTED_SHA" ]]; then
    [[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "o SHA deve ter 40 caracteres hexadecimais minúsculos"
  fi
}

set_facial_enabled() {
  local enabled="$1" temp_file
  [[ "$enabled" == "true" || "$enabled" == "false" ]] || fail "valor facial inválido"
  temp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  chmod 600 "$temp_file"
  FACIAL_ENABLED_VALUE="$enabled" python3 - "$ENV_FILE" "$temp_file" <<'PY'
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
key = "FACIAL_PROCESSING_ENABLED"
lines = source.read_text(encoding="utf-8").splitlines()
output = []
seen = False
for line in lines:
    if line.startswith(f"{key}="):
        if not seen:
            output.append(f"{key}={os.environ['FACIAL_ENABLED_VALUE']}")
            seen = True
        continue
    output.append(line)
if not seen:
    output.append(f"{key}={os.environ['FACIAL_ENABLED_VALUE']}")
target.write_text("\n".join(output) + "\n", encoding="utf-8")
PY
  mv "$temp_file" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

verify_target() {
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "a operação só pode executar em $PROJECT_ROOT"
  [[ -f "$COMPOSE_FILE" ]] || fail "arquivo Compose esperado não encontrado"
  [[ -f "$ENV_FILE" ]] || fail "arquivo de ambiente de homologação não encontrado"
  [[ "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail "o diretório não é o checkout esperado"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout remoto possui alterações locais; reconciliação humana necessária"

  local origin_url current_sha
  origin_url="$(git remote get-url origin)"
  [[ "$origin_url" =~ github\.com[:/]${EXPECTED_REPOSITORY//\//\/}(\.git)?$ ]] || fail "origin não aponta para o repositório GitHub esperado"
  current_sha="$(git rev-parse HEAD)"
  if [[ -n "$EXPECTED_SHA" && "$current_sha" != "$EXPECTED_SHA" ]]; then
    fail "o SHA publicado diverge do SHA autorizado"
  fi

  mkdir -p "$STATE_DIR"
  chmod 600 "$ENV_FILE"
  compose config --quiet
}

facial_container_id() {
  docker ps --quiet \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --filter "label=com.docker.compose.service=face-worker"
}

record_inventory() {
  local face_container
  echo "inventário facial Markina"
  printf 'sha=%s\n' "$(git rev-parse HEAD)"
  printf 'architecture=%s cpus=%s\n' "$(uname -m)" "$(nproc)"
  awk '/MemTotal/ {printf "memory_kib=%s\n", $2}' /proc/meminfo
  df -hP "$PROJECT_ROOT"
  compose ps
  echo "portas publicadas do projeto Markina"
  docker ps \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --format '{{.Names}} {{.Ports}}'
  face_container="$(facial_container_id)"
  printf 'face_worker=%s\n' "$([[ -n "$face_container" ]] && printf ativo || printf inativo)"
  compose run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r' | tail -n 1
  compose exec -T api python -c '
import json
import os

keys = (
    "FACIAL_CALIBRATION_VERSION",
    "FACIAL_LEGAL_NOTICE_VERSION",
    "FACIAL_CONSENT_VERSION",
    "FACIAL_LEGAL_BASIS_REFERENCE",
    "FACIAL_RETENTION_POLICY_VERSION",
    "FACIAL_MINOR_POLICY_VERSION",
    "FACIAL_AEAD_ACTIVE_KEY_ID",
    "FACIAL_AEAD_KEYS_JSON",
)
print(json.dumps({
    "environment": os.getenv("APP_ENV", ""),
    "facial_enabled": os.getenv("FACIAL_PROCESSING_ENABLED", "false").lower() == "true",
    "minor_search_enabled": os.getenv("FACIAL_MINOR_SEARCH_ENABLED", "false").lower() == "true",
    "required_configuration_present": {key: bool(os.getenv(key, "")) for key in keys},
}, sort_keys=True))
'
}

write_synthetic_configuration() {
  local timestamp temp_file result target_environment
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  ENV_BACKUP="$STATE_DIR/facial-env-preactivate-${timestamp}.backup"
  cp --preserve=mode "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  temp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  chmod 600 "$temp_file"

  target_environment="$(grep '^APP_ENV=' "$ENV_FILE" | tail -n 1)"
  target_environment="${target_environment#*=}"
  [[ "$target_environment" == "homolog" || "$target_environment" == "staging" ]] || {
    rm -f "$temp_file"
    fail "APP_ENV não identifica o ambiente de homologação esperado"
    return 1
  }

  if ! result="$(FACIAL_TARGET_ENV="$target_environment" python3 - "$ENV_FILE" "$temp_file" <<'PY'
import base64
import json
import os
import secrets
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
lines = source.read_text(encoding="utf-8").splitlines()
values = {}
for line in lines:
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key] = value

key_id = values.get("FACIAL_AEAD_ACTIVE_KEY_ID") or "homolog-synthetic-v1"
keyring_raw = values.get("FACIAL_AEAD_KEYS_JSON", "")
keyring = {}
preserved = False
try:
    candidate = json.loads(keyring_raw) if keyring_raw else {}
    encoded = candidate.get(key_id, "") if isinstance(candidate, dict) else ""
    if len(base64.b64decode(encoded, altchars=b"-_", validate=True)) == 32:
        keyring = candidate
        preserved = True
except (ValueError, TypeError, json.JSONDecodeError):
    pass
if not preserved:
    keyring = {key_id: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")}

updates = {
    "FACIAL_PROCESSING_ENABLED": "true",
    "FACIAL_CREDENTIAL_ENV": os.environ["FACIAL_TARGET_ENV"],
    "FACIAL_MODEL_VERSION": "yunet-2023mar+sface-2021dec",
    "FACIAL_QUALITY_VERSION": "opencv-technical-v1",
    "FACIAL_CALIBRATION_VERSION": "homolog-synthetic-threshold-750-v1",
    "FACIAL_LEGAL_NOTICE_VERSION": "homolog-synthetic-adult-notice-v1",
    "FACIAL_CONSENT_VERSION": "homolog-synthetic-adult-consent-v1",
    "FACIAL_LEGAL_BASIS_REFERENCE": "homolog-synthetic-only-no-real-data-v1",
    "FACIAL_RETENTION_POLICY_VERSION": "homolog-reference-15m-candidates-24h-v1",
    "FACIAL_MINOR_POLICY_VERSION": "homolog-minors-blocked-v1",
    "FACIAL_MINOR_SEARCH_ENABLED": "false",
    "FACIAL_SIMILARITY_THRESHOLD_MILLI": "750",
    "FACIAL_AEAD_ACTIVE_KEY_ID": key_id,
    "FACIAL_AEAD_KEYS_JSON": json.dumps(keyring, separators=(",", ":")),
    "FACIAL_WORKER_CONCURRENCY": "1",
    "FACIAL_WORKER_MEMORY_LIMIT": "768m",
    "FACIAL_WORKER_CPU_LIMIT": "1.0",
}

seen = set()
output = []
for line in lines:
    if line and not line.startswith("#") and "=" in line:
        key = line.split("=", 1)[0]
        if key in updates:
            if key not in seen:
                output.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
    output.append(line)
for key, value in updates.items():
    if key not in seen:
        output.append(f"{key}={value}")
target.write_text("\n".join(output) + "\n", encoding="utf-8")
print("preservada" if preserved else "gerada")
PY
)"; then
    rm -f "$temp_file"
    fail "não foi possível gravar a configuração facial sintética"
    return 1
  fi
  mv "$temp_file" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "configuração facial sintética gravada; chave AEAD $result no próprio host"
}

wait_for_service() {
  local service="$1" container status="unknown" attempt
  container="$(compose_facial ps -q "$service")"
  [[ -n "$container" ]] || fail "serviço Markina ausente após ativação: $service"
  for attempt in $(seq 1 45); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  if [[ "$status" != "healthy" ]]; then
    if [[ "$service" == "face-worker" ]]; then
      compose_facial logs --no-color --tail 80 face-worker >&2 || true
    fi
    fail "serviço Markina não ficou saudável: $service ($status)"
    return 1
  fi
}

verify_activation() {
  local face_container unexpected_ports
  wait_for_service api
  wait_for_service face-worker
  compose exec -T api python -c '
from app.facial.config import facial_settings_from_environment

settings = facial_settings_from_environment(verify_runtime_assets=False)
assert settings.enabled
assert settings.environment in {"homolog", "staging"}
assert settings.credential_environment == settings.environment
assert not settings.minor_search_enabled
assert settings.worker_concurrency == 1
print("configuração facial fail-closed validada na API")
'
  face_container="$(facial_container_id)"
  [[ -n "$face_container" ]] || fail "face-worker não está ativo"
  unexpected_ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$face_container")"
  [[ "$unexpected_ports" == "{}" || "$unexpected_ports" == "null" ]] || fail "face-worker publicou porta inesperada"
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
  echo "piloto facial sintético ativo: menores=false concorrência=1 cpu=1 memória=768m portas=0"
}

rollback_activation() {
  local exit_code="$1"
  trap - ERR
  if [[ "$ACTIVATION_STARTED" -eq 1 && -n "$ENV_BACKUP" && -f "$ENV_BACKUP" ]]; then
    echo "falha na ativação; restaurando somente a configuração facial da Markina" >&2
    cp --preserve=mode "$ENV_BACKUP" "$ENV_FILE"
    compose_facial stop face-worker >/dev/null 2>&1 || true
    compose up -d --no-deps --force-recreate api >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}

rollback_pause() {
  local exit_code="$1"
  trap - ERR
  if [[ "$PAUSE_STARTED" -eq 1 && -n "$ENV_BACKUP" && -f "$ENV_BACKUP" ]]; then
    echo "falha ao pausar; restaurando somente o piloto facial da Markina" >&2
    cp --preserve=mode "$ENV_BACKUP" "$ENV_FILE"
    compose_facial up -d --no-deps face-worker >/dev/null 2>&1 || true
    compose up -d --no-deps --force-recreate api >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}

pause_synthetic() {
  local timestamp enabled face_container
  [[ "$CONFIRMATION" == "PAUSE_SYNTHETIC_FACIAL_FOR_DEPLOY" ]] || fail "confirmação explícita da pausa sintética ausente"
  enabled="$(grep '^FACIAL_PROCESSING_ENABLED=' "$ENV_FILE" | tail -n 1)"
  enabled="${enabled#*=}"
  [[ "${enabled,,}" == "true" ]] || fail "piloto facial sintético não está ativo"
  face_container="$(facial_container_id)"
  [[ -n "$face_container" ]] || fail "face-worker ativo não foi encontrado"

  record_inventory
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  ENV_BACKUP="$STATE_DIR/facial-env-preupgrade-${timestamp}.backup"
  cp --preserve=mode "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  PAUSE_STARTED=1
  set_facial_enabled false
  compose_facial stop face-worker
  compose up -d --no-deps --force-recreate api
  wait_for_service api
  compose exec -T api python -c '
import os
import sys
sys.exit(0 if os.getenv("FACIAL_PROCESSING_ENABLED", "false").lower() == "false" else 1)
' || fail "API não confirmou a pausa facial"
  [[ -z "$(facial_container_id)" ]] || fail "face-worker permaneceu ativo após pausa"
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "paused-synthetic-for-deploy" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
  echo "piloto facial sintético pausado com backup restrito para upgrade"
}

activate_synthetic() {
  [[ "$CONFIRMATION" == "ENABLE_SYNTHETIC_ADULT_FACIAL_HOMOLOG" ]] || fail "confirmação explícita da ativação sintética ausente"
  [[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]] || fail "o host de homologação não é ARM64"
  [[ -z "$(facial_container_id)" ]] || fail "face-worker já está ativo; use inventário antes de nova operação"

  record_inventory
  write_synthetic_configuration
  ACTIVATION_STARTED=1
  compose_facial up -d --build --no-deps face-worker
  compose up -d --no-deps --force-recreate api
  verify_activation
  record_inventory
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "activated-synthetic-adults" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
}

main() {
  parse_arguments "$@"
  verify_target
  case "$MODE" in
    inventory)
      record_inventory
      ;;
    pause-synthetic)
      trap 'rollback_pause $?' ERR
      pause_synthetic
      ;;
    activate-synthetic)
      trap 'rollback_activation $?' ERR
      activate_synthetic
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
  main "$@"
fi
