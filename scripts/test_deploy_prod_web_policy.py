"""Guarda de escopo e gates do procedimento web-only."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/deploy-prod-web.sh").read_text(encoding="utf-8")
APP = (ROOT / "scripts/deploy-prod-app-services.sh").read_text(encoding="utf-8")
LOCK = (ROOT / "scripts/deploy-prod-lock.sh").read_text(encoding="utf-8")
STATE = (ROOT / "scripts/deploy-prod-state.sh").read_text(encoding="utf-8")


def main():
    for name, text in (("web", SCRIPT), ("app", APP)):
        for fragment in ('GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1', 'release_load_support || fail',
                         'acquire_production_deploy_lock', 'release_assert_web_identity'):
            if fragment not in text:
                raise AssertionError(f"{name}: gate ausente {fragment}")
        if re.search(r"git (?:fetch|init)|mktemp|source /dev/stdin", text):
            raise AssertionError(f"{name}: inventário deve usar somente memória e objetos locais")
    for fragment in ('readonly PROJECT_ROOT="/opt/markina-gallery"', 'readonly PROJECT_NAME="markina-gallery"',
                     'readonly COMPOSE_FILE="docker/docker-compose.yml"', 'readonly ENV_FILE="docker/.env.homolog"',
                     'readonly PUBLIC_URL="https://markina.pickyourpic.com.br"',
                     'compose build web', 'compose up -d --no-deps --no-build --force-recreate web',
                     'verify_scope "$ACTIVE_SHA" "$TARGET_SHA"', 'approval_fingerprint',
                     'web-pending.identity', 'web-previous.identity', 'release_check_image "$RECOVERY_IMAGE" true',
                     'check_web_after_change "$RECOVERY_IMAGE"', 'release_non_web_snapshot', '== 404'):
        if fragment not in SCRIPT:
            raise AssertionError(f"web: contrato ausente {fragment}")
    if 'exec {production_deploy_lock_fd}<' not in LOCK or 'flock -n "$production_deploy_lock_fd"' not in LOCK:
        raise AssertionError("lock deve abrir arquivo existente para leitura e adquirir exclusividade")
    if re.search(r'exec .*?>', LOCK):
        raise AssertionError("lock não pode criar/truncar arquivo")
    for action, arguments in re.findall(r"compose\s+(build|up)\s+([^\n]+)", SCRIPT):
        expected = "web; }" if action == "build" else "-d --no-deps --no-build --force-recreate web; }"
        if arguments.strip() != expected:
            raise AssertionError(f"mutação fora do contrato: {action} {arguments}")
    for pattern in (r"docker\s+(?:system|image)\s+prune", r"compose\s+(?:down|exec|restart|stop|run)",
                    r"(?:rm|rmdir)\s+-[A-Za-z]*r", r"alembic", r"nginx -s"):
        if re.search(pattern, SCRIPT):
            raise AssertionError(f"operação fora do escopo web: {pattern}")
    if 'source <(printf' not in STATE:
        raise AssertionError("suporte deve ser carregado sem here-string grande/temporários")
    for name in ('web', 'app-services'):
        text = (ROOT / f"scripts/deploy-prod-{name}.sh").read_text(encoding="utf-8")
        for support in ('state', 'lock'):
            data = (ROOT / f'scripts/deploy-prod-{support}.sh').read_bytes().replace(b'\r\n', b'\n')
            expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if f'RELEASE_{support.upper()}_BLOB="{expected}"' not in text:
                raise AssertionError('suporte deve estar pinado ao blob exato revisado')
        loader = text.split('release_load_support() {', 1)[1].split('main() {', 1)[0].strip()
        canonical = STATE.split('release_load_support() {', 1)[1].strip()
        if loader != canonical:
            raise AssertionError("loader autocontido deve corresponder ao suporte revisado")
    print("deploy-prod-web policy: ok")


if __name__ == "__main__":
    main()
