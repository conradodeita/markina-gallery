#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/deploy-prod-infinitepay-retirement.sh"

[[ "$(compose_label_for_service api)" == "$COMPOSE_FILE_LABEL" ]] \
  || { echo "Compose base API label diverge" >&2; exit 1; }
COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY=true
expected_api_label="$COMPOSE_FILE_LABEL,$ACTIVE_IMAGES_OVERLAY"
[[ "$(compose_label_for_service api)" == "$expected_api_label" ]] \
  || { echo "API deve reconhecer o overlay de imagens ativo durante o inventário" >&2; exit 1; }
[[ "$(compose_label_for_service web)" == "$expected_api_label" ]] \
  || { echo "web deve reconhecer o overlay de imagens ativo durante o inventário" >&2; exit 1; }
[[ "$(compose_label_for_service nginx)" == "$COMPOSE_FILE_LABEL" ]] \
  || { echo "nginx deve preservar sua proveniência sem overlay" >&2; exit 1; }
COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY=false
[[ "$(compose_label_for_service api)" == "$COMPOSE_FILE_LABEL" ]] \
  || { echo "Compose de destino não deve carregar overlay legado" >&2; exit 1; }

python3 - "$SCRIPT_DIR/deploy-prod-infinitepay-retirement.sh" <<'PY'
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

path = Path(sys.argv[1])
shell_source = path.read_text(encoding="utf-8")
start = shell_source.index("compose_binding_metadata()")
start = shell_source.index("python3 -c '\n", start) + len("python3 -c '\n")
end = shell_source.index("\n'", start)
python_source = shell_source[start:end]
compiled = compile(python_source, f"{path}:compose_binding_metadata", "exec")

with tempfile.TemporaryDirectory(prefix="retirement-compose-") as compose_dir:
    binding_path = Path(compose_dir) / ".env.infinitepay-bindings"
    binding_path.write_text("opaque fixture", encoding="utf-8")
    os.environ["MARKINA_RETIREMENT_COMPOSE_DIR"] = compose_dir
    os.environ.pop("MARKINA_RETIREMENT_BINDING_PATH_OVERRIDE", None)
    sys.stdin = io.StringIO(json.dumps({
        "services": {"api": {"env_file": [
            {"path": "${WHATSAPP_BINDINGS_ENV_FILE:-.env.whatsapp-bindings}"},
            {"path": "${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}"},
        ]}},
    }))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compiled, {})
    metadata = json.loads(output.getvalue())
    assert metadata["path"] == str(binding_path)
    assert metadata["type"] == "regular_file"
    assert metadata["compose_consumers"] == ["markina-gallery/api"]

    override_path = Path(compose_dir) / "custom-infinitepay-bindings.env"
    override_path.write_text("opaque fixture", encoding="utf-8")
    os.environ["MARKINA_RETIREMENT_BINDING_PATH_OVERRIDE"] = str(override_path)
    sys.stdin = io.StringIO(json.dumps({
        "services": {"api": {"env_file": [{
            "path": "${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}",
        }]}},
    }))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compiled, {})
    metadata = json.loads(output.getvalue())
    assert metadata["path"] == str(override_path)

    sys.stdin = io.StringIO(json.dumps({
        "services": {"api": {"env_file": [{"path": "${INFINITEPAY_CUSTOM_PATH:-bindings.env}"}]}},
    }))
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            exec(compiled, {})
    except SystemExit as error:
        assert "não suportada" in str(error)
    else:
        raise AssertionError("interpolação de caminho não reconhecida não foi recusada")
PY

calls=()
inventory() { calls+=(inventory); }
release() { calls+=(release); }

main --mode release --sha "$(printf 'a%.0s' {1..40})" \
  --approval-fingerprint "$(printf 'b%.0s' {1..64})"
[[ "${calls[*]}" == "release" ]] || { echo "modo release não chamou release()" >&2; exit 1; }

calls=()
main --mode inventory --sha "$(printf 'c%.0s' {1..40})"
[[ "${calls[*]}" == "inventory" ]] || { echo "modo inventory não chamou inventory()" >&2; exit 1; }

if ( main --mode unexpected --sha "$(printf 'd%.0s' {1..40})" ) >/dev/null 2>&1; then
  echo "modo desconhecido foi aceito" >&2
  exit 1
fi

echo "retirement deployment dispatch: ok"
python3 "$SCRIPT_DIR/test_retirement_release_flow.py"
python3 "$SCRIPT_DIR/test_retirement_legacy_worker.py"
