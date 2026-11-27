#!/bin/sh
set -eu

. /usr/share/doc/pyp-backup-tools/backup-tools.lock

restic version | grep -Eq "^restic ${RESTIC_VERSION}( |$)"
test "$(rclone version | sed -n '1p')" = "rclone v${RCLONE_VERSION}"
case "$(pg_dump --version)" in
  "pg_dump (PostgreSQL) ${POSTGRESQL_CLIENT_VERSION}"|"pg_dump (PostgreSQL) ${POSTGRESQL_CLIENT_VERSION} (Debian ${POSTGRESQL_CLIENT_PACKAGE_VERSION})") ;;
  *) echo 'backup_worker_pg_dump_version_mismatch' >&2; exit 1 ;;
esac
case "$(pg_restore --version)" in
  "pg_restore (PostgreSQL) ${POSTGRESQL_CLIENT_VERSION}"|"pg_restore (PostgreSQL) ${POSTGRESQL_CLIENT_VERSION} (Debian ${POSTGRESQL_CLIENT_PACKAGE_VERSION})") ;;
  *) echo 'backup_worker_pg_restore_version_mismatch' >&2; exit 1 ;;
esac
test -s /usr/share/doc/postgresql-client-17/copyright

umask 077
probe_root="$(mktemp -d /tmp/pyp-backup-tools-smoke.XXXXXX)"
trap 'rm -rf "$probe_root"' EXIT HUP INT TERM
mkdir -p "$probe_root/home" "$probe_root/repository" "$probe_root/cache"
printf '%s' 'synthetic-smoke-password-only' > "$probe_root/restic-password"
printf '[local]\ntype = local\n' > "$probe_root/rclone.conf"
chmod 0600 "$probe_root/restic-password" "$probe_root/rclone.conf"

export HOME="$probe_root/home"
export RESTIC_CACHE_DIR="$probe_root/cache"
export RESTIC_PASSWORD_FILE="$probe_root/restic-password"
export RCLONE_CONFIG="$probe_root/rclone.conf"
export RESTIC_REPOSITORY="rclone:local:$probe_root/repository"

marker='PYP_BACKUP_WORKER_SYNTHETIC_CANARY'
cd "$probe_root"
printf '%s' "$marker" > canary
restic init >/dev/null
restic backup canary >/dev/null
restic check --read-data >/dev/null
restic dump latest canary > restored
cmp --silent canary restored

python - "$probe_root/repository" "$marker" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
marker = sys.argv[2].encode("utf-8")
if any(marker in path.read_bytes() for path in root.rglob("*") if path.is_file()):
    raise SystemExit("backup_worker_plaintext_detected")
PY

printf 'backup_worker_tools_smoke=passed restic=%s rclone=%s postgresql_client=%s\n' \
  "$RESTIC_VERSION" "$RCLONE_VERSION" "$POSTGRESQL_CLIENT_VERSION"
