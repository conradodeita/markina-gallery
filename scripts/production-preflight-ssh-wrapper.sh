#!/usr/bin/env bash
# ForcedCommand para a chave read-only de preflight. Instalar cÃƒÂ³pia root-owned
# como /usr/local/sbin/markina-gallery-preflight-ssh-wrapper e referenciar
# com restrict,command= em authorized_keys.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly FACIAL_SCRIPT_BLOB_SHA="515c3c82c30bf76be0ec8f01013225fb71276df3"
readonly APP_SCRIPT_BLOB_SHA="2a7b4c905c50ce192609240dad4b9b0c7ce591a6"
readonly RETIREMENT_SCRIPT_BLOB_SHA="d8fb13a50b5254e458f19d2c5d4ed8c43fadea1b"
readonly ORDERS_SCRIPT_BLOB_SHA="f45b16ca2d748172ca617c78e31de6cff2fa4289"
readonly PREVIEW_MIGRATION_INVENTORY_BLOB_SHA="1296ccb0e0f6295bc07b30837fc5043e7dac4db6"
readonly APP_ENV_INVENTORY_BLOB_SHA="8a460514b25ee26355e5252815096940b5736083"
readonly APP_BASE_IMAGE_EXPORT_BLOB_SHA="988ca208646836ecb965b80ec91c2ada9a38dc37"

fail() { echo "production-preflight: $*" >&2; exit 1; }

original_command="${SSH_ORIGINAL_COMMAND:-}"
inventory_runtime="bash"
inventory_arguments=()
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
elif [[ "$original_command" =~ ^MARKINA_PICKER_SUPPORT_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  inventory_mode="picker-inventory"
elif [[ "$original_command" =~ ^MARKINA_APP_ADOPTION_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  inventory_mode="adoption-inventory"
  inventory_runtime="app-adoption"
elif [[ "$original_command" =~ ^MARKINA_APP_HANDOFF_SHA=([0-9a-f]{40})_BUNDLE=([0-9a-f]{64})_BASE=(sha256:[0-9a-f]{64})_API=(sha256:[0-9a-f]{64})_WEB=(sha256:[0-9a-f]{64})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  inventory_arguments=(--artifact-sha256 "${BASH_REMATCH[2]}" --api-base-image-id "${BASH_REMATCH[3]}"
    --candidate-api-id "${BASH_REMATCH[4]}" --candidate-web-id "${BASH_REMATCH[5]}")
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  inventory_mode="handoff-inventory"
elif [[ "$original_command" =~ ^MARKINA_APP_HANDOFF_(WITNESSES|LEGACY_RECOVERY|RECOVERY)_SHA=([0-9a-f]{40})$ ]]; then
  selection="${BASH_REMATCH[1]}"
  target_sha="${BASH_REMATCH[2]}"
  script_name="deploy-prod-app-services.sh"
  script_blob_sha="$APP_SCRIPT_BLOB_SHA"
  case "$selection" in
    WITNESSES) inventory_mode="handoff-witness-inventory" ;;
    LEGACY_RECOVERY) inventory_mode="handoff-legacy-recovery-inventory" ;;
    RECOVERY) inventory_mode="handoff-recovery-inventory" ;;
  esac
elif [[ "$original_command" =~ ^MARKINA_APP_BASE_IMAGE_EXPORT_SHA=([0-9a-f]{40})_IMAGE_ID=(sha256:[0-9a-f]{64})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  expected_image_id="${BASH_REMATCH[2]}"
  script_name="export_prod_app_api_base_image.sh"
  script_blob_sha="$APP_BASE_IMAGE_EXPORT_BLOB_SHA"
  inventory_mode="base-image-export"
  inventory_runtime="api-base-export"
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
elif [[ "$original_command" =~ ^MARKINA_APP_ENV_INVENTORY_TARGET_SHA=([0-9a-f]{40})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  script_name="app_env_transition_inventory.py"
  script_blob_sha="$APP_ENV_INVENTORY_BLOB_SHA"
  inventory_mode="app-env-inventory"
  inventory_runtime="python"
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
elif [[ "$inventory_runtime" == "api-base-export" ]]; then
  printf '%s\n' "$script_body" | MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
    bash -s -- --mode export --sha "$target_sha" --expected-image-id "$expected_image_id"
elif [[ "$inventory_runtime" == "app-adoption" ]]; then
  printf '%s\n' "$script_body" | MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
    MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL" bash -s -- --mode adoption-inventory --sha "$target_sha"
else
  printf '%s\n' "$script_body" | MARKINA_EXPECTED_REPOSITORY="$EXPECTED_REPOSITORY" \
    MARKINA_PUBLIC_BASE_URL="$PUBLIC_URL" bash -s -- --mode "$inventory_mode" --sha "$target_sha" "${inventory_arguments[@]}"
fi
