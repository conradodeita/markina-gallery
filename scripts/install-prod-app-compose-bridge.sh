#!/usr/bin/env bash
# Protected production operation: install the reviewed bridge, never deploy.
set -Eeuo pipefail
umask 077
readonly REPOSITORY="conradodeita/markina-gallery"
readonly BRIDGE="/usr/local/sbin/markina-gallery-app-compose-bridge"
readonly BACKUPS="/var/backups/markina-gallery"
readonly PRIVATE_STATE="/var/lib/markina-gallery/app-compose-bridge"
fail() { echo "app-bridge-install: $*" >&2; exit 1; }
origin_is_canonical() {
  case "$1" in
    "https://github.com/$REPOSITORY.git"|"ssh://github.com/$REPOSITORY.git"|"git@github.com:$REPOSITORY.git") return 0 ;;
    *) return 1 ;;
  esac
}
[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$REPOSITORY" ]] || fail repository_invalid
[[ $# == 4 && "$1" == --support-sha && "$3" == --bridge-blob ]] || fail arguments_invalid
support_sha="$2"; bridge_blob="$4"
[[ "$support_sha" =~ ^[0-9a-f]{40}$ && "$bridge_blob" =~ ^[0-9a-f]{40}$ ]] || fail identity_invalid
[[ "$(hostname -s)" == clearbudget-vnic && "$(pwd -P)" == /opt/markina-gallery ]] || fail host_or_checkout_invalid
origin_url="$(git remote get-url origin)"
origin_is_canonical "$origin_url" || fail origin_invalid
[[ "$(git ls-remote origin refs/heads/main | cut -f1)" == "$support_sha" ]] || fail main_changed
[[ -z "$(git status --porcelain)" ]] || fail checkout_dirty
sudo -n true || fail sudo_unavailable
sudo -n test ! -L /var/lib/markina-gallery || fail state_parent_symlink
[[ "$(sudo -n stat -c '%U:%G:%a' /var/lib/markina-gallery)" == root:root:755 ]] || fail state_parent_invalid
sudo -n test ! -L "$BACKUPS" || fail backup_directory_symlink
case "$(sudo -n stat -c '%U:%G:%a' "$BACKUPS")" in root:root:700|root:root:750|root:root:755) ;; *) fail backup_directory_invalid ;; esac
exec {install_lock}</var/lib/markina-gallery/deploy-state/production-release.lock
flock -n "$install_lock" || fail release_lock_busy
if sudo -n test -e "$PRIVATE_STATE"; then
  sudo -n test ! -L "$PRIVATE_STATE" || fail private_state_symlink
  [[ "$(sudo -n stat -c '%U:%G:%a' "$PRIVATE_STATE")" == root:root:700 ]] || fail private_state_invalid
else
  sudo -n install -d -o root -g root -m 0700 "$PRIVATE_STATE"
fi
temporary="$(mktemp)"
staging="/usr/local/sbin/.markina-gallery-app-compose-bridge-$support_sha.new"
cleanup() { rm -f -- "$temporary"; }
trap cleanup EXIT
curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 \
  "https://raw.githubusercontent.com/$REPOSITORY/$support_sha/scripts/production_app_compose_bridge.py" \
  -o "$temporary" || fail candidate_unavailable
[[ "$(git hash-object "$temporary")" == "$bridge_blob" ]] || fail candidate_blob_mismatch
expected_sha="$(sha256sum "$temporary" | cut -d ' ' -f1)"
before_ids="$(docker ps -aq --no-trunc | LC_ALL=C sort)"
before="$(docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}' $before_ids | LC_ALL=C sort | sha256sum | cut -d ' ' -f1)"
backup=""
if sudo -n test -e "$BRIDGE"; then
  sudo -n test -f "$BRIDGE" && sudo -n test ! -L "$BRIDGE" || fail installed_bridge_invalid
  [[ "$(sudo -n stat -c '%U:%G:%a' "$BRIDGE")" == root:root:755 ]] || fail installed_bridge_metadata_invalid
  backup="$BACKUPS/app-compose-bridge-$(date -u +%Y%m%dT%H%M%SZ)-${support_sha:0:12}"
  sudo -n test ! -e "$backup" && sudo -n test ! -L "$backup" || fail backup_exists
  sudo -n install -o root -g root -m 0600 "$BRIDGE" "$backup"
  [[ "$(sudo -n sha256sum "$BRIDGE" | cut -d ' ' -f1)" == "$(sudo -n sha256sum "$backup" | cut -d ' ' -f1)" ]] || fail backup_mismatch
fi
sudo -n test ! -e "$staging" && sudo -n test ! -L "$staging" || fail staging_exists
sudo -n install -o root -g root -m 0755 "$temporary" "$staging"
sudo -n mv -T "$staging" "$BRIDGE"
if [[ "$(sudo -n stat -c '%U:%G:%a' "$BRIDGE")" != root:root:755 \
   || "$(sudo -n sha256sum "$BRIDGE" | cut -d ' ' -f1)" != "$expected_sha" ]]; then
  if [[ -n "$backup" ]]; then
    sudo -n install -o root -g root -m 0755 "$backup" "$staging"
    sudo -n mv -T "$staging" "$BRIDGE"
  fi
  fail installed_identity_mismatch
fi
if "$BRIDGE" --mode inventory --sha "$support_sha" hashes >/dev/null 2>&1; then fail nonroot_was_accepted; fi
if sudo -n "$BRIDGE" --mode inventory --sha "$support_sha" compose -- exec -T api sh >/dev/null 2>&1; then fail arbitrary_command_was_accepted; fi
after_ids="$(docker ps -aq --no-trunc | LC_ALL=C sort)"
[[ "$before_ids" == "$after_ids" ]] || fail container_ids_changed
after="$(docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}' $after_ids | LC_ALL=C sort | sha256sum | cut -d ' ' -f1)"
[[ "$before" == "$after" ]] || fail container_runtime_changed
# Fetch only the support objects needed by the pinned read-only executor.
# The active production checkout and its files remain at their original SHA.
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
[[ "$(git rev-parse origin/main)" == "$support_sha" ]] || fail fetched_main_changed
printf 'app_bridge_install=success\nbridge_identity=root:root:755\nbridge_sha256=%s\nbridge_blob=%s\ncontainers_unchanged=true\n' "$expected_sha" "$bridge_blob"
[[ -z "$backup" ]] || printf 'previous_bridge_backup=%s\n' "$backup"
