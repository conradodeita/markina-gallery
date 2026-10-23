#!/usr/bin/env bash
# ForcedCommand para a chave read-only de preflight. Instalar cÃƒÂ³pia root-owned
# como /usr/local/sbin/markina-gallery-preflight-ssh-wrapper e referenciar
# com restrict,command= em authorized_keys.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly FACIAL_SCRIPT_BLOB_SHA="bc07f8a4acb90526ed98b74ea5a8acd23cc0d90e"
readonly APP_SCRIPT_BLOB_SHA="612a60cc04e5efd8e0301999f2e4ee5558c09d75"
readonly RETIREMENT_SCRIPT_BLOB_SHA="59044e2bc3e473554752b64c5d49238f5da10fdf"

fail() { echo "production-preflight: $*" >&2; exit 1; }

original_command="${SSH_ORIGINAL_COMMAND:-}"
if [[ "$original_command" =~ ^MARKINA_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-facial-services.sh"
  script_blob_sha="$FACIAL_SCRIPT_BLOB_SHA"
  inventory_mode="inventory"
elif [[ "$original_command" =~ ^MARKINA_APP_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  inventory_mode="inventory"
elif [[ "$original_command" =~ ^MARKINA_APP_ROLLBACK_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  inventory_mode="rollback-inventory"
elif [[ "$original_command" =~ ^MARKINA_RETIREMENT_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-infinitepay-retirement.sh"
  script_blob_sha="$RETIREMENT_SCRIPT_BLOB_SHA"
  inventory_mode="inventory"
else
  fail "comando SSH nÃƒÂ£o permitido"
fi

cd "$PROJECT_ROOT"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "raiz de projeto inesperada"

# A versÃƒÂ£o atualmente publicada no checkout pode nÃƒÂ£o conter este script.
# Busca-se o arquivo da revisÃƒÂ£o imutÃƒÂ¡vel, valida-se seu blob Git e aceita-se
# apenas o modo inventÃƒÂ¡rio. O script repete a checagem de que o SHA ÃƒÂ© o HEAD
# de origin/main; o cliente SSH nunca fornece stdin ou argumentos adicionais.
raw_url="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$target_sha/scripts/$script_name"
script_body="$(curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' \
  --tlsv1.2 "$raw_url")" || fail "nÃƒÂ£o foi possÃƒÂ­vel obter o inventÃƒÂ¡rio candidato"
actual_blob_sha="$(printf '%s\n' "$script_body" | git hash-object --stdin)"
[[ "$actual_blob_sha" == "$script_blob_sha" ]] || fail "script diverge do blob revisado"

# Stdin vem exclusivamente do conteÃƒÂºdo cujo hash acabou de ser validado.
printf '%s\n' "$script_body" | MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
  MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL" bash -s -- --mode "$inventory_mode" --sha "$target_sha"
