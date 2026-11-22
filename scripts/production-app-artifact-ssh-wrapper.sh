#!/usr/bin/env bash
# Recebedor de bundle de imagens CI. Instalar root-owned e associar somente à
# chave exclusiva de upload com restrict,command= em authorized_keys.
set -Eeuo pipefail
umask 077

readonly MAX_BUNDLE_BYTES=4294967296
fail() { echo "production-app-artifact: $*" >&2; exit 1; }

[[ $# -eq 0 ]] || fail "argumentos adicionais não permitidos"
[[ ! -t 0 ]] || fail "TTY não permitido"
original_command="${SSH_ORIGINAL_COMMAND:-}"
if [[ "$original_command" =~ ^MARKINA_APP_ARTIFACT_UPLOAD_SHA=([0-9a-f]{40})_BUNDLE_SHA256=([0-9a-f]{64})$ ]]; then
  target_sha="${BASH_REMATCH[1]}"
  expected_bundle_sha="${BASH_REMATCH[2]}"
else
  fail "comando de upload não permitido"
fi

readonly artifact_dir="/tmp/markina-gallery-app-artifacts-${UID}"
[[ ! -L "$artifact_dir" ]] || fail "diretório de artefatos é symlink"
if [[ ! -e "$artifact_dir" ]]; then
  mkdir -m 700 -- "$artifact_dir" || fail "não foi possível criar diretório temporário"
fi
[[ -d "$artifact_dir" && ! -L "$artifact_dir" ]] || fail "diretório temporário inválido"
[[ "$(stat -c '%u' -- "$artifact_dir")" == "$UID" ]] || fail "diretório pertence a outro usuário"
chmod 700 -- "$artifact_dir" || fail "não foi possível proteger diretório temporário"

python3 -c '
import hashlib, os, sys, tempfile

directory, target_sha, expected, limit_text = sys.argv[1:]
limit = int(limit_text)
fd, temporary = tempfile.mkstemp(prefix="." + target_sha + ".upload-", dir=directory)
digest = hashlib.sha256()
size = 0
try:
    with os.fdopen(fd, "wb") as output:
        while True:
            chunk = sys.stdin.buffer.read(min(1024 * 1024, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError("bundle excede o limite de bytes")
            digest.update(chunk)
            output.write(chunk)
        if size == 0:
            raise ValueError("bundle vazio")
        output.flush()
        os.fsync(output.fileno())
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError("SHA-256 do bundle diverge")
    final = os.path.join(directory, target_sha + ".bundle")
    os.replace(temporary, final)
    directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    print("bundle_received=" + target_sha + " sha256=" + actual + " bytes=" + str(size))
except Exception as exc:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    print("production-app-artifact: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
' "$artifact_dir" "$target_sha" "$expected_bundle_sha" "$MAX_BUNDLE_BYTES"
