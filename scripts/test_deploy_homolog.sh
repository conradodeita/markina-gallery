#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-homolog.sh"

output="$(mktemp)"
err_probe="$(mktemp)"
trap 'rm -f "$output" "$err_probe"' EXIT

if MARKINA_EXPECTED_REPOSITORY="owner/repository" bash "$DEPLOY_SCRIPT" --sha 0000000000000000000000000000000000000000 >"$output" 2>&1; then
  echo "o deploy aceitou execução fora de /opt/markina-gallery" >&2
  exit 1
fi

grep -Fq 'o deploy só pode executar em /opt/markina-gallery' "$output"

if MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  bash -s -- --sha 0000000000000000000000000000000000000000 \
  <"$DEPLOY_SCRIPT" >"$output" 2>&1; then
  echo "o deploy via stdin aceitou execução fora de /opt/markina-gallery" >&2
  exit 1
fi
grep -Fq 'o deploy só pode executar em /opt/markina-gallery' "$output"

set +e
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" \
  MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  ERR_PROBE="$err_probe" \
  bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  trap '\''printf "%s\n" trapped > "$ERR_PROBE"'\'' ERR
  fail "falha sintética pós-switch"
' >"$output" 2>&1
fail_status=$?
set -e
[[ "$fail_status" -ne 0 ]]
grep -Fq 'deploy-homolog: falha sintética pós-switch' "$output"
grep -Fq 'trapped' "$err_probe"

dirty_output="$(mktemp)"
migration_output="$(mktemp)"
health_output="$(mktemp)"
rollback_log="$(mktemp)"
secrets_env="$(mktemp)"
same_secret_env="$(mktemp)"
origin_env="$(mktemp)"
payload_env="$(mktemp)"
invalid_payload_env="$(mktemp)"
trap 'rm -f "$output" "$err_probe" "$dirty_output" "$migration_output" "$health_output" "$rollback_log" "$secrets_env" "$same_secret_env" "$origin_env" "$payload_env" "$invalid_payload_env"' EXIT

printf 'APP_ENV=homologation\nAUTH_PII_FINGERPRINT_SALT=\nGALLERY_CAPABILITY_SIGNING_KEY=\n' >"$secrets_env"
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" SECRETS_ENV="$secrets_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_pii_fingerprint_salt "$SECRETS_ENV"
    ensure_gallery_capability_signing_key "$SECRETS_ENV"
    fingerprint="$(grep "^AUTH_PII_FINGERPRINT_SALT=" "$SECRETS_ENV")"
    fingerprint="${fingerprint#*=}"
    signing="$(grep "^GALLERY_CAPABILITY_SIGNING_KEY=" "$SECRETS_ENV")"
    signing="${signing#*=}"
    [[ "${#fingerprint}" -ge 32 ]]
    [[ "${#signing}" -ge 32 ]]
    [[ "$fingerprint" != "$signing" ]]
    [[ "$(stat -c %a "$SECRETS_ENV")" == "600" ]]
  ' >"$output" 2>&1
grep -Fq 'GALLERY_CAPABILITY_SIGNING_KEY configurado com segredo aleatório exclusivo de homologação' "$output"

printf 'APP_ENV=homologation\nEMAIL_PAYLOAD_ENCRYPTION_KEY=\n' >"$payload_env"
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" PAYLOAD_ENV="$payload_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_sensitive_payload_encryption_key "$PAYLOAD_ENV"
    value="$(grep "^EMAIL_PAYLOAD_ENCRYPTION_KEY=" "$PAYLOAD_ENV")"
    value="${value#*=}"
    [[ -n "$value" ]]
    PAYLOAD_KEY_VALUE="$value" python3 - <<'"'"'PY'"'"'
import base64
import os

assert len(base64.urlsafe_b64decode(os.environ["PAYLOAD_KEY_VALUE"].encode("ascii"))) == 32
PY
    [[ "$(stat -c %a "$PAYLOAD_ENV")" == "600" ]]
  ' >"$output" 2>&1
grep -Fq 'EMAIL_PAYLOAD_ENCRYPTION_KEY configurada com segredo aleatório exclusivo de homologação' "$output"

printf 'EMAIL_PAYLOAD_ENCRYPTION_KEY=invalida\n' >"$invalid_payload_env"
if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" PAYLOAD_ENV="$invalid_payload_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_sensitive_payload_encryption_key "$PAYLOAD_ENV"
  ' >"$output" 2>&1; then
  echo "chave de payload inválida não foi recusada" >&2
  exit 1
fi
grep -Fq 'EMAIL_PAYLOAD_ENCRYPTION_KEY deve codificar exatamente 32 bytes em base64 urlsafe' "$output"

same_secret="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
printf 'AUTH_PII_FINGERPRINT_SALT=%s\nGALLERY_CAPABILITY_SIGNING_KEY=%s\n' "$same_secret" "$same_secret" >"$same_secret_env"
if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" SECRETS_ENV="$same_secret_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_gallery_capability_signing_key "$SECRETS_ENV"
  ' >"$output" 2>&1; then
  echo "chave de galeria igual ao fingerprint de PII não foi recusada" >&2
  exit 1
fi
grep -Fq 'GALLERY_CAPABILITY_SIGNING_KEY deve ser diferente de AUTH_PII_FINGERPRINT_SALT' "$output"

printf 'APP_ENV=staging\nPUBLIC_APP_ORIGIN=\n' >"$origin_env"
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" ORIGIN_ENV="$origin_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_public_app_origin "$ORIGIN_ENV" "https://markina-homolog.example/"
    [[ "$(grep -c "^PUBLIC_APP_ORIGIN=" "$ORIGIN_ENV")" -eq 1 ]]
    grep -Fxq "PUBLIC_APP_ORIGIN=https://markina-homolog.example" "$ORIGIN_ENV"
    [[ "$(stat -c %a "$ORIGIN_ENV")" == "600" ]]
  ' >"$output" 2>&1
grep -Fq 'PUBLIC_APP_ORIGIN sincronizada com a origem pública autorizada de homologação' "$output"

if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" ORIGIN_ENV="$origin_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    ensure_public_app_origin "$ORIGIN_ENV" "https://markina-homolog.example/caminho"
  ' >"$output" 2>&1; then
  echo "origem pública com caminho foi aceita" >&2
  exit 1
fi
grep -Fq 'MARKINA_PUBLIC_BASE_URL não representa uma origem HTTPS válida' "$output"

if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    git() { [[ "$*" == "status --porcelain" ]] && printf " M arquivo-local\n"; }
    verify_clean_checkout
  ' >"$dirty_output" 2>&1; then
  echo "checkout sujo não interrompeu a publicação" >&2
  exit 1
fi
grep -Fq 'checkout remoto possui alterações locais' "$dirty_output"

facial_env="$(mktemp)"
trap 'rm -f "$output" "$err_probe" "$dirty_output" "$migration_output" "$health_output" "$rollback_log" "$secrets_env" "$same_secret_env" "$origin_env" "$payload_env" "$invalid_payload_env" "$facial_env"' EXIT
printf 'FACIAL_PROCESSING_ENABLED=false\n' >"$facial_env"
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" FACIAL_ENV="$facial_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    set_facial_enabled true "$FACIAL_ENV"
    grep -Fxq "FACIAL_PROCESSING_ENABLED=true" "$FACIAL_ENV"
    [[ "$(stat -c %a "$FACIAL_ENV")" == "600" ]]
    set_facial_enabled false "$FACIAL_ENV"
    grep -Fxq "FACIAL_PROCESSING_ENABLED=false" "$FACIAL_ENV"
  ' >"$output" 2>&1
grep -Fq 'FACIAL_PROCESSING_ENABLED persistido como true em homologação' "$output"

MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" FACIAL_ENV="$facial_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() { echo "o Compose anterior não conhece os workers novos" >&2; return 99; }
    docker() { [[ "$1" == "ps" ]] && return 0; }
    verify_facial_deploy_state "$FACIAL_ENV"
  ' >"$output" 2>&1
grep -Fq 'flag=false workers=ausentes' "$output"
if grep -Fq 'o Compose anterior não conhece os workers novos' "$output"; then
  echo "a verificação inicial consultou workers ausentes no Compose anterior" >&2
  exit 1
fi

printf 'FACIAL_PROCESSING_ENABLED=true\n' >"$facial_env"
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" FACIAL_ENV="$facial_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() {
      [[ "$1" == "exec" ]] && return 0
    }
    docker() {
      [[ "$1" == "ps" ]] && { printf "container-sintetico\n"; return 0; }
      [[ "$1" == "inspect" ]] && printf "healthy\n"
    }
    verify_facial_deploy_state "$FACIAL_ENV"
  ' >"$output" 2>&1
grep -Fq 'flag=true workers=saudáveis' "$output"

if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" FACIAL_ENV="$facial_env" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() { [[ "$1" == "exec" ]] && return 0; }
    docker() {
      [[ "$1" == "ps" && "$*" == *"service=face-index-worker"* ]] && return 0
      [[ "$1" == "ps" ]] && { printf "container-sintetico\n"; return 0; }
      [[ "$1" == "inspect" ]] && printf "healthy\n"
    }
    verify_facial_deploy_state "$FACIAL_ENV"
  ' >"$output" 2>&1; then
  echo "deploy aceitou combinação facial incoerente" >&2
  exit 1
fi
grep -Fq 'face-index-worker deve estar ativo com flag=true' "$output"

if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() {
      [[ "$*" == "build migrate" ]] && return 0
      [[ "$*" == "run --rm --no-deps migrate" ]] && return 42
      return 0
    }
    apply_target_migrations "20260829_0014 (head)"
  ' >"$migration_output" 2>&1; then
  echo "migration sintética falha não interrompeu a publicação" >&2
  exit 1
fi
grep -Fq 'migration do SHA alvo falhou; banco preservado para revisão humana' "$migration_output"

if MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() { [[ "$1" == "ps" ]] && printf "container-sintetico\n"; }
    docker() {
      if [[ "$1" == "inspect" && "$*" == *"diagnóstico sanitizado:"* ]]; then
        printf "diagnóstico sanitizado: service=api status=running health=unhealthy exit_code=0 oom=false restart_count=2 state_error=absent\n"
        return 0
      fi
      [[ "$1" == "inspect" ]] && printf "unhealthy\n"
      if [[ "$1" == "logs" ]]; then
        printf "conteúdo-proibido-do-job\nModuleNotFoundError: conteúdo-proibido-do-job\n"
        return 0
      fi
    }
    seq() { printf "1\n"; }
    sleep() { :; }
    wait_for_health
  ' >"$health_output" 2>&1; then
  echo "healthcheck sintético falho não interrompeu a publicação" >&2
  exit 1
fi
grep -Fq 'serviço Markina não ficou saudável: api (unhealthy)' "$health_output"
grep -Fq 'diagnóstico sanitizado: service=api' "$health_output"
grep -Fq 'oom=' "$health_output"
grep -Fq 'restart_count=' "$health_output"
grep -Fq 'exception_class=ModuleNotFoundError' "$health_output"
if grep -Fq 'conteúdo-proibido-do-job' "$health_output"; then
  echo "diagnóstico expôs conteúdo da mensagem de exceção" >&2
  exit 1
fi

whatsapp_output="$(mktemp)"
trap 'rm -f "$output" "$err_probe" "$dirty_output" "$migration_output" "$health_output" "$rollback_log" "$secrets_env" "$same_secret_env" "$origin_env" "$whatsapp_output"' EXIT
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    compose() {
      if [[ "$*" == "config --services" ]]; then printf "evolution-api\n"; return 0; fi
      if [[ "$1" == "ps" ]]; then printf "container-%s\n" "$3"; return 0; fi
      printf "compose %s\n" "$*"
    }
    docker() { [[ "$1" == "inspect" ]] && printf "healthy\n"; }
    start_whatsapp_infrastructure_if_active
  ' >"$whatsapp_output" 2>&1
grep -Fq 'compose up -d evolution-db evolution-redis evolution-api' "$whatsapp_output"

set +e
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" ROLLBACK_LOG="$rollback_log" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    SHA_SWITCHED=1
    MIGRATION_CHANGED=0
    SCHEMA_ROLLBACK_UNSAFE=0
    PREVIOUS_SHA=1111111111111111111111111111111111111111
    git() { printf "git %s\n" "$*" >> "$ROLLBACK_LOG"; }
    compose() { printf "compose %s\n" "$*" >> "$ROLLBACK_LOG"; }
    verify_facial_deploy_state() { printf "facial rollback verificado\n" >> "$ROLLBACK_LOG"; }
    record_revision() { printf "record %s %s\n" "$1" "$2" >> "$ROLLBACK_LOG"; }
    rollback_code_if_safe 23
  ' >"$output" 2>&1
safe_rollback_status=$?
set -e
[[ "$safe_rollback_status" -eq 23 ]]
grep -Fq 'git switch --detach 1111111111111111111111111111111111111111' "$rollback_log"
grep -Fq 'compose up -d --build --no-deps api web worker' "$rollback_log"
grep -Fq 'facial rollback verificado' "$rollback_log"
grep -Fq 'record last-rollback 1111111111111111111111111111111111111111' "$rollback_log"

: >"$rollback_log"
set +e
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" ROLLBACK_LOG="$rollback_log" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    SHA_SWITCHED=1
    MIGRATION_CHANGED=0
    SCHEMA_ROLLBACK_UNSAFE=0
    FACIAL_DEPLOY_ENABLED=true
    PREVIOUS_SHA=2222222222222222222222222222222222222222
    git() { printf "git %s\n" "$*" >> "$ROLLBACK_LOG"; }
    compose() { printf "compose %s\n" "$*" >> "$ROLLBACK_LOG"; }
    verify_facial_deploy_state() { printf "facial rollback ativo verificado\n" >> "$ROLLBACK_LOG"; }
    record_revision() { printf "record %s %s\n" "$1" "$2" >> "$ROLLBACK_LOG"; }
    rollback_code_if_safe 24
  ' >"$output" 2>&1
enabled_rollback_status=$?
set -e
[[ "$enabled_rollback_status" -eq 24 ]]
grep -Fq 'compose up -d --build --no-deps face-search-worker face-index-worker face-maintenance-worker' "$rollback_log"
grep -Fq 'facial rollback ativo verificado' "$rollback_log"

: >"$rollback_log"
set +e
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" MARKINA_EXPECTED_REPOSITORY="owner/repository" ROLLBACK_LOG="$rollback_log" \
  bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    SHA_SWITCHED=1
    MIGRATION_CHANGED=0
    SCHEMA_ROLLBACK_UNSAFE=1
    PREVIOUS_SHA=1111111111111111111111111111111111111111
    git() { printf "git %s\n" "$*" >> "$ROLLBACK_LOG"; }
    compose() { printf "compose %s\n" "$*" >> "$ROLLBACK_LOG"; }
    rollback_code_if_safe 29
  ' >"$output" 2>&1
unsafe_rollback_status=$?
set -e
[[ "$unsafe_rollback_status" -eq 29 ]]
[[ ! -s "$rollback_log" ]]
grep -Fq 'banco não foi restaurado' "$output"

python3 "$SCRIPT_DIR/test_deploy_homolog_policy.py"
python3 "$SCRIPT_DIR/test_maintain_homolog_policy.py"
python3 "$SCRIPT_DIR/test_facial_production_policy.py"
echo "deploy-homolog shell: ok"
