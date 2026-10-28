#!/usr/bin/env bash
# Executor one-shot. O workflow protegido fornece este arquivo por stdin; somente
# os helpers fixados e obtidos do SHA de suporte são carregados no host.
set -Eeuo pipefail
umask 077

readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly TARGET_SHA="0dd015a62447e0c8d4c6af16b381140c8118f2ec"
readonly INVENTORY_BLOB_SHA="1296ccb0e0f6295bc07b30837fc5043e7dac4db6"
readonly FLOW_BLOB_SHA="a5b898b614723e5ad73c583b73988034c5c16a3c"
readonly RELEASE_BLOB_SHA="9dc4c049eb3a890e42c6c1d0df9fa1daaa266dad"

fail() { echo "preview-adjustment-migration: $*" >&2; exit 1; }

[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$EXPECTED_REPOSITORY" ]] || fail "repositório divergente"
[[ "${MARKINA_PUBLIC_BASE_URL:-}" == "$PUBLIC_URL" ]] || fail "domínio divergente"
mode=""
approval_fingerprint=""
if [[ "$#" == 4 && "$1" == --mode && "$2" == prepare-backup && "$3" == --support-sha ]]; then
  mode=prepare-backup
elif [[ "$#" == 6 && "$1" == --mode && "$2" == release && "$3" == --support-sha \
  && "$5" == --approval-fingerprint ]]; then
  mode=release
  approval_fingerprint="$6"
  [[ "$approval_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint ausente ou inválido"
else
  fail "argumentos não permitidos"
fi
support_sha="$4"
[[ "$support_sha" =~ ^[0-9a-f]{40}$ ]] || fail "SHA de suporte inválido"

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

if [[ "$mode" == prepare-backup ]]; then
  PYTHONPATH="$temporary" python3 -B "$temporary/preview_adjustment_migration_release.py" prepare-backup \
    --support-sha "$support_sha"
else
  PYTHONPATH="$temporary" MARKINA_APPROVAL_FINGERPRINT="$approval_fingerprint" \
    python3 -B "$temporary/preview_adjustment_migration_release.py" release \
      --support-sha "$support_sha" --approval-fingerprint "$approval_fingerprint"
fi
