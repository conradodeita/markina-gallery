#!/usr/bin/env bash
# Opera uma janela facial privada, autorizada e vinculada a lote em homologação.
# Nunca publica portas, não toca em outro projeto e não registra PII ou biometria.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:?MARKINA_EXPECTED_REPOSITORY é obrigatório}"
readonly ACTIVATE_TOKEN="ENABLE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"
readonly PAUSE_TOKEN="PAUSE_AUTHORIZED_PRIVATE_FACIAL_FOR_DEPLOY"
readonly LEGACY_PAUSE_TOKEN="PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE"
readonly CLOSE_TOKEN="CLOSE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"
readonly RECONCILE_TOKEN="RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"

MODE=""
CONFIRMATION=""
EXPECTED_SHA=""
BATCH_ID=""
ORIGIN_REF=""
AUTHORIZATION_REF=""
OPERATOR_REF=""
EXPECTED_COUNT=""
RETENTION_HOURS=""
WINDOW_MINUTES=""
CONTAINS_MINORS=""
WINDOW_EXPIRES_AT=""
ENV_BACKUP=""
ACTIVATION_STARTED=0
PAUSE_STARTED=0

usage() {
  echo "Uso: manage-homolog-facial.sh --mode inventory|pause-legacy-for-private-upgrade|pause-private|activate-private|reconcile-private|close-private [--confirmation <token>] [--sha <sha>] [--batch-id <ref>] [--origin-ref <ref>] [--authorization-ref <ref>] [--operator-ref <ref>] [--expected-count 500..1000] [--retention-hours 1..72] [--window-minutes 30..240] [--contains-minors true|false]" >&2
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
      --mode) MODE="${2:-}"; shift 2 ;;
      --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
      --sha) EXPECTED_SHA="${2:-}"; shift 2 ;;
      --batch-id) BATCH_ID="${2:-}"; shift 2 ;;
      --origin-ref) ORIGIN_REF="${2:-}"; shift 2 ;;
      --authorization-ref) AUTHORIZATION_REF="${2:-}"; shift 2 ;;
      --operator-ref) OPERATOR_REF="${2:-}"; shift 2 ;;
      --expected-count) EXPECTED_COUNT="${2:-}"; shift 2 ;;
      --retention-hours) RETENTION_HOURS="${2:-}"; shift 2 ;;
      --window-minutes) WINDOW_MINUTES="${2:-}"; shift 2 ;;
      --contains-minors) CONTAINS_MINORS="${2:-}"; shift 2 ;;
      *) usage; fail "argumento não permitido: $1"; return 1 ;;
    esac
  done
  [[ "$MODE" == "inventory" || "$MODE" == "pause-legacy-for-private-upgrade" || "$MODE" == "pause-private" || "$MODE" == "activate-private" || "$MODE" == "reconcile-private" || "$MODE" == "close-private" ]] || {
    usage
    fail "modo não permitido"
    return 1
  }
  [[ -z "$EXPECTED_SHA" || "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || {
    fail "o SHA deve ter 40 caracteres hexadecimais minúsculos"
    return 1
  }
}

validate_reference() {
  local value="$1" label="$2"
  [[ "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$ ]] || {
    fail "$label deve ser uma referência opaca de 3 a 128 caracteres, sem PII"
    return 1
  }
}

validate_activation_arguments() {
  validate_reference "$BATCH_ID" "batch-id" || return 1
  validate_reference "$ORIGIN_REF" "origin-ref" || return 1
  validate_reference "$AUTHORIZATION_REF" "authorization-ref" || return 1
  validate_reference "$OPERATOR_REF" "operator-ref" || return 1
  [[ "$EXPECTED_COUNT" =~ ^[0-9]+$ ]] && (( EXPECTED_COUNT >= 500 && EXPECTED_COUNT <= 1000 )) || {
    fail "expected-count deve ficar entre 500 e 1000"
    return 1
  }
  [[ "$RETENTION_HOURS" =~ ^[0-9]+$ ]] && (( RETENTION_HOURS >= 1 && RETENTION_HOURS <= 72 )) || {
    fail "retention-hours deve ficar entre 1 e 72"
    return 1
  }
  [[ "$WINDOW_MINUTES" =~ ^[0-9]+$ ]] && (( WINDOW_MINUTES >= 30 && WINDOW_MINUTES <= 240 )) || {
    fail "window-minutes deve ficar entre 30 e 240"
    return 1
  }
  [[ "$CONTAINS_MINORS" == "true" || "$CONTAINS_MINORS" == "false" ]] || {
    fail "contains-minors deve ser true ou false"
    return 1
  }
}

verify_target() {
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "a operação só pode executar em $PROJECT_ROOT"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "Compose ou ambiente de homologação ausente"
  [[ "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail "o diretório não é o checkout esperado"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout remoto possui alterações locais; reconciliação humana necessária"
  local origin_url current_sha
  origin_url="$(git remote get-url origin)"
  [[ "$origin_url" =~ github\.com[:/]${EXPECTED_REPOSITORY//\//\/}(\.git)?$ ]] || fail "origin não aponta para o repositório GitHub esperado"
  current_sha="$(git rev-parse HEAD)"
  [[ -z "$EXPECTED_SHA" || "$current_sha" == "$EXPECTED_SHA" ]] || fail "o SHA publicado diverge do SHA autorizado"
  mkdir -p "$STATE_DIR"
  chmod 600 "$ENV_FILE"
  compose config --quiet
}

facial_container_id() {
  docker ps --quiet --filter "label=com.docker.compose.project=$PROJECT_NAME" --filter "label=com.docker.compose.service=face-worker"
}

read_env_value() {
  local key="$1" line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  printf '%s' "${line#*=}"
}

record_inventory() {
  local face_container
  echo "inventário facial privado Markina"
  printf 'sha=%s\n' "$(git rev-parse HEAD)"
  printf 'architecture=%s cpus=%s\n' "$(uname -m)" "$(nproc)"
  awk '/MemTotal/ {printf "memory_kib=%s\n", $2}' /proc/meminfo
  df -hP "$PROJECT_ROOT"
  compose ps
  echo "portas publicadas do projeto Markina"
  docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Names}} {{.Ports}}'
  face_container="$(facial_container_id)"
  printf 'face_worker=%s\n' "$([[ -n "$face_container" ]] && printf ativo || printf inativo)"
  printf 'private_mode=%s batch_id=%s contains_minors=%s expires_at=%s\n' \
    "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" "$(read_env_value FACIAL_HOMOLOG_BATCH_ID)" \
    "$(read_env_value FACIAL_HOMOLOG_CONTAINS_MINORS)" "$(read_env_value FACIAL_HOMOLOG_WINDOW_EXPIRES_AT)"
  compose run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r' | tail -n 1
}

write_environment() {
  local operation="$1" timestamp temp_file
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  ENV_BACKUP="$STATE_DIR/facial-env-pre${operation}-${timestamp}.backup"
  cp --preserve=mode "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  temp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  chmod 600 "$temp_file"
  FACIAL_OPERATION="$operation" FACIAL_BATCH_ID="$BATCH_ID" FACIAL_ORIGIN_REF="$ORIGIN_REF" \
  FACIAL_AUTHORIZATION_REF="$AUTHORIZATION_REF" FACIAL_OPERATOR_REF="$OPERATOR_REF" \
  FACIAL_EXPECTED_COUNT="$EXPECTED_COUNT" FACIAL_RETENTION_HOURS="$RETENTION_HOURS" \
  FACIAL_WINDOW_MINUTES="$WINDOW_MINUTES" FACIAL_CONTAINS_MINORS="$CONTAINS_MINORS" \
    python3 - "$ENV_FILE" "$temp_file" <<'PY'
import base64
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

source, target = map(Path, sys.argv[1:])
lines = source.read_text(encoding="utf-8").splitlines()
values = {}
for line in lines:
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key] = value
environment = values.get("APP_ENV", "")
if environment not in {"homolog", "staging"}:
    raise SystemExit("APP_ENV não identifica homologação")

operation = os.environ["FACIAL_OPERATION"]
if operation == "activate":
    key_id = values.get("FACIAL_AEAD_ACTIVE_KEY_ID") or "homolog-private-v1"
    try:
        keyring = json.loads(values.get("FACIAL_AEAD_KEYS_JSON", "{}"))
        encoded = keyring.get(key_id, "") if isinstance(keyring, dict) else ""
        if len(base64.b64decode(encoded, altchars=b"-_", validate=True)) != 32:
            raise ValueError
    except (ValueError, TypeError, json.JSONDecodeError):
        keyring = {key_id: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")}
    expiry = datetime.now(timezone.utc) + timedelta(minutes=int(os.environ["FACIAL_WINDOW_MINUTES"]))
    contains_minors = os.environ["FACIAL_CONTAINS_MINORS"]
    updates = {
        "FACIAL_PROCESSING_ENABLED": "true",
        "FACIAL_CREDENTIAL_ENV": environment,
        "FACIAL_MODEL_VERSION": "yunet-2023mar+sface-2021dec",
        "FACIAL_QUALITY_VERSION": "opencv-technical-v1",
        "FACIAL_CALIBRATION_VERSION": "homolog-private-threshold-750-v1",
        "FACIAL_LEGAL_NOTICE_VERSION": "homolog-private-authorized-v1",
        "FACIAL_CONSENT_VERSION": "homolog-private-authorized-v1",
        "FACIAL_LEGAL_BASIS_REFERENCE": os.environ["FACIAL_AUTHORIZATION_REF"],
        "FACIAL_RETENTION_POLICY_VERSION": f"homolog-private-{os.environ['FACIAL_RETENTION_HOURS']}h-v1",
        "FACIAL_MINOR_POLICY_VERSION": "homolog-private-minors-authorized-v1" if contains_minors == "true" else "homolog-private-adults-v1",
        "FACIAL_MINOR_SEARCH_ENABLED": contains_minors,
        "FACIAL_HOMOLOG_PRIVATE_MODE": "true",
        "FACIAL_HOMOLOG_BATCH_ID": os.environ["FACIAL_BATCH_ID"],
        "FACIAL_HOMOLOG_ORIGIN_REF": os.environ["FACIAL_ORIGIN_REF"],
        "FACIAL_HOMOLOG_AUTHORIZATION_REF": os.environ["FACIAL_AUTHORIZATION_REF"],
        "FACIAL_HOMOLOG_OPERATOR_REF": os.environ["FACIAL_OPERATOR_REF"],
        "FACIAL_HOMOLOG_EXPECTED_COUNT": os.environ["FACIAL_EXPECTED_COUNT"],
        "FACIAL_HOMOLOG_RETENTION_HOURS": os.environ["FACIAL_RETENTION_HOURS"],
        "FACIAL_HOMOLOG_CONTAINS_MINORS": contains_minors,
        "FACIAL_HOMOLOG_WINDOW_EXPIRES_AT": expiry.isoformat(),
        "FACIAL_SIMILARITY_THRESHOLD_MILLI": "750",
        "FACIAL_AEAD_ACTIVE_KEY_ID": key_id,
        "FACIAL_AEAD_KEYS_JSON": json.dumps(keyring, separators=(",", ":")),
        "FACIAL_WORKER_CONCURRENCY": "1",
        "FACIAL_WORKER_MEMORY_LIMIT": "768m",
        "FACIAL_WORKER_CPU_LIMIT": "1.0",
    }
else:
    updates = {
        "FACIAL_PROCESSING_ENABLED": "false",
        "FACIAL_MINOR_SEARCH_ENABLED": "false",
        "FACIAL_HOMOLOG_PRIVATE_MODE": "false",
        "FACIAL_HOMOLOG_BATCH_ID": "",
        "FACIAL_HOMOLOG_ORIGIN_REF": "",
        "FACIAL_HOMOLOG_AUTHORIZATION_REF": "",
        "FACIAL_HOMOLOG_OPERATOR_REF": "",
        "FACIAL_HOMOLOG_EXPECTED_COUNT": "0",
        "FACIAL_HOMOLOG_RETENTION_HOURS": "0",
        "FACIAL_HOMOLOG_CONTAINS_MINORS": "false",
        "FACIAL_HOMOLOG_WINDOW_EXPIRES_AT": "",
    }

seen, output = set(), []
for line in lines:
    key = line.split("=", 1)[0] if line and not line.startswith("#") and "=" in line else None
    if key in updates:
        if key not in seen:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
    else:
        output.append(line)
for key, value in updates.items():
    if key not in seen:
        output.append(f"{key}={value}")
target.write_text("\n".join(output) + "\n", encoding="utf-8")
PY
  mv "$temp_file" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

write_manifest() {
  local status="$1"
  FACIAL_MANIFEST_STATUS="$status" FACIAL_STATE_DIR="$STATE_DIR" FACIAL_BATCH_ID="$BATCH_ID" \
  FACIAL_ORIGIN_REF="$ORIGIN_REF" FACIAL_AUTHORIZATION_REF="$AUTHORIZATION_REF" \
  FACIAL_OPERATOR_REF="$OPERATOR_REF" FACIAL_EXPECTED_COUNT="$EXPECTED_COUNT" \
  FACIAL_RETENTION_HOURS="$RETENTION_HOURS" FACIAL_CONTAINS_MINORS="$CONTAINS_MINORS" \
  FACIAL_EXPIRES_AT="${WINDOW_EXPIRES_AT:-$(read_env_value FACIAL_HOMOLOG_WINDOW_EXPIRES_AT)}" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

batch = os.environ["FACIAL_BATCH_ID"]
path = Path(os.environ["FACIAL_STATE_DIR"]) / f"facial-batch-{batch}.json"
payload = {
    "batch_id": batch,
    "origin_ref": os.environ["FACIAL_ORIGIN_REF"],
    "authorization_ref": os.environ["FACIAL_AUTHORIZATION_REF"],
    "operator_ref": os.environ["FACIAL_OPERATOR_REF"],
    "purpose": "facial-performance-homologation",
    "expected_count": int(os.environ["FACIAL_EXPECTED_COUNT"]),
    "retention_hours": int(os.environ["FACIAL_RETENTION_HOURS"]),
    "contains_minors": os.environ["FACIAL_CONTAINS_MINORS"] == "true",
    "window_expires_at": os.environ["FACIAL_EXPIRES_AT"],
    "status": os.environ["FACIAL_MANIFEST_STATUS"],
    "recorded_at": datetime.now(timezone.utc).isoformat(),
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
path.chmod(0o600)
PY
}

wait_for_service() {
  local service="$1" container status="unknown" attempt
  container="$(compose_facial ps -q "$service")"
  [[ -n "$container" ]] || fail "serviço Markina ausente: $service"
  for attempt in $(seq 1 45); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || { compose_facial logs --no-color --tail 80 "$service" >&2 || true; fail "serviço não ficou saudável: $service ($status)"; }
}

wait_for_media_worker_idle() {
  local processing="1" attempt
  for attempt in $(seq 1 120); do
    processing="$(compose exec -T api python -c '
from sqlalchemy import func, select
from app.auth import MediaJob, SessionLocal
with SessionLocal() as db:
    print(db.scalar(select(func.count(MediaJob.id)).where(MediaJob.status == "processing")) or 0)
')"
    [[ "$processing" == "0" ]] && return 0
    sleep 2
  done
  fail "worker de mídia não ficou ocioso; nenhum processo foi recriado"
}

verify_persistent_gate() {
  local expected="$1" service
  for service in api worker; do
    wait_for_service "$service"
    FACIAL_EXPECTED_GATE="$expected" compose exec -T -e FACIAL_EXPECTED_GATE "$service" python -c '
import os
from app.facial.config import facial_settings_from_environment
s = facial_settings_from_environment(verify_runtime_assets=False)
assert s.enabled == (os.environ["FACIAL_EXPECTED_GATE"] == "true")
print("gate facial validado no processo persistente")'
  done
}

reload_reverse_proxy() {
  wait_for_service nginx
  compose exec -T nginx nginx -t
  compose exec -T nginx nginx -s reload
}

verify_activation() {
  verify_persistent_gate true
  wait_for_service face-worker
  FACIAL_EXPECTED_BATCH="$BATCH_ID" FACIAL_EXPECTED_MINORS="$CONTAINS_MINORS" compose exec -T \
    -e FACIAL_EXPECTED_BATCH -e FACIAL_EXPECTED_MINORS api python -c '
import os
from app.facial.config import facial_settings_from_environment
s = facial_settings_from_environment(verify_runtime_assets=False)
assert s.enabled and s.private_homologation_active
assert s.homolog_batch_id == os.environ["FACIAL_EXPECTED_BATCH"]
assert s.minor_search_enabled == (os.environ["FACIAL_EXPECTED_MINORS"] == "true")
assert s.worker_concurrency == 1
print("gate privado vinculado ao lote validado")'
  local ports
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$(facial_container_id)")"
  [[ "$ports" == "{}" || "$ports" == "null" ]] || fail "face-worker publicou porta inesperada"
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
}

rollback_activation() {
  local exit_code="$1"
  trap - ERR
  if [[ "$ACTIVATION_STARTED" -eq 1 && -f "$ENV_BACKUP" ]]; then
    cp --preserve=mode "$ENV_BACKUP" "$ENV_FILE"
    compose_facial stop face-worker >/dev/null 2>&1 || true
    compose up -d --no-deps --force-recreate api worker >/dev/null 2>&1 || true
    reload_reverse_proxy >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}

rollback_pause() {
  local exit_code="$1"
  trap - ERR
  if [[ "$PAUSE_STARTED" -eq 1 && -f "$ENV_BACKUP" ]]; then
    cp --preserve=mode "$ENV_BACKUP" "$ENV_FILE"
    compose_facial up -d --no-deps face-worker >/dev/null 2>&1 || true
    compose up -d --no-deps --force-recreate api worker >/dev/null 2>&1 || true
    reload_reverse_proxy >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}

pause_active_worker() {
  local history_event="$1"
  record_inventory
  local timestamp temp_file
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  ENV_BACKUP="$STATE_DIR/facial-env-preupgrade-${timestamp}.backup"
  cp --preserve=mode "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  wait_for_media_worker_idle
  temp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  PAUSE_STARTED=1
  python3 - "$ENV_FILE" "$temp_file" <<'PY'
import sys
from pathlib import Path
p, t = map(Path, sys.argv[1:])
lines = p.read_text(encoding="utf-8").splitlines()
out = ["FACIAL_PROCESSING_ENABLED=false" if line.startswith("FACIAL_PROCESSING_ENABLED=") else line for line in lines]
t.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
  mv "$temp_file" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  compose_facial stop face-worker
  compose up -d --no-deps --force-recreate api worker
  verify_persistent_gate false
  reload_reverse_proxy
  [[ -z "$(facial_container_id)" ]] || fail "face-worker permaneceu ativo após pausa"
  compose exec -T api python -c 'import os; assert os.getenv("FACIAL_PROCESSING_ENABLED", "false").lower() == "false"'
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$history_event" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
}

pause_legacy_for_private_upgrade() {
  local facial_enabled
  [[ "$CONFIRMATION" == "$LEGACY_PAUSE_TOKEN" ]] || {
    fail "confirmação explícita da transição facial legada ausente"
    return 1
  }
  [[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" != "true" ]] || {
    fail "a transição legada recusa uma janela facial privada ativa"
    return 1
  }
  facial_enabled="$(read_env_value FACIAL_PROCESSING_ENABLED)"
  [[ "${facial_enabled,,}" == "true" ]] || {
    fail "o piloto facial legado não está ativo"
    return 1
  }
  [[ -n "$(facial_container_id)" ]] || {
    fail "face-worker legado ativo não foi encontrado"
    return 1
  }
  pause_active_worker "paused-legacy-for-private-upgrade" || return 1
}

pause_private() {
  local facial_enabled
  [[ "$CONFIRMATION" == "$PAUSE_TOKEN" ]] || {
    fail "confirmação explícita da pausa privada ausente"
    return 1
  }
  [[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" == "true" ]] || {
    fail "janela facial privada não está ativa"
    return 1
  }
  facial_enabled="$(read_env_value FACIAL_PROCESSING_ENABLED)"
  [[ "${facial_enabled,,}" == "true" ]] || {
    fail "janela facial privada não está processando"
    return 1
  }
  [[ -n "$(facial_container_id)" ]] || {
    fail "face-worker privado ativo não foi encontrado"
    return 1
  }
  pause_active_worker "paused-private-for-deploy" || return 1
}

activate_private() {
  [[ "$CONFIRMATION" == "$ACTIVATE_TOKEN" ]] || fail "confirmação explícita da ativação privada ausente"
  validate_activation_arguments
  [[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]] || fail "o host de homologação não é ARM64"
  [[ -z "$(facial_container_id)" ]] || fail "face-worker já está ativo"
  [[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" != "true" ]] || fail "já existe lote privado ativo"
  record_inventory
  wait_for_media_worker_idle
  write_environment activate
  ACTIVATION_STARTED=1
  WINDOW_EXPIRES_AT="$(read_env_value FACIAL_HOMOLOG_WINDOW_EXPIRES_AT)"
  write_manifest active
  compose_facial up -d --build --no-deps face-worker
  compose up -d --no-deps --force-recreate api worker
  reload_reverse_proxy
  verify_activation
  record_inventory
  printf '%s activated-private batch=%s sha=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BATCH_ID" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
}

reconcile_private() {
  [[ "$CONFIRMATION" == "$RECONCILE_TOKEN" ]] || { fail "confirmação explícita da reconciliação privada ausente"; return 1; }
  validate_reference "$BATCH_ID" "batch-id" || return 1
  validate_reference "$AUTHORIZATION_REF" "authorization-ref" || return 1
  [[ "$EXPECTED_COUNT" =~ ^[0-9]+$ ]] && (( EXPECTED_COUNT >= 500 && EXPECTED_COUNT <= 1000 )) || { fail "expected-count deve ficar entre 500 e 1000"; return 1; }
  [[ "$CONTAINS_MINORS" == "true" || "$CONTAINS_MINORS" == "false" ]] || { fail "contains-minors deve ser true ou false"; return 1; }
  [[ "$(read_env_value FACIAL_PROCESSING_ENABLED)" == "true" ]] || { fail "processamento facial não está ativo"; return 1; }
  [[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" == "true" ]] || { fail "janela facial privada não está ativa"; return 1; }
  [[ "$(read_env_value FACIAL_HOMOLOG_BATCH_ID)" == "$BATCH_ID" ]] || { fail "batch-id diverge do lote ativo"; return 1; }
  [[ "$(read_env_value FACIAL_HOMOLOG_AUTHORIZATION_REF)" == "$AUTHORIZATION_REF" ]] || { fail "authorization-ref diverge do lote ativo"; return 1; }
  [[ "$(read_env_value FACIAL_HOMOLOG_EXPECTED_COUNT)" == "$EXPECTED_COUNT" ]] || { fail "expected-count diverge do lote ativo"; return 1; }
  [[ "$(read_env_value FACIAL_HOMOLOG_CONTAINS_MINORS)" == "$CONTAINS_MINORS" ]] || { fail "contains-minors diverge do lote ativo"; return 1; }
  [[ -n "$(facial_container_id)" ]] || { fail "face-worker privado ativo não foi encontrado"; return 1; }
  record_inventory

  local -a manifest_window
  mapfile -t manifest_window < <(
    FACIAL_STATE_DIR="$STATE_DIR" FACIAL_BATCH_ID="$BATCH_ID" \
    FACIAL_AUTHORIZATION_REF="$AUTHORIZATION_REF" FACIAL_EXPECTED_COUNT="$EXPECTED_COUNT" \
    FACIAL_CONTAINS_MINORS="$CONTAINS_MINORS" python3 - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

path = Path(os.environ["FACIAL_STATE_DIR"]) / f"facial-batch-{os.environ['FACIAL_BATCH_ID']}.json"
payload = json.loads(path.read_text(encoding="utf-8"))
expected = {
    "batch_id": os.environ["FACIAL_BATCH_ID"],
    "authorization_ref": os.environ["FACIAL_AUTHORIZATION_REF"],
    "expected_count": int(os.environ["FACIAL_EXPECTED_COUNT"]),
    "contains_minors": os.environ["FACIAL_CONTAINS_MINORS"] == "true",
    "status": "active",
}
if any(payload.get(key) != value for key, value in expected.items()):
    raise SystemExit("manifesto do lote diverge da reconciliação autorizada")
started_at = datetime.fromisoformat(payload["recorded_at"])
expires_at = datetime.fromisoformat(payload["window_expires_at"])
if started_at >= expires_at:
    raise SystemExit("janela registrada no manifesto é inválida")
print(started_at.isoformat())
print(expires_at.isoformat())
PY
  )
  [[ "${#manifest_window[@]}" -eq 2 ]] || fail "manifesto do lote não forneceu janela válida"

  FACIAL_BATCH_STARTED_AT="${manifest_window[0]}" FACIAL_BATCH_EXPIRES_AT="${manifest_window[1]}" \
  FACIAL_EXPECTED_COUNT="$EXPECTED_COUNT" FACIAL_RECONCILE_BATCH="$BATCH_ID" compose exec -T \
    -e FACIAL_BATCH_STARTED_AT -e FACIAL_BATCH_EXPIRES_AT -e FACIAL_EXPECTED_COUNT \
    -e FACIAL_RECONCILE_BATCH api python - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.auth import FacialJob, MediaDerivative, ParentGallery, PhotoAsset, PhotoFolder, SessionLocal
from app.facial.config import facial_settings_from_environment
from app.facial.indexing import enqueue_photo_index_if_eligible

started_at = datetime.fromisoformat(os.environ["FACIAL_BATCH_STARTED_AT"])
expires_at = datetime.fromisoformat(os.environ["FACIAL_BATCH_EXPIRES_AT"])
expected_count = int(os.environ["FACIAL_EXPECTED_COUNT"])
derivatives_root = Path(os.getenv("MEDIA_DERIVATIVES_ROOT", "/var/lib/markina/derivatives")).resolve()
analysis = aliased(MediaDerivative)
protected = aliased(MediaDerivative)

with SessionLocal() as db:
    scope = (
        PhotoAsset.created_at >= started_at,
        PhotoAsset.created_at < expires_at,
        PhotoFolder.purpose == "content",
        ParentGallery.active.is_(True),
        ParentGallery.lifecycle_status == "active",
    )
    photo_ids = list(db.scalars(
        select(PhotoAsset.id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .join(ParentGallery, ParentGallery.id == PhotoAsset.parent_gallery_id)
        .where(*scope)
        .order_by(PhotoAsset.id)
    ))
    if len(photo_ids) != expected_count:
        raise SystemExit(f"lote persistido divergente: {len(photo_ids)}/{expected_count}")
    ready_rows = list(db.execute(
        select(PhotoAsset, analysis)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .join(ParentGallery, ParentGallery.id == PhotoAsset.parent_gallery_id)
        .join(analysis, (analysis.photo_asset_id == PhotoAsset.id) & (analysis.variant == "admin_preview") & (analysis.status == "ready"))
        .join(protected, (protected.photo_asset_id == PhotoAsset.id) & (protected.variant == "client_preview") & (protected.status == "ready"))
        .where(*scope, PhotoAsset.available.is_(True))
        .order_by(PhotoAsset.id)
    ))
    if len(ready_rows) != expected_count:
        raise SystemExit(f"prévias ainda não concluídas: {len(ready_rows)}/{expected_count}")

    settings = facial_settings_from_environment(verify_runtime_assets=False)
    if not settings.enabled or not settings.private_homologation_active:
        raise SystemExit("gate privado expirado ou inválido")
    for photo, derivative in ready_rows:
        if not derivative.relative_path:
            raise SystemExit("prévia facial sem caminho interno")
        derivative_path = (derivatives_root / derivative.relative_path).resolve()
        try:
            derivative_path.relative_to(derivatives_root)
        except ValueError as error:
            raise SystemExit("prévia facial fora do diretório autorizado") from error
        item = enqueue_photo_index_if_eligible(
            db,
            photo,
            derivative,
            derivative_path=derivative_path,
            settings=settings,
        )
        if item is None:
            raise SystemExit("foto elegível não produziu job facial")
    db.commit()
    states = {
        status: int(count)
        for status, count in db.execute(
        select(FacialJob.status, func.count(func.distinct(FacialJob.photo_asset_id)))
        .where(FacialJob.kind == "index", FacialJob.photo_asset_id.in_(photo_ids))
        .group_by(FacialJob.status)
        )
    }
    covered = db.scalar(
        select(func.count(func.distinct(FacialJob.photo_asset_id))).where(
            FacialJob.kind == "index", FacialJob.photo_asset_id.in_(photo_ids)
        )
    ) or 0
    if covered != expected_count:
        raise SystemExit(f"cobertura de jobs divergente: {covered}/{expected_count}")
    print(json.dumps({"batch_id": os.environ["FACIAL_RECONCILE_BATCH"], "photos": expected_count, "job_states": states}, sort_keys=True))
PY
  printf '%s reconciled-private batch=%s photos=%s sha=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BATCH_ID" "$EXPECTED_COUNT" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
}

purge_and_prove() {
  FACIAL_CLOSING_BATCH="$BATCH_ID" compose exec -T -e FACIAL_CLOSING_BATCH api python - <<'PY'
import json
import os
from sqlalchemy import select, text, update
from app.auth import AuditEvent, FacialSearchRequest, GalleryFacialPolicy, SessionLocal, now
from app.facial.purge import purge_gallery_records

with SessionLocal() as db:
    policies = list(db.scalars(select(GalleryFacialPolicy)))
    totals = {"galleries": len(policies), "embeddings": 0, "candidates": 0, "requests": 0, "notifications": 0, "jobs": 0}
    report_fields = {
        "embeddings": "embeddings",
        "candidates": "candidates",
        "requests": "requests_cancelled",
        "notifications": "notifications_cancelled",
        "jobs": "jobs_cancelled",
    }
    for policy in policies:
        report = purge_gallery_records(db, parent_gallery_id=policy.parent_gallery_id)
        for total_field, report_field in report_fields.items():
            totals[total_field] += getattr(report, report_field)
        policy.status = "disabled"
        policy.suspended_at = now()
        policy.updated_at = now()
    db.execute(
        update(FacialSearchRequest)
        .where(FacialSearchRequest.reference_locator_ciphertext.is_not(None))
        .values(
            reference_locator_ciphertext=None,
            reference_locator_nonce=None,
            reference_key_id=None,
            reference_deleted_at=now(),
            updated_at=now(),
        )
        .execution_options(synchronize_session=False)
    )
    db.add(AuditEvent(event="facial.homolog_batch_closed", subject=f"batch_id:{os.environ['FACIAL_CLOSING_BATCH']};galleries:{len(policies)}"))
    db.commit()
    proof = db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM photo_face_embedding) AS embeddings,
          (SELECT COUNT(*) FROM facial_search_candidate) AS candidates,
          (SELECT COUNT(*) FROM facial_search_request WHERE reference_locator_ciphertext IS NOT NULL) AS references,
          (SELECT COUNT(*) FROM facial_search_notification_outbox WHERE status IN ('queued', 'processing')) AS pending_notifications
    """)).mappings().one()
    proof = {key: int(value) for key, value in proof.items()}
    if any(proof.values()):
        raise SystemExit(f"prova de exclusão falhou: {json.dumps(proof, sort_keys=True)}")
    print(json.dumps({"purged": totals, "proof": proof}, sort_keys=True))
PY
}

close_private() {
  [[ "$CONFIRMATION" == "$CLOSE_TOKEN" ]] || fail "confirmação explícita do fechamento privado ausente"
  validate_reference "$BATCH_ID" "batch-id"
  [[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" == "true" ]] || fail "janela facial privada não está ativa"
  [[ "$(read_env_value FACIAL_HOMOLOG_BATCH_ID)" == "$BATCH_ID" ]] || fail "batch-id diverge do lote ativo"
  ORIGIN_REF="$(read_env_value FACIAL_HOMOLOG_ORIGIN_REF)"
  AUTHORIZATION_REF="$(read_env_value FACIAL_HOMOLOG_AUTHORIZATION_REF)"
  OPERATOR_REF="$(read_env_value FACIAL_HOMOLOG_OPERATOR_REF)"
  EXPECTED_COUNT="$(read_env_value FACIAL_HOMOLOG_EXPECTED_COUNT)"
  RETENTION_HOURS="$(read_env_value FACIAL_HOMOLOG_RETENTION_HOURS)"
  CONTAINS_MINORS="$(read_env_value FACIAL_HOMOLOG_CONTAINS_MINORS)"
  WINDOW_EXPIRES_AT="$(read_env_value FACIAL_HOMOLOG_WINDOW_EXPIRES_AT)"
  record_inventory
  wait_for_media_worker_idle
  compose_facial stop face-worker
  [[ -z "$(facial_container_id)" ]] || fail "face-worker permaneceu ativo"
  write_environment close
  compose up -d --no-deps --force-recreate api worker
  verify_persistent_gate false
  reload_reverse_proxy
  purge_and_prove
  write_manifest closed-and-purged
  compose exec -T api python -c 'import os; assert os.getenv("FACIAL_PROCESSING_ENABLED", "false").lower() == "false"; assert os.getenv("FACIAL_HOMOLOG_PRIVATE_MODE", "false").lower() == "false"; assert os.getenv("FACIAL_MINOR_SEARCH_ENABLED", "false").lower() == "false"'
  printf '%s closed-private-purged batch=%s sha=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BATCH_ID" "$(git rev-parse HEAD)" >> "$STATE_DIR/facial-history.log"
  echo "lote privado fechado; dados faciais derivados eliminados e gate seguro restaurado"
}

main() {
  parse_arguments "$@"
  verify_target
  case "$MODE" in
    inventory) record_inventory ;;
    pause-legacy-for-private-upgrade) trap 'rollback_pause $?' ERR; pause_legacy_for_private_upgrade ;;
    pause-private) trap 'rollback_pause $?' ERR; pause_private ;;
    activate-private) trap 'rollback_activation $?' ERR; activate_private ;;
    reconcile-private) reconcile_private ;;
    close-private) close_private ;;
  esac
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
  main "$@"
fi
