#!/usr/bin/env bash
set -Eeuo pipefail

readonly TEST_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$TEST_SCRIPT_DIR/resume-homolog.sh"

fail_test() {
  echo "falha no teste de retomada: $*" >&2
  exit 1
}

PREVIEW_ID=""
MISSING_SERVICE=""
HEALTH_STATUS="healthy"
CURL_FAIL="false"
CURL_COUNT=0
COMPOSE_CAPTURE=""

read_facial_enabled() { printf '%s\n' "${FACIAL_ENABLED:-false}"; }

docker() {
  case "$1" in
    ps)
      [[ -z "$PREVIEW_ID" ]] || printf '%s\n' "$PREVIEW_ID"
      ;;
    inspect)
      printf '%s\n' "$HEALTH_STATUS"
      ;;
    *) fail_test "docker não esperado: $*" ;;
  esac
}

compose() {
  COMPOSE_CAPTURE="$*"
  if [[ "$1 $2" == "ps --all" ]]; then
    local service="${@: -1}"
    [[ "$service" == "$MISSING_SERVICE" ]] && return 0
    printf 'container-%s\n' "$service"
  elif [[ "$1 $2" == "ps --quiet" ]]; then
    printf 'container-%s\n' "${@: -1}"
  fi
}

curl() {
  CURL_COUNT=$((CURL_COUNT + 1))
  [[ "$CURL_FAIL" == false ]] || return 22
}

sleep() { :; }

FACIAL_ENABLED=false
discover_services
[[ "${SERVICES[*]}" == "api web worker nginx" ]] || fail_test "lista base incorreta: ${SERVICES[*]}"

FACIAL_ENABLED=true
discover_services
[[ "${SERVICES[*]}" == "api web worker nginx face-search-worker face-index-worker face-maintenance-worker" ]] \
  || fail_test "workers faciais opcionais incorretos: ${SERVICES[*]}"

FACIAL_ENABLED=false
PREVIEW_ID=preview-container
discover_services
[[ "${SERVICES[-1]}" == preview-adjustment-worker && "$PREVIEW_WORKER_ACTIVE" == 1 ]] \
  || fail_test "worker de prévia existente não foi incluído"

PREVIEW_ID=""
MISSING_SERVICE=worker
if discover_services; then fail_test "serviço ausente não foi recusado"; fi
MISSING_SERVICE=""

HEALTH_STATUS=unhealthy
if require_healthy_dependency db; then fail_test "DB não saudável foi aceito"; fi
HEALTH_STATUS=healthy
require_healthy_dependency db

SERVICES=(api web worker nginx)
compose() { COMPOSE_CAPTURE="$*"; }
start_application_services
[[ "$COMPOSE_CAPTURE" == "up -d --no-deps --no-recreate api web worker nginx" ]] \
  || fail_test "retomada não foi delimitada: $COMPOSE_CAPTURE"

compose() {
  COMPOSE_CAPTURE="$*"
  if [[ "$1 $2" == "ps --quiet" ]]; then printf 'container-%s\n' "${@: -1}"; fi
}
wait_for_health
[[ "$CURL_COUNT" == 4 ]] || fail_test "esperava quatro healthchecks, executados: $CURL_COUNT"
CURL_FAIL=true
if wait_for_health; then fail_test "falha de endpoint não foi propagada"; fi

echo "testes do fluxo de retomada aprovados"
