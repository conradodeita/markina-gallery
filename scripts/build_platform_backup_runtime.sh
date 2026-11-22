#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly LOCK_FILE="$REPOSITORY_ROOT/scripts/backup_runtime/requirements-py310-arm64.lock"

fail() { echo "platform-backup-runtime-build: $*" >&2; exit 1; }

[[ $# == 2 ]] || fail "uso interno inválido"
readonly SOURCE_SHA="$1"
readonly OUTPUT_BUNDLE="$2"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA inválido"
[[ -n "$OUTPUT_BUNDLE" && ! -e "$OUTPUT_BUNDLE" && ! -L "$OUTPUT_BUNDLE" ]] || fail "saída precisa ser nova"

wheelhouse="$(mktemp -d)"
trap 'rm -rf -- "$wheelhouse"' EXIT

python -m pip download \
  --only-binary=:all: --no-deps --require-hashes \
  --dest "$wheelhouse" \
  --python-version 3.10 --implementation cp \
  --abi cp310 --abi abi3 --abi none \
  --platform manylinux_2_28_aarch64 \
  --platform manylinux_2_17_aarch64 \
  --platform manylinux2014_aarch64 \
  -r "$LOCK_FILE"

build_result="$(python "$REPOSITORY_ROOT/scripts/platform_backup_runtime_artifact.py" build \
  --sha "$SOURCE_SHA" --wheelhouse "$wheelhouse" --output "$OUTPUT_BUNDLE")" \
  || fail "não foi possível montar o pacote"
bundle_sha256="$(python -c 'import json,sys; value=json.load(sys.stdin); print(value.get("bundle_sha256", ""))' <<<"$build_result")"
[[ "$bundle_sha256" =~ ^[0-9a-f]{64}$ ]] || fail "digest do pacote inválido"
python "$REPOSITORY_ROOT/scripts/platform_backup_runtime_artifact.py" verify \
  --sha "$SOURCE_SHA" --bundle "$OUTPUT_BUNDLE" --bundle-sha256 "$bundle_sha256" \
  >/dev/null || fail "pacote não passou pela verificação posterior"
printf 'source_sha=%s\nbundle_sha256=%s\n' "$SOURCE_SHA" "$bundle_sha256"
