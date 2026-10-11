#!/usr/bin/env bash
# Contratos operacionais Gemma: nenhuma chamada Docker real nestes testes.
set -Eeuo pipefail
gemma_test_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
gemma_test_output="$(mktemp)"
trap 'rm -f "$gemma_test_output"' EXIT
export MARKINA_EXPECTED_REPOSITORY="owner/repository"

# A descoberta usa labels do projeto e nunca trata Gemma como worker SFace.
for gemma_running in 0 1; do
 (
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  docker() {
    [[ "$*" == *project=markina-gallery* && "$*" == *service=face-gemma-index-worker* ]] || return 84
    [[ "$gemma_running" == 0 ]] || echo synthetic-gemma
    return 0
  }
  discover_gemma_worker
  [[ "$GEMMA_WORKER_ACTIVE" == "$gemma_running" ]]
  [[ " ${FACIAL_SERVICES[*]} " != *' face-gemma-index-worker '* ]]
 )
done

# Um leitor Gemma ativo deve parar antes de Alembic; terceiros nunca são alvos.
(
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  FACIAL_DEPLOY_ENABLED=true
  GEMMA_WORKER_ACTIVE=1
  stopped=0
  compose() {
    printf '%s\n' "$*"
    if [[ "$1" == stop ]]; then
      [[ "$*" == 'stop --timeout 60 api worker face-search-worker face-index-worker face-maintenance-worker face-gemma-index-worker' ]] || return 80
      stopped=1
    fi
    [[ "$1" != run || "$stopped" == 1 ]] || return 81
  }
  docker() {
    [[ "$*" == *project=markina-gallery* && "$*" != *evolution* && "$*" != *firefly* ]] || return 82
  }
  current_revision() { echo '20261011_0074 (head)'; }
  apply_target_migrations '20261009_0072 (head)'
  [[ "$MIGRATION_CHANGED" == 1 ]]
) >"$gemma_test_output" 2>&1
grep -Fq 'stop --timeout 60 api worker face-search-worker face-index-worker face-maintenance-worker face-gemma-index-worker' "$gemma_test_output"

# Ausência do container experimental não inicia/builda Gemma pela flag facial.
for gemma_active in 0 1; do
 (
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  FACIAL_DEPLOY_ENABLED=true
  GEMMA_WORKER_ACTIVE="$gemma_active"
  compose() { printf 'compose %s\n' "$*"; }
  python3() { :; }
  prepare_branding_transition
  start_application_services
 ) >"$gemma_test_output" 2>&1
 if [[ "$gemma_active" == 1 ]]; then
  grep -Fxq 'compose build face-gemma-index-worker' "$gemma_test_output"
  grep -Fxq 'compose up -d --build --no-deps face-gemma-index-worker' "$gemma_test_output"
 elif grep -Fq 'face-gemma-index-worker' "$gemma_test_output"; then
  echo 'Gemma foi iniciado implicitamente' >&2; exit 1
 fi
done

# Falha de parada do Gemma impede qualquer migration.
if (
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  GEMMA_WORKER_ACTIVE=1
  compose() {
    [[ "$1" == stop ]] && return 42
    [[ "$1" == run ]] && echo UNEXPECTED-MIGRATION
    return 0
  }
  apply_target_migrations '20261009_0072 (head)'
) >"$gemma_test_output" 2>&1; then
  echo 'Migration aceitou falha de parada Gemma' >&2; exit 1
fi
grep -Fq 'migration bloqueada' "$gemma_test_output"
if grep -Fq UNEXPECTED-MIGRATION "$gemma_test_output"; then exit 1; fi

# Parada que retorna sucesso mas deixa Gemma vivo também bloqueia Alembic.
if (
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  GEMMA_WORKER_ACTIVE=1
  compose() { [[ "$1" != run ]] || echo UNEXPECTED-MIGRATION; }
  docker() { [[ "$*" != *service=face-gemma-index-worker* ]] || echo synthetic-still-running; }
  apply_target_migrations '20261009_0072 (head)'
) >"$gemma_test_output" 2>&1; then
  echo 'Migration aceitou leitor Gemma ainda ativo' >&2; exit 1
fi
grep -Fq 'escritor Markina ainda ativo: face-gemma-index-worker' "$gemma_test_output"
if grep -Fq UNEXPECTED-MIGRATION "$gemma_test_output"; then exit 1; fi

# Gemma participa do gate de saúde quando seu container estava ativo.
set +e
(
  set -e
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  GEMMA_WORKER_ACTIVE=1
  compose() { printf '%s\n' "$3"; }
  docker() { [[ "$*" == *face-gemma-index-worker* ]] && echo unhealthy || echo healthy; }
  report_container_state() { :; }
  sleep() { :; }
  curl() { echo UNEXPECTED-HTTP; }
  wait_for_health
) >"$gemma_test_output" 2>&1
gemma_health_status=$?
set -e
if [[ "$gemma_health_status" == 0 ]]; then
  echo 'Deploy aceitou Gemma não saudável' >&2; exit 1
fi
grep -Fq 'serviço Markina não ficou saudável: face-gemma-index-worker' "$gemma_test_output"
if grep -Fq UNEXPECTED-HTTP "$gemma_test_output"; then exit 1; fi

# O contrato de leitores da manutenção inclui somente Gemma realmente ativo.
gemma_pause_fragment="$(sed -n '/^paused_services=(api worker)/,/^preview_container=/p' "$gemma_test_root/scripts/maintain-homolog-data.sh" | sed '$d')"
for gemma_running in 0 1; do
 (
  compose() { [[ "$*" != 'ps -q face-gemma-index-worker' || "$gemma_running" == 0 ]] || echo synthetic-gemma; return 0; }
  docker() { [[ "$*" == inspect* ]] || return 85; echo true; }
  eval "$gemma_pause_fragment"
  if [[ "$gemma_running" == 1 ]]; then
    [[ "${paused_services[*]}" == 'api worker face-gemma-index-worker' ]]
  else
    [[ "${paused_services[*]}" == 'api worker' ]]
  fi
 )
done

# Retomada descobre somente containers existentes do projeto exclusivo.
for gemma_exists in 0 1; do
 (
  source "$gemma_test_root/scripts/resume-homolog.sh"
  read_facial_enabled() { echo true; }
  docker() {
    [[ "$*" == *project=markina-gallery* ]] || return 83
    if [[ "$*" == *service=face-gemma-index-worker* && "$gemma_exists" == 1 ]]; then echo synthetic-gemma; fi
  }
  compose() { [[ "$*" == ps* ]] && echo synthetic-container; return 0; }
  discover_services
  printf '%s\n' "${SERVICES[@]}"
 ) >"$gemma_test_output" 2>&1
 if [[ "$gemma_exists" == 1 ]]; then
  grep -Fxq face-gemma-index-worker "$gemma_test_output"
 elif grep -Fxq face-gemma-index-worker "$gemma_test_output"; then
  echo 'Retomada criou serviço Gemma ausente' >&2; exit 1
 fi
done

# Rollback para checkout sem Gemma deve parar o leitor antes de trocar código.
set +e
(
  source "$gemma_test_root/scripts/deploy-homolog.sh"
  GEMMA_WORKER_ACTIVE=1
  SHA_SWITCHED=1
  PREVIOUS_SHA=1111111111111111111111111111111111111111
  compose() { printf 'compose %s\n' "$*"; }
  git() {
    [[ "$1" == cat-file ]] && return 1
    printf 'git %s\n' "$*"
  }
  verify_facial_deploy_state() { :; }
  record_revision() { :; }
  rollback_code_if_safe 23
) >"$gemma_test_output" 2>&1
gemma_rollback_status=$?
set -e
[[ "$gemma_rollback_status" == 23 ]]
grep -Fxq 'compose stop --timeout 60 face-gemma-index-worker' "$gemma_test_output"
if grep -Fq 'up -d --build --no-deps face-gemma-index-worker' "$gemma_test_output"; then exit 1; fi
python3 - "$gemma_test_output" <<'PY'
from pathlib import Path
import sys
events = Path(sys.argv[1]).read_text()
assert events.index('compose stop --timeout 60 face-gemma-index-worker') < events.index('git switch --detach')
PY
echo 'gemma operations: ok'
