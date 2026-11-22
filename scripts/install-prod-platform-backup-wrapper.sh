#!/usr/bin/env bash
# Instala exclusivamente o forced-command root-owned do operador de backup.
set -Eeuo pipefail
umask 077

readonly REPOSITORY="conradodeita/markina-gallery"
readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
readonly WRAPPER="/usr/local/sbin/markina-gallery-preflight-ssh-wrapper"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly LOCK_FILE="$STATE_DIR/production-release.lock"
readonly BACKUP_DIR="/var/backups/markina-gallery"

fail() { echo "platform-backup-wrapper-install: $*" >&2; exit 1; }

[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$REPOSITORY" ]] || fail "repositório divergente"
[[ $# == 6 && "$1" == --sha && "$3" == --wrapper-blob \
   && "$5" == --approval-fingerprint ]] || fail "argumentos não permitidos"
support_sha="$2"
wrapper_blob="$4"
approval_fingerprint="$6"
[[ "$support_sha" =~ ^[0-9a-f]{40}$ && "$wrapper_blob" =~ ^[0-9a-f]{40}$ \
   && "$approval_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "identidade inválida"
[[ "$(hostname -s)" == "$EXPECTED_HOST" ]] || fail "host divergente"
cd "$PROJECT_ROOT"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "checkout divergente"
case "$(git remote get-url origin)" in
  "https://github.com/$REPOSITORY"|"https://github.com/$REPOSITORY.git"|\
  "ssh://github.com/$REPOSITORY.git"|"git@github.com:$REPOSITORY.git") ;;
  *) fail "remoto divergente" ;;
esac
[[ "$(git ls-remote origin refs/heads/main | cut -f1)" == "$support_sha" ]] \
  || fail "SHA não é a ponta atual da main"
[[ -z "$(git status --porcelain)" ]] || fail "checkout operacional contém alterações"

sudo -n true || fail "sudo não interativo indisponível"
sudo -n test ! -L "$STATE_DIR" || fail "diretório de estado é symlink"
[[ "$(sudo -n stat -c '%U:%G:%a' -- "$STATE_DIR")" == ubuntu:ubuntu:700 ]] \
  || fail "diretório de estado inseguro"
sudo -n test -f "$LOCK_FILE" && sudo -n test ! -L "$LOCK_FILE" || fail "lock comum ausente ou inseguro"
[[ "$(sudo -n stat -c '%U:%G:%a' -- "$LOCK_FILE")" == ubuntu:ubuntu:600 ]] \
  || fail "lock comum inseguro"
sudo -n test -d "$BACKUP_DIR" && sudo -n test ! -L "$BACKUP_DIR" || fail "diretório de backup indisponível"
case "$(sudo -n stat -c '%U:%G:%a' -- "$BACKUP_DIR")" in root:root:700|root:root:750|root:root:755) ;; *) fail "diretório de backup inseguro" ;; esac
exec {release_lock}<"$LOCK_FILE"
flock -n "$release_lock" || fail "outro release está em andamento"
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main || fail "main aprovada indisponível"
[[ "$(git rev-parse origin/main)" == "$support_sha" ]] || fail "referência local diverge da main aprovada"

inventory_source="$(mktemp)"
temporary=""
staging=""
rollback=""
cleanup() {
  [[ -z "$temporary" ]] || rm -f -- "$temporary" >/dev/null 2>&1 || true
  rm -f -- "$inventory_source" >/dev/null 2>&1 || true
  local protected_artifacts=()
  [[ -z "$staging" ]] || protected_artifacts+=("$staging")
  [[ -z "$rollback" ]] || protected_artifacts+=("$rollback")
  if ((${#protected_artifacts[@]} > 0)); then
    sudo -n rm -f -- "${protected_artifacts[@]}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

read_approved_inventory_source() {
  local approved_sha="$1"
  local destination="$2"
  local module_path="scripts/platform_backup_runtime_inventory.py"
  local expected_blob actual_blob
  expected_blob="$(git rev-parse "$approved_sha:$module_path" 2>/dev/null)" || return 1
  [[ "$expected_blob" =~ ^[0-9a-f]{40}$ ]] || return 1
  git show "$approved_sha:$module_path" > "$destination" 2>/dev/null || return 1
  actual_blob="$(git hash-object -- "$destination" 2>/dev/null)" || return 1
  [[ "$actual_blob" == "$expected_blob" ]]
}

read_approved_inventory_source "$support_sha" "$inventory_source" \
  || fail "módulo de diagnóstico aprovado indisponível ou inválido"
inventory_b64="$(base64 -w0 -- "$inventory_source")"
diagnostic_bootstrap="$(cat <<'PY'
import base64
import sys
import types

module = types.ModuleType("platform_backup_runtime_inventory")
module.__file__ = "platform_backup_runtime_inventory.py"
sys.modules[module.__name__] = module
exec(compile(base64.b64decode(sys.argv[1]), module.__file__, "exec"), module.__dict__)
raise SystemExit(module.diagnostic_main())
PY
)"

current_inventory="$(SSH_ORIGINAL_COMMAND="MARKINA_APP_TARGET_SHA=$support_sha" "$WRAPPER")" \
  || fail "preflight read-only falhou"
current_fingerprint="$(sed -nE 's/^approval_fingerprint=([0-9a-f]{64})$/\1/p' <<<"$current_inventory" | tail -n1)"
[[ "$current_fingerprint" == "$approval_fingerprint" ]] || fail "fingerprint mudou após aprovação"

before_ids="$(docker ps -aq --no-trunc | LC_ALL=C sort)"
[[ -n "$before_ids" ]] || fail "inventário de containers vazio"
before="$(docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}' $before_ids \
  | LC_ALL=C sort | sha256sum | cut -d ' ' -f1)"

sudo -n test -f "$WRAPPER" && sudo -n test ! -L "$WRAPPER" || fail "wrapper atual ausente ou inseguro"
[[ "$(sudo -n stat -c '%U:%G:%a' -- "$WRAPPER")" == root:root:755 ]] \
  || fail "metadados do wrapper atual divergentes"
temporary="$(mktemp)"
staging="/usr/local/sbin/.markina-gallery-preflight-ssh-wrapper.$support_sha.new"
rollback="/usr/local/sbin/.markina-gallery-preflight-ssh-wrapper.$support_sha.rollback"
raw_url="https://raw.githubusercontent.com/$REPOSITORY/$support_sha/scripts/production-preflight-ssh-wrapper.sh"
curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 \
  "$raw_url" -o "$temporary" || fail "wrapper aprovado indisponível"
[[ "$(git hash-object -- "$temporary")" == "$wrapper_blob" ]] || fail "blob do wrapper diverge"
"$BASH" -n "$temporary" || fail "sintaxe do wrapper inválida"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$BACKUP_DIR/preflight-ssh-wrapper-${stamp}-platform-backup-${support_sha:0:12}"
sudo -n test ! -e "$backup" && sudo -n test ! -L "$backup" || fail "backup já existe"
sudo -n test ! -e "$staging" && sudo -n test ! -L "$staging" || fail "staging root-owned já existe"
sudo -n test ! -e "$rollback" && sudo -n test ! -L "$rollback" || fail "rollback root-owned já existe"
sudo -n install -o root -g root -m 0600 -- "$WRAPPER" "$backup" || fail "backup do wrapper falhou"
backup_sha256="$(sudo -n sha256sum -- "$backup" | cut -d ' ' -f1)"
[[ "$backup_sha256" =~ ^[0-9a-f]{64}$ ]] || fail "hash do backup inválido"
restore_previous_wrapper() {
  sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
    || fail "rollback do wrapper falhou"
  sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "rollback do wrapper falhou"
}
sudo -n test ! -e "$staging" && sudo -n test ! -L "$staging" || fail "staging root-owned já existe"
sudo -n install -o root -g root -m 0755 -- "$temporary" "$staging" || fail "staging do wrapper falhou"
sudo -n mv -T -- "$staging" "$WRAPPER" || fail "troca atômica falhou"

installed_sha256="$(sudo -n sha256sum -- "$WRAPPER" | cut -d ' ' -f1)" \
  || { restore_previous_wrapper; fail "hash instalado indisponível; wrapper anterior restaurado"; }
identity="$(sudo -n stat -c '%U:%G:%a' -- "$WRAPPER")" \
  || { restore_previous_wrapper; fail "identidade instalada indisponível; wrapper anterior restaurado"; }
if [[ "$identity" != root:root:755 || "$installed_sha256" != "$(sha256sum "$temporary" | cut -d ' ' -f1)" ]]; then
  restore_previous_wrapper
  fail "identidade instalada diverge; wrapper anterior restaurado"
fi
if SSH_ORIGINAL_COMMAND="id" "$WRAPPER" >/dev/null 2>&1; then
  restore_previous_wrapper
  fail "wrapper aceitou comando arbitrário"
fi

backup_diagnostic="$(sudo -n /usr/bin/python3.10 -B -c "$diagnostic_bootstrap" "$inventory_b64")" \
  || {
    restore_previous_wrapper
    fail "diagnóstico do runtime falhou; wrapper anterior restaurado"
  }
if ! /usr/bin/python3.10 - "$backup_diagnostic" <<'PY' >/dev/null
import json
import sys

line = sys.argv[1]
prefix = "backup_runtime_container_diagnostics="
try:
    if "\n" in line or "\r" in line or not line.startswith(prefix):
        raise ValueError
    report = json.loads(line[len(prefix):])
    if (type(report) is not dict or set(report) != {"schema_version", "roles"}
            or type(report.get("schema_version")) is not int or report["schema_version"] != 1):
        raise ValueError
    roles = report["roles"]
    if type(roles) is not dict or set(roles) != {"api", "web", "db"}:
        raise ValueError
    fields = {"records", "running", "stopped", "unknown"}
    for role in roles.values():
        if type(role) is not dict or set(role) != fields:
            raise ValueError
        if any(type(value) is not int or value < 0 for value in role.values()):
            raise ValueError
        if role["records"] > 512 or role["records"] != role["running"] + role["stopped"] + role["unknown"]:
            raise ValueError
except (TypeError, ValueError):
    raise SystemExit(1)
PY
then
  restore_previous_wrapper
  fail "diagnóstico retornou formato inválido; wrapper anterior restaurado"
fi
after_ids="$(docker ps -aq --no-trunc | LC_ALL=C sort)" \
  || { restore_previous_wrapper; fail "inventário pós-instalação falhou; wrapper anterior restaurado"; }
[[ "$before_ids" == "$after_ids" ]] \
  || { restore_previous_wrapper; fail "IDs de containers mudaram; wrapper anterior restaurado"; }
after="$(docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}' $after_ids \
  | LC_ALL=C sort | sha256sum | cut -d ' ' -f1)" \
  || { restore_previous_wrapper; fail "snapshot pós-instalação falhou; wrapper anterior restaurado"; }
[[ "$before" == "$after" ]] \
  || { restore_previous_wrapper; fail "containers mudaram; wrapper anterior restaurado"; }

printf '%s\n' "$backup_diagnostic"
printf 'backup_wrapper_install=success\nwrapper_blob=%s\nwrapper_sha256=%s\nwrapper_identity=%s\n' \
  "$wrapper_blob" "$installed_sha256" "$identity"
printf 'previous_wrapper_backup_sha256=%s\n' "$backup_sha256"
printf 'application_and_shared_containers_unchanged=true\n'
