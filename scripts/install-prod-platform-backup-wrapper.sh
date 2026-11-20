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
cleanup() {
  rm -f -- "$temporary"
  sudo -n rm -f -- "$staging" "$rollback" >/dev/null 2>&1 || true
}
trap cleanup EXIT
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
sudo -n test ! -e "$staging" && sudo -n test ! -L "$staging" || fail "staging root-owned já existe"
sudo -n install -o root -g root -m 0755 -- "$temporary" "$staging" || fail "staging do wrapper falhou"
sudo -n mv -T -- "$staging" "$WRAPPER" || fail "troca atômica falhou"

installed_sha256="$(sudo -n sha256sum -- "$WRAPPER" | cut -d ' ' -f1)"
identity="$(sudo -n stat -c '%U:%G:%a' -- "$WRAPPER")"
if [[ "$identity" != root:root:755 || "$installed_sha256" != "$(sha256sum "$temporary" | cut -d ' ' -f1)" ]]; then
  sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
    && sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "identidade divergiu e rollback falhou"
  fail "identidade instalada diverge; wrapper anterior restaurado"
fi
if SSH_ORIGINAL_COMMAND="id" "$WRAPPER" >/dev/null 2>&1; then
  sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
    && sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "comando arbitrário aceito e rollback falhou"
  fail "wrapper aceitou comando arbitrário"
fi

backup_inventory="$(SSH_ORIGINAL_COMMAND="MARKINA_PLATFORM_BACKUP_INVENTORY_SHA=$support_sha" "$WRAPPER")" \
  || {
    sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
      && sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "inventário falhou e rollback do wrapper falhou"
    fail "inventário do runtime falhou; wrapper anterior restaurado"
  }
after_ids="$(docker ps -aq --no-trunc | LC_ALL=C sort)"
[[ "$before_ids" == "$after_ids" ]] || fail "IDs de containers mudaram"
after="$(docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}' $after_ids \
  | LC_ALL=C sort | sha256sum | cut -d ' ' -f1)"
[[ "$before" == "$after" ]] || fail "containers mudaram"

fingerprint="$(sed -nE 's/^backup_runtime_fingerprint=([0-9a-f]{64})$/\1/p' <<<"$backup_inventory" | tail -n1)"
[[ "$fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint do backup ausente"
printf '%s\n' "$backup_inventory"
printf 'backup_wrapper_install=success\nwrapper_blob=%s\nwrapper_sha256=%s\nwrapper_identity=%s\n' \
  "$wrapper_blob" "$installed_sha256" "$identity"
printf 'previous_wrapper_backup_sha256=%s\n' "$backup_sha256"
printf 'application_and_shared_containers_unchanged=true\nbackup_runtime_fingerprint=%s\n' "$fingerprint"
