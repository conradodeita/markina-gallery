#!/usr/bin/env bash
# ForcedCommand para a chave read-only de preflight. Instalar cópia root-owned
# como /usr/local/sbin/markina-gallery-preflight-ssh-wrapper e referenciar
# com restrict,command= em authorized_keys.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly INVENTORY_SCRIPT_BLOB_SHA="2ed22f25cb5facc7f8849fffac33ab9880461412"

fail() { echo "production-preflight: $*" >&2; exit 1; }

original_command="${SSH_ORIGINAL_COMMAND:-}"
[[ "$original_command" =~ ^MARKINA_TARGET_SHA=([0-9a-f]{40})$ ]] \
  || fail "comando SSH não permitido"
target_sha="${BASH_REMATCH[1]}"

cd "$PROJECT_ROOT"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "raiz de projeto inesperada"

# A versão atualmente publicada no checkout pode não conter este script.
# Busca-se o arquivo da revisão imutável, valida-se seu blob Git e aceita-se
# apenas o modo inventário. O script repete a checagem de que o SHA é o HEAD
# de origin/main; o cliente SSH nunca fornece stdin ou argumentos adicionais.
script_file="$(mktemp "${TMPDIR:-/tmp}/markina-preflight.XXXXXX")"
trap 'rm -f "$script_file"' EXIT
raw_url="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$target_sha/scripts/deploy-prod-facial-services.sh"
curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' \
  --tlsv1.2 --output "$script_file" "$raw_url" \
  || fail "não foi possível obter o script de inventário da revisão candidata"
actual_blob_sha="$(git hash-object "$script_file")"
[[ "$actual_blob_sha" == "$INVENTORY_SCRIPT_BLOB_SHA" ]] \
  || fail "script de inventário diverge da versão revisada e fixada no wrapper"

MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL" \
  bash "$script_file" --mode inventory --sha "$target_sha" </dev/null
