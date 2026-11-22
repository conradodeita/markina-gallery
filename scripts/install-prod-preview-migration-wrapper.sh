#!/usr/bin/env bash
# Instala somente o wrapper root-owned de preflight já versionado e revisado.
set -Eeuo pipefail
umask 077

readonly EXPECTED_REPOSITORY="conradodeita/markina-gallery"
readonly WRAPPER="/usr/local/sbin/markina-gallery-preflight-ssh-wrapper"
readonly BACKUP_DIR="/var/backups/markina-gallery"

fail() { echo "preview-wrapper-install: $*" >&2; exit 1; }

[[ "${MARKINA_EXPECTED_REPOSITORY:-}" == "$EXPECTED_REPOSITORY" ]] || fail "repositório divergente"
[[ "$#" == 6 && "$1" == --mode && "$2" == install && "$3" == --support-sha \
  && "$5" == --wrapper-blob ]] || fail "argumentos não permitidos"
support_sha="$4"
wrapper_blob="$6"
[[ "$support_sha" =~ ^[0-9a-f]{40}$ ]] || fail "SHA de suporte inválido"
[[ "$wrapper_blob" =~ ^[0-9a-f]{40}$ ]] || fail "blob do wrapper inválido"

cd /opt/markina-gallery
[[ "$(pwd -P)" == /opt/markina-gallery ]] || fail "raiz de projeto inesperada"
repository="$(git remote get-url origin)" || fail "remoto Git indisponível"
[[ "$repository" == 'https://github.com/conradodeita/markina-gallery.git' \
  || "$repository" == 'https://github.com/conradodeita/markina-gallery' \
  || "$repository" == 'git@github.com:conradodeita/markina-gallery.git' ]] || fail "repositório divergente"
[[ "$(hostname -s)" == clearbudget-vnic ]] || fail "host de instalação divergente"
remote_main="$(git ls-remote origin refs/heads/main)" || fail "main indisponível"
[[ "${remote_main%%$'\t'*}" == "$support_sha" ]] || fail "SHA de suporte não é main atual"

authorized_keys="$HOME/.ssh/authorized_keys"
[[ -f "$authorized_keys" && ! -L "$authorized_keys" ]] || fail "authorized_keys ausente ou inseguro"
grep -Fq 'restrict,command="/usr/local/sbin/markina-gallery-preflight-ssh-wrapper"' \
  "$authorized_keys" || fail "comando forçado read-only não está presente"
sudo -n true || fail "sudo não interativo indisponível"
sudo -n test -f "$WRAPPER" && sudo -n test ! -L "$WRAPPER" || fail "wrapper instalado ausente ou inseguro"
sudo -n test -d "$BACKUP_DIR" && sudo -n test ! -L "$BACKUP_DIR" || fail "diretório de backup root-owned ausente ou inseguro"

temporary="$(mktemp)" || fail "staging local indisponível"
staging="/usr/local/sbin/.markina-gallery-preflight-ssh-wrapper.${support_sha}.new"
rollback="/usr/local/sbin/.markina-gallery-preflight-ssh-wrapper.${support_sha}.rollback"
cleanup() {
  rm -f -- "$temporary"
  sudo -n rm -f -- "$staging" "$rollback" >/dev/null 2>&1 || true
}
trap cleanup EXIT
raw_url="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$support_sha/scripts/production-preflight-ssh-wrapper.sh"
curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' --tlsv1.2 \
  "$raw_url" -o "$temporary" || fail "wrapper versionado indisponível"
actual_blob="$(git hash-object -- "$temporary")"
[[ "$actual_blob" == "$wrapper_blob" ]] || fail "blob do wrapper diverge"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$BACKUP_DIR/preflight-ssh-wrapper-${stamp}-preview-migration-${support_sha:0:12}"
sudo -n test ! -e "$backup" || fail "backup da instalação já existe"
sudo -n install -o root -g root -m 0600 -- "$WRAPPER" "$backup" || fail "backup root-owned falhou"
backup_sha="$(sudo -n sha256sum -- "$backup" | cut -d ' ' -f1)"
[[ "$backup_sha" =~ ^[0-9a-f]{64}$ ]] || fail "checksum do backup inválido"

sudo -n test ! -e "$staging" || fail "staging root-owned já existe"
sudo -n install -o root -g root -m 0755 -- "$temporary" "$staging" || fail "staging root-owned falhou"
sudo -n mv -T -- "$staging" "$WRAPPER" || fail "troca atômica do wrapper falhou"

identity="$(sudo -n stat -c '%U:%G:%a' -- "$WRAPPER")"
installed_sha="$(sudo -n sha256sum -- "$WRAPPER" | cut -d ' ' -f1)"
[[ "$identity" == 'root:root:755' && "$installed_sha" == "$(sha256sum "$temporary" | cut -d ' ' -f1)" ]] \
  || {
    sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
      && sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "identidade divergiu e recuperação do wrapper falhou"
    fail "identidade ou checksum instalado diverge; wrapper anterior restaurado"
  }
if SSH_ORIGINAL_COMMAND='id' "$WRAPPER" >/dev/null 2>&1; then
  sudo -n install -o root -g root -m 0755 -- "$backup" "$rollback" \
    && sudo -n mv -T -- "$rollback" "$WRAPPER" || fail "comando arbitrário aceito e recuperação do wrapper falhou"
  fail "wrapper aceitou comando arbitrário"
fi

printf 'preview_wrapper_install=success\n'
printf 'wrapper_sha256=%s\n' "$installed_sha"
printf 'wrapper_identity=%s\n' "$identity"
printf 'previous_wrapper_backup=%s\n' "$backup"
printf 'previous_wrapper_sha256=%s\n' "$backup_sha"
