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
readonly APP_SCRIPT_BLOB_SHA="646852479c83d0bfa356203379a95cbd9e4019f6"
readonly RETIREMENT_SCRIPT_BLOB_SHA="935af96ec1b650eb2c9ae188186eec38f0dd532b"
readonly ORDERS_SCRIPT_BLOB_SHA="13371d50abfdeedbe02408546a685277b3e7f042"
readonly PREVIEW_MIGRATION_INVENTORY_BLOB_SHA="f8746444ffba02e0a19ff871322571310222e458"

fail() { echo "production-preflight: $*" >&2; exit 1; }

original_command="${SSH_ORIGINAL_COMMAND:-}"
inventory_runtime="bash"
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
elif [[ "$original_command" =~ ^MARKINA_ORDERS_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="orders_pilot_release.py"
  script_blob_sha="$ORDERS_SCRIPT_BLOB_SHA"
  inventory_mode="inventory"
  inventory_runtime="python"
elif [[ "$original_command" =~ ^MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="preview_adjustment_migration_inventory.py"
  script_blob_sha="$PREVIEW_MIGRATION_INVENTORY_BLOB_SHA"
  inventory_runtime="preview-migration-python"
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
if [[ "$inventory_runtime" == "python" ]]; then
  printf '%s\n' "$script_body" | PYTHONPATH="$PROJECT_ROOT/scripts" \
    python3 -B - "$inventory_mode" --sha "$target_sha"
elif [[ "$inventory_runtime" == "preview-migration-python" ]]; then
  printf '%s\n' "$script_body" | MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA="$target_sha" \
    PYTHONPATH="$PROJECT_ROOT/scripts" python3 -B -
else
  printf '%s\n' "$script_body" | MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
    MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL" bash -s -- --mode "$inventory_mode" --sha "$target_sha"
fi
