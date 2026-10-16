#!/usr/bin/env bash
# ForcedCommand para a chave read-only de preflight. Instalar cópia root-owned
# como /usr/local/sbin/markina-gallery-preflight-ssh-wrapper e referenciar
# com restrict,command= em authorized_keys.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"

fail() { echo "production-preflight: $*" >&2; exit 1; }

original_command="${SSH_ORIGINAL_COMMAND:-}"
[[ "$original_command" =~ ^MARKINA_TARGET_SHA=([0-9a-f]{40})$ ]] \
  || fail "comando SSH não permitido"
target_sha="${BASH_REMATCH[1]}"

cd "$PROJECT_ROOT"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "raiz de projeto inesperada"
export MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY"
export MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL"

# O script é lido do checkout fixo do servidor; stdin remoto nunca é executado.
exec bash scripts/deploy-prod-facial-services.sh --mode inventory --sha "$target_sha" </dev/null
