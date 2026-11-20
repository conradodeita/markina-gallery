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
readonly BACKUP_ARTIFACT_BLOB_SHA="af6ae65732b94a52ecbcadb7cb0ebf9b455af296"
readonly BACKUP_INVENTORY_BLOB_SHA="64cd8c08a71e28332cbd2d276637fb48621e9625"
readonly BACKUP_INSTALLER_BLOB_SHA="0b96e8257720aba015ea01a1eaa37ba17dd9dfb7"

fail() { echo "production-preflight: $*" >&2; exit 1; }

acquire_backup_release_lock() {
  readonly backup_state_dir="/var/lib/markina-gallery/deploy-state"
  readonly backup_release_lock="$backup_state_dir/production-release.lock"
  [[ -d "$backup_state_dir" && ! -L "$backup_state_dir" \
     && "$(stat -c '%U:%G:%a' -- "$backup_state_dir")" == ubuntu:ubuntu:700 ]] \
    || fail "lock do release indisponível"
  [[ -f "$backup_release_lock" && ! -L "$backup_release_lock" \
     && "$(stat -c '%U:%G:%a' -- "$backup_release_lock")" == ubuntu:ubuntu:600 ]] \
    || fail "lock do release inseguro"
  exec {backup_release_lock_fd}<"$backup_release_lock"
  flock -n "$backup_release_lock_fd" || fail "outro release está em andamento"
}

original_command="${SSH_ORIGINAL_COMMAND:-}"
backup_mode=""
backup_sha=""
backup_digest=""
backup_fingerprint=""
if [[ "$original_command" =~ ^MARKINA_PLATFORM_BACKUP_INVENTORY_SHA=([0-9a-f]{40})$ ]]; then
  backup_mode="inventory"
  backup_sha="${BASH_REMATCH[1]}"
elif [[ "$original_command" =~ ^MARKINA_PLATFORM_BACKUP_INSTALL_SHA=([0-9a-f]{40})_BUNDLE=([0-9a-f]{64})_FINGERPRINT=([0-9a-f]{64})$ ]]; then
  backup_mode="install"
  backup_sha="${BASH_REMATCH[1]}"
  backup_digest="${BASH_REMATCH[2]}"
  backup_fingerprint="${BASH_REMATCH[3]}"
elif [[ "$original_command" =~ ^MARKINA_PLATFORM_BACKUP_BIND_SHA=([0-9a-f]{40})_BUNDLE=([0-9a-f]{64})_FINGERPRINT=([0-9a-f]{64})$ ]]; then
  backup_mode="bind-and-rehearse"
  backup_sha="${BASH_REMATCH[1]}"
  backup_digest="${BASH_REMATCH[2]}"
  backup_fingerprint="${BASH_REMATCH[3]}"
elif [[ "$original_command" =~ ^MARKINA_PLATFORM_BACKUP_RECONCILE_SHA=([0-9a-f]{40})_BUNDLE=([0-9a-f]{64})_FINGERPRINT=([0-9a-f]{64})$ ]]; then
  backup_mode="reconcile"
  backup_sha="${BASH_REMATCH[1]}"
  backup_digest="${BASH_REMATCH[2]}"
  backup_fingerprint="${BASH_REMATCH[3]}"
fi

if [[ -n "$backup_mode" ]]; then
  cd "$PROJECT_ROOT"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "raiz de projeto inesperada"
  [[ "$(git ls-remote origin refs/heads/main | cut -f1)" == "$backup_sha" ]] \
    || fail "SHA de operação não é a ponta atual da main"
  source_dir="$(mktemp -d)" || fail "staging de suporte indisponível"
  trap 'rm -rf -- "$source_dir"' EXIT
  raw_base="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$backup_sha/scripts"
  curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 \
    "$raw_base/platform_backup_runtime_inventory.py" -o "$source_dir/inventory.py" \
    || fail "inventário do backup indisponível"
  [[ "$(git hash-object -- "$source_dir/inventory.py")" == "$BACKUP_INVENTORY_BLOB_SHA" ]] \
    || fail "blob do inventário do backup diverge"
  inventory_b64="$(base64 -w0 "$source_dir/inventory.py")"
  inventory_bootstrap="$(cat <<'PY'
import base64
import sys
import types

module = types.ModuleType("platform_backup_runtime_inventory")
module.__file__ = "platform_backup_runtime_inventory.py"
sys.modules[module.__name__] = module
exec(compile(base64.b64decode(sys.argv[1]), module.__file__, "exec"), module.__dict__)
operation, args = sys.argv[2], sys.argv[3:]
if operation == "inventory":
    raise SystemExit(module.main())
if operation == "assert-installed" and len(args) == 2:
    try:
        module.verify_installed_release(args[0], args[1])
    except (module.InventoryError, OSError, ValueError):
        print("installed_runtime=invalid")
        raise SystemExit(1)
    print("installed_runtime=verified")
    raise SystemExit(0)
raise SystemExit(2)
PY
)"
  case "$backup_mode" in
    inventory)
      sudo -n /usr/bin/python3.10 -B -c "$inventory_bootstrap" "$inventory_b64" inventory </dev/null
      exit 0
      ;;
    install)
      for pair in "platform_backup_runtime_artifact.py:$BACKUP_ARTIFACT_BLOB_SHA:artifact.py" \
                  "install_platform_backup_runtime.py:$BACKUP_INSTALLER_BLOB_SHA:installer.py"; do
        IFS=: read -r source_name expected_blob local_name <<< "$pair"
        curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 \
          "$raw_base/$source_name" -o "$source_dir/$local_name" || fail "suporte do instalador indisponível"
        [[ "$(git hash-object -- "$source_dir/$local_name")" == "$expected_blob" ]] \
          || fail "blob do instalador diverge"
      done
      artifact_b64="$(base64 -w0 "$source_dir/artifact.py")"
      installer_b64="$(base64 -w0 "$source_dir/installer.py")"
      installer_bootstrap="$(cat <<'PY'
import base64
import sys
import types

payloads = sys.argv[1:4]
arguments = sys.argv[4:]
for name, payload in zip(("platform_backup_runtime_artifact", "platform_backup_runtime_inventory"), payloads[:2]):
    module = types.ModuleType(name)
    module.__file__ = name + ".py"
    sys.modules[name] = module
    exec(compile(base64.b64decode(payload), module.__file__, "exec"), module.__dict__)
sys.argv = ["install_platform_backup_runtime.py", *arguments]
namespace = {"__name__": "__main__", "__file__": "install_platform_backup_runtime.py"}
exec(compile(base64.b64decode(payloads[2]), namespace["__file__"], "exec"), namespace)
PY
)"
      sudo -n /usr/bin/python3.10 -B -c "$installer_bootstrap" \
        "$artifact_b64" "$inventory_b64" "$installer_b64" \
        --sha "$backup_sha" --bundle-sha256 "$backup_digest" \
        --approval-fingerprint "$backup_fingerprint"
      exit $?
      ;;
    bind-and-rehearse|reconcile)
      [[ "$backup_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint inválida"
      acquire_backup_release_lock
      sudo -n /usr/bin/python3.10 -B -c "$inventory_bootstrap" \
        "$inventory_b64" assert-installed "$backup_sha" "$backup_digest" >/dev/null \
        || fail "runtime instalado diverge da revisão aprovada"
      inventory_report="$(sudo -n /usr/bin/python3.10 -B -c "$inventory_bootstrap" \
        "$inventory_b64" inventory </dev/null)" || fail "inventário do backup falhou"
      actual_fingerprint="$(printf '%s\n' "$inventory_report" | sed -nE 's/^backup_runtime_fingerprint=([0-9a-f]{64})$/\1/p' | tail -n1)"
      [[ "$actual_fingerprint" == "$backup_fingerprint" ]] || fail "fingerprint diverge do preflight aprovado"
      printf '%s\n' "$inventory_report"
      runtime_python="/opt/pyp-backup-runtime/current/venv/bin/python"
      cli_code='import os,sys; os.environ["APP_ENV"]="production"; sys.path.insert(0,"/opt/pyp-backup-runtime/current/backend"); from app.platform_backup import production_cli; sys.argv=["production_cli.py",sys.argv[1]]; raise SystemExit(production_cli.main())'
      if [[ "$backup_mode" == "reconcile" ]]; then
        sudo -n "$runtime_python" -B -c "$cli_code" --reconcile-synthetic-destination
      else
        sudo -n "$runtime_python" -B -c "$cli_code" --bind-selected-destination
        sudo -n "$runtime_python" -B -c "$cli_code" --synthetic-destination-rehearsal
      fi
      exit $?
      ;;
  esac
fi

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
