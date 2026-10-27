#!/usr/bin/env bash
# Executor one-shot. O workflow protegido fornece este arquivo por stdin; somente
# os helpers fixados e obtidos do SHA de suporte são carregados no host.
set -Eeuo pipefail
umask 077

readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly TARGET_SHA="0dd015a62447e0c8d4c6af16b381140c8118f2ec"
readonly INVENTORY_BLOB_SHA="8436db2256cd31d9e4ae5f11e025486272655604"
readonly FLOW_BLOB_SHA="e629474c68a6cddc1a34b09f46771464fa96a4d8"
readonly RELEASE_BLOB_SHA="a3a7c32366cc4758847cdc0a1b4b0f2f617abb97"

fail() { echo "preview-adjustment-migration: $*" >&2; exit 1; }

[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$EXPECTED_REPOSITORY" ]] || fail "repositório divergente"
[[ "${MARKINA_PUBLIC_BASE_URL:-}" == "$PUBLIC_URL" ]] || fail "domínio divergente"
[[ "$#" == 6 && "$1" == --mode && "$2" == release && "$3" == --support-sha \
  && "$5" == --approval-fingerprint ]] || fail "argumentos não permitidos"
support_sha="$4"
approval_fingerprint="$6"
[[ "$support_sha" =~ ^[0-9a-f]{40}$ ]] || fail "SHA de suporte inválido"
[[ "$approval_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint ausente ou inválido"

cd /opt/markina-gallery
[[ "$(pwd -P)" == /opt/markina-gallery ]] || fail "raiz de projeto inesperada"
remote_main="$(git ls-remote origin refs/heads/main)" || fail "main indisponível"
[[ "${remote_main%%$'\t'*}" == "$support_sha" ]] || fail "SHA de suporte não é main atual"

temporary="$(mktemp -d /var/lib/markina-gallery/deploy-state/preview-migration-run.XXXXXX)" || fail "staging indisponível"
chmod 700 "$temporary"
trap 'rm -rf -- "$temporary"' EXIT

fetch_pinned() {
  local name="$1" expected="$2" url="$PUBLIC_URL"
  url="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$support_sha/scripts/$name"
  curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 "$url" -o "$temporary/$name" \
    || fail "helper indisponível: $name"
  local actual
  actual="$(git hash-object -- "$temporary/$name")"
  [[ "$actual" == "$expected" ]] || fail "helper diverge do blob aprovado: $name"
}

fetch_pinned preview_adjustment_migration_inventory.py "$INVENTORY_BLOB_SHA"
fetch_pinned preview_adjustment_migration_release_flow.py "$FLOW_BLOB_SHA"
fetch_pinned preview_adjustment_migration_release.py "$RELEASE_BLOB_SHA"

PYTHONPATH="$temporary" MARKINA_APPROVAL_FINGERPRINT="$approval_fingerprint" \
  python3 -B "$temporary/preview_adjustment_migration_release.py" release \
    --support-sha "$support_sha" --approval-fingerprint "$approval_fingerprint"
