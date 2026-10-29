#!/usr/bin/env bash
# Operador one-shot; código imutável em memória, sem staging para inventário.
set -Eeuo pipefail
umask 077
fail() {
  local code="${1:-preflight_recusado}"
  case "$code" in
    repositorio_config_invalido|url_publica_invalida|argumentos_invalidos|operacao_invalida|sha_suporte_invalido|aprovacao_invalida|bundle_invalido|aprovacao_recuperacao_invalida|diretorio_checkout_invalido|remoto_origem_indisponivel|remoto_origem_invalido|main_remota_indisponivel|main_remota_divergente) ;;
    *) code=preflight_recusado ;;
  esac
  printf 'nginx-provenance: preflight recusado (%s)\n' "$code" >&2
  exit 1
}
readonly EXPECTED_REPOSITORY='conradodeita/markina-gallery'
readonly MODULE_BLOB_SHA='128121277e0e161afd71129c70421530f61b7401'
is_expected_repository_origin() {
  local candidate="${1,,}"
  case "$candidate" in
    "https://github.com/$EXPECTED_REPOSITORY.git"|"https://github.com/$EXPECTED_REPOSITORY"|"git@github.com:$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY"|"ssh://git@github.com/$EXPECTED_REPOSITORY.git"|"ssh://git@github.com/$EXPECTED_REPOSITORY") return 0 ;;
    *) return 1 ;;
  esac
}
[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$EXPECTED_REPOSITORY" ]] || fail repositorio_config_invalido
[[ "${MARKINA_PUBLIC_BASE_URL:-}" == 'https://markina.pickyourpic.com.br' ]] || fail url_publica_invalida
[[ "$#" == 5 ]] || fail argumentos_invalidos
mode="$1"; support_sha="$2"; approval="$3"; bundle="$4"; recovery_approval="$5"
case "$mode" in inventory|prepare|release|recovery-inventory|recover) ;; *) fail operacao_invalida ;; esac
[[ "$support_sha" =~ ^[0-9a-f]{40}$ ]] || fail sha_suporte_invalido
if [[ "$mode" != inventory ]]; then [[ "$approval" =~ ^[0-9a-f]{64}$ ]] || fail aprovacao_invalida; fi
if [[ "$mode" == release || "$mode" == recovery-inventory || "$mode" == recover ]]; then
  [[ "$bundle" =~ ^[0-9a-f]{64}$ ]] || fail bundle_invalido
fi
if [[ "$mode" == recover ]]; then [[ "$recovery_approval" =~ ^[0-9a-f]{64}$ ]] || fail aprovacao_recuperacao_invalida; fi
cd /opt/markina-gallery 2>/dev/null || fail diretorio_checkout_invalido
[[ "$(pwd -P 2>/dev/null)" == /opt/markina-gallery ]] || fail diretorio_checkout_invalido
origin_url="$(git remote get-url origin 2>/dev/null)" || fail remoto_origem_indisponivel
is_expected_repository_origin "$origin_url" || fail remoto_origem_invalido
if ! remote_main="$(GIT_OPTIONAL_LOCKS=0 git ls-remote origin refs/heads/main 2>/dev/null)"; then
  fail main_remota_indisponivel
fi
[[ "${remote_main%%$'\t'*}" == "$support_sha" ]] || fail main_remota_divergente
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
