#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export MARKINA_EXPECTED_REPOSITORY="owner/repository"
# shellcheck source=manage-homolog-facial.sh
source "$SCRIPT_DIR/manage-homolog-facial.sh"

BATCH_ID="batch-2026-09-07"
ORIGIN_REF="origin-register-42"
AUTHORIZATION_REF="approval-register-42"
OPERATOR_REF="photographer-admin-42"
EXPECTED_COUNT="500"
RETENTION_HOURS="24"
WINDOW_MINUTES="120"
CONTAINS_MINORS="true"
validate_activation_arguments

if (ORIGIN_REF=""; validate_activation_arguments >/dev/null 2>&1); then
  echo "ativação aceitou lote sem origem documentada" >&2
  exit 1
fi
if (EXPECTED_COUNT="1001"; validate_activation_arguments >/dev/null 2>&1); then
  echo "ativação aceitou quantidade fora do lote aprovado" >&2
  exit 1
fi
if (CONTAINS_MINORS="yes"; validate_activation_arguments >/dev/null 2>&1); then
  echo "ativação aceitou declaração de menores divergente" >&2
  exit 1
fi
if (parse_arguments --mode activate-synthetic >/dev/null 2>&1); then
  echo "operador aceitou modo sintético legado" >&2
  exit 1
fi
parse_arguments --mode pause-legacy-for-private-upgrade
MODE=""
parse_arguments --mode reconcile-private
[[ "$MODE" == "reconcile-private" ]]
MODE=""
parse_arguments --mode resume-private
[[ "$MODE" == "resume-private" ]]

pause_result="$({
  CONFIRMATION="PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE"
  read_env_value() {
    [[ "$1" == "FACIAL_PROCESSING_ENABLED" ]] && printf 'true' || printf 'false'
  }
  facial_container_id() { printf 'face-worker-id'; }
  pause_active_worker() { printf '%s' "$1"; }
  pause_legacy_for_private_upgrade
})"
[[ "$pause_result" == "paused-legacy-for-private-upgrade" ]]

if (
  CONFIRMATION="PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE"
  read_env_value() { printf 'true'; }
  facial_container_id() { printf 'face-worker-id'; }
  pause_active_worker() { :; }
  pause_legacy_for_private_upgrade >/dev/null 2>&1
); then
  echo "transição legada aceitou gate privado ativo" >&2
  exit 1
fi

if (
  CONFIRMATION="RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"
  BATCH_ID="batch-2026-09-07"
  AUTHORIZATION_REF="approval-register-42"
  EXPECTED_COUNT="500"
  CONTAINS_MINORS="true"
  read_env_value() {
    case "$1" in
      FACIAL_PROCESSING_ENABLED|FACIAL_HOMOLOG_PRIVATE_MODE) printf 'true' ;;
      FACIAL_HOMOLOG_BATCH_ID) printf 'outro-lote' ;;
      FACIAL_HOMOLOG_AUTHORIZATION_REF) printf '%s' "$AUTHORIZATION_REF" ;;
      FACIAL_HOMOLOG_EXPECTED_COUNT) printf '%s' "$EXPECTED_COUNT" ;;
      FACIAL_HOMOLOG_CONTAINS_MINORS) printf '%s' "$CONTAINS_MINORS" ;;
    esac
  }
  facial_container_id() { printf 'face-worker-id'; }
  record_inventory() { echo "não deveria inventariar" >&2; return 1; }
  reconcile_private >/dev/null 2>&1
); then
  echo "reconciliação aceitou batch-id divergente" >&2
  exit 1
fi

if (
  CONFIRMATION="token-invalido"
  BATCH_ID="batch-2026-09-07"
  AUTHORIZATION_REF="approval-register-42"
  EXPECTED_COUNT="500"
  WINDOW_MINUTES="30"
  CONTAINS_MINORS="true"
  resume_private >/dev/null 2>&1
); then
  echo "retomada aceitou token inválido" >&2
  exit 1
fi

echo "manage-homolog-facial validation: ok"
