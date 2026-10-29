#!/usr/bin/env bash
# Operador one-shot; código imutável em memória, sem staging para inventário.
set -Eeuo pipefail
umask 077
fail() { echo 'nginx-provenance: operação recusada' >&2; exit 1; }
readonly EXPECTED_REPOSITORY='conradodeita/markina-gallery'
readonly MODULE_BLOB_SHA='996dce9eb370daa0ec99872ed96249265eed6a39'
[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$EXPECTED_REPOSITORY" ]] || fail
[[ "${MARKINA_PUBLIC_BASE_URL:-}" == 'https://markina.pickyourpic.com.br' ]] || fail
[[ "$#" == 5 ]] || fail
mode="$1"; support_sha="$2"; approval="$3"; bundle="$4"; recovery_approval="$5"
case "$mode" in inventory|prepare|release|recovery-inventory|recover) ;; *) fail ;; esac
[[ "$support_sha" =~ ^[0-9a-f]{40}$ ]] || fail
if [[ "$mode" != inventory ]]; then [[ "$approval" =~ ^[0-9a-f]{64}$ ]] || fail; fi
if [[ "$mode" == release || "$mode" == recovery-inventory || "$mode" == recover ]]; then
  [[ "$bundle" =~ ^[0-9a-f]{64}$ ]] || fail
fi
if [[ "$mode" == recover ]]; then [[ "$recovery_approval" =~ ^[0-9a-f]{64}$ ]] || fail; fi
cd /opt/markina-gallery
[[ "$(pwd -P)" == /opt/markina-gallery ]] || fail
[[ "$(git remote get-url origin)" == "https://github.com/$EXPECTED_REPOSITORY.git" ]] || fail
remote_main="$(GIT_OPTIONAL_LOCKS=0 git ls-remote origin refs/heads/main)" || fail
[[ "${remote_main%%$'\t'*}" == "$support_sha" ]] || fail
python3 -B - "$support_sha" "$mode" "$approval" "$bundle" "$recovery_approval" "$MODULE_BLOB_SHA" <<'PY'
import hashlib, sys, urllib.request, urllib.parse
try:
    sha, mode, approval, bundle, recovery, blob = sys.argv[1:]
    url = 'https://raw.githubusercontent.com/conradodeita/markina-gallery/' + sha + '/scripts/nginx_compose_provenance.py'
    with urllib.request.urlopen(url, timeout=20) as response:
        target = urllib.parse.urlsplit(response.geturl())
        if target.scheme != 'https' or target.hostname != 'raw.githubusercontent.com':
            raise ValueError()
        data = response.read(262145)
    if len(data) > 262144 or hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest() != blob:
        raise ValueError()
except Exception:
    raise SystemExit('nginx-provenance: fonte imutável indisponível') from None
sys.argv = ['nginx_compose_provenance.py', mode, '--approval', approval, '--bundle', bundle,
            '--recovery-approval', recovery]
exec(compile(data, 'nginx_compose_provenance.py', 'exec'), {'__name__': '__main__'})
PY
