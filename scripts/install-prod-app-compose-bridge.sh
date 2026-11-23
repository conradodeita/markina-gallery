#!/usr/bin/env bash
# Protected production entry point for the pinned preflight-support coordinator.
set -Eeuo pipefail
umask 077
readonly REPOSITORY="conradodeita/markina-gallery"
readonly PROJECT_ROOT="/opt/markina-gallery"
readonly SUPPORT_HELPER="scripts/production_app_preflight_support.py"
fail() { printf 'app-bridge-install: %s\n' "$1" >&2; exit 1; }
origin_is_canonical() {
  case "$1" in
    "https://github.com/$REPOSITORY.git"|"ssh://github.com/$REPOSITORY.git"|"git@github.com:$REPOSITORY.git") return 0 ;;
    *) return 1 ;;
  esac
}

[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$REPOSITORY" ]] || fail repository_invalid
[[ $# -ge 8 && "$1" == --mode && "$3" == --support-sha \
  && "$5" == --helper-blob && "$7" == --connection-binding ]] || fail arguments_invalid
mode="$2"
support_sha="$4"
helper_blob="$6"
connection_binding="$8"
shift 8
[[ "$support_sha" =~ ^[0-9a-f]{40}$ && "$helper_blob" =~ ^[0-9a-f]{40}$ \
  && "$connection_binding" =~ ^[0-9a-f]{64}$ ]] || fail identity_invalid

support_args=(--mode "$mode" --support-sha "$support_sha" --connection-binding "$connection_binding")
case "$mode" in
  support-inventory)
    [[ $# == 0 ]] || fail arguments_invalid
    ;;
  prepare-support)
    [[ $# == 2 && "$1" == --approval-fingerprint && "$2" =~ ^[0-9a-f]{64}$ ]] || fail arguments_invalid
    support_args+=(--approval-fingerprint "$2")
    ;;
  restore-support-inventory)
    [[ $# == 2 && "$1" == --receipt-sha256 && "$2" =~ ^[0-9a-f]{64}$ ]] || fail arguments_invalid
    support_args+=(--receipt-sha256 "$2")
    ;;
  restore-support)
    [[ $# == 4 && "$1" == --approval-fingerprint && "$2" =~ ^[0-9a-f]{64}$ \
      && "$3" == --receipt-sha256 && "$4" =~ ^[0-9a-f]{64}$ ]] || fail arguments_invalid
    support_args+=(--approval-fingerprint "$2" --receipt-sha256 "$4")
    ;;
  *) fail operation_invalid ;;
esac

[[ "$(hostname -s 2>/dev/null)" == clearbudget-vnic \
  && "$(pwd -P 2>/dev/null)" == "$PROJECT_ROOT" ]] || fail host_or_checkout_invalid
origin_url="$(git remote get-url origin 2>/dev/null)" || fail origin_invalid
origin_is_canonical "$origin_url" || fail origin_invalid
remote_main="$(git ls-remote --exit-code origin refs/heads/main 2>/dev/null)" || fail main_unavailable
[[ "$remote_main" == "$support_sha"$'\t''refs/heads/main' ]] || fail main_changed
[[ -z "$(git status --porcelain 2>/dev/null)" ]] || fail checkout_dirty
sudo -n true >/dev/null 2>&1 || fail sudo_unavailable

refs_before="$(git for-each-ref --format='%(refname) %(objectname)' 2>/dev/null)" || fail refs_unavailable
git fetch --no-tags --no-write-fetch-head --refmap= origin refs/heads/main >/dev/null 2>&1 || fail support_objects_unavailable
refs_after="$(git for-each-ref --format='%(refname) %(objectname)' 2>/dev/null)" || fail refs_unavailable
[[ "$refs_before" == "$refs_after" ]] || fail support_fetch_changed_refs

actual_helper_blob="$(git rev-parse "$support_sha:$SUPPORT_HELPER" 2>/dev/null)" || fail support_helper_unavailable
[[ "$actual_helper_blob" == "$helper_blob" ]] || fail support_helper_blob_mismatch
git cat-file -e "$support_sha:$SUPPORT_HELPER" 2>/dev/null || fail support_helper_unavailable

# This is the existing protected SSH workflow and pinned Git object. The helper
# acquires the common host lock and enforces the approved four-operation contract.
if ! git cat-file blob "$support_sha:$SUPPORT_HELPER" 2>/dev/null \
  | sudo -n /usr/bin/python3.10 -B - "${support_args[@]}"; then
  exit 1
fi
