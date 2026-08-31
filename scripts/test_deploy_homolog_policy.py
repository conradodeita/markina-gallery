"""Verificações estruturais da automação de homologação, executáveis no CI."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "deploy-homolog.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")


def require(text: str, description: str, source: str) -> None:
    if text not in source:
        raise AssertionError(f"ausente: {description}")


def forbid(pattern: str, description: str, source: str) -> None:
    if re.search(pattern, source, flags=re.MULTILINE):
        raise AssertionError(f"proibido: {description}")


def main() -> int:
    require('readonly PROJECT_ROOT="/opt/markina-gallery"', "diretório fixo Markina", SCRIPT)
    require('readonly PROJECT_NAME="markina-gallery"', "projeto Compose fixo", SCRIPT)
    require('[[ "$(pwd -P)" == "$PROJECT_ROOT" ]]', "recusa de diretório inesperado", SCRIPT)
    require('git status --porcelain', "recusa de checkout sujo", SCRIPT)
    require('ensure_pii_fingerprint_salt', "configuração segura do fingerprint de PII", SCRIPT)
    require('openssl rand -hex 32', "geração criptográfica do fingerprint de PII", SCRIPT)
    require('chmod 600 "$ENV_FILE"', "permissão restrita do arquivo de ambiente", SCRIPT)
    require('chmod 600 "$temp_file"', "permissão restrita do arquivo de ambiente temporário", SCRIPT)
    require('record_predeploy_inventory', "inventário remoto antes do deploy", SCRIPT)
    require('df -hP "$PROJECT_ROOT"', "registro de espaço livre", SCRIPT)
    require('docker volume ls --filter "label=com.docker.compose.project=$PROJECT_NAME"', "inventário limitado aos volumes Markina", SCRIPT)
    require('origin não aponta para o repositório GitHub esperado', "recusa de origem Git inesperada", SCRIPT)
    require('git merge-base --is-ancestor "$DEPLOY_SHA" origin/develop', "validação de SHA em develop", SCRIPT)
    require('git switch --detach "$DEPLOY_SHA"', "seleção explícita de SHA", SCRIPT)
    require('return 1', "falha encaminhada ao trap de recuperação", SCRIPT)
    require('compose build migrate', "imagem de migration reconstruída no SHA alvo", SCRIPT)
    require('compose run --rm --no-deps migrate', "migration isolada", SCRIPT)
    require('SCHEMA_ROLLBACK_UNSAFE=1', "bloqueio conservador após início da migration", SCRIPT)
    require('SCHEMA_ROLLBACK_UNSAFE=0', "liberação somente após revisão inalterada", SCRIPT)
    require('next_revision" == *"(head)"*', "confirmação de migration no head alvo", SCRIPT)
    require('echo "migration Markina:', "registro não sensível da revisão aplicada", SCRIPT)
    require(
        'git switch --detach "$DEPLOY_SHA"\n'
        '  SHA_SWITCHED=1\n'
        '  apply_target_migrations "$previous_revision"',
        "migration executada somente após a seleção explícita do SHA",
        SCRIPT,
    )
    require(
        '  # A imagem do serviço migrate pode pertencer ao SHA anteriormente publicado.\n'
        '  # Reconstrua-a após selecionar o alvo para que o Alembic enxergue exatamente\n'
        '  # as revisions do commit que será iniciado nos demais serviços.\n'
        '  compose build migrate || {',
        "build da migration antes de sua execução",
        SCRIPT,
    )
    require('compose up -d --build --no-deps api web worker', "recriação limitada de serviços", SCRIPT)
    require('compose up -d evolution-db evolution-redis evolution-api', "infraestrutura WhatsApp interna e explícita", SCRIPT)
    require('compose config --services | grep -Fxq evolution-api', "ativação do perfil WhatsApp sem ler segredos", SCRIPT)
    require('start_whatsapp_infrastructure_if_active', "gate do provedor real antes dos workers", SCRIPT)
    require('compose up -d --force-recreate --no-deps nginx', "recriação limitada do nginx Markina", SCRIPT)
    require('rollback automático de código não é seguro após mudança de schema', "bloqueio de rollback de banco", SCRIPT)
    require('MARKINA_EXPECTED_REPOSITORY', "validação de origem Git", SCRIPT)
    forbid(r'\bgit\s+reset\b', "git reset", SCRIPT)
    forbid(r'\bgit\s+checkout\b', "git checkout", SCRIPT)
    forbid(r'\bdocker\s+system\s+prune\b', "docker system prune", SCRIPT)
    forbid(r'\bcompose\s+down\b', "docker compose down", SCRIPT)
    forbid(r'\b(?:rm|rmdir)\s+-[A-Za-z]*r', "remoção recursiva", SCRIPT)
    forbid(r'echo\s+.*\$salt', "impressão do segredo de fingerprint", SCRIPT)

    require('branches: [develop]', "gatilho restrito a develop", WORKFLOW)
    require('deploy-homolog:', "job de deploy", WORKFLOW)
    require('needs: [backend, frontend, openspec, gitleaks]', "dependência integral da CI", WORKFLOW)
    require('environment: homolog', "Environment protegido", WORKFLOW)
    require('secrets.HOMOLOG_SSH_PRIVATE_KEY', "chave via secret", WORKFLOW)
    require('StrictHostKeyChecking=yes', "verificação de host SSH", WORKFLOW)
    require('cd /opt/markina-gallery && env MARKINA_EXPECTED_REPOSITORY=', "diretório remoto explícito", WORKFLOW)
    forbid(r'password\s*[:=]\s*["\']?[^${\s]', "senha literal", WORKFLOW)

    require("MEDIA_HISTORY_ROOT: /var/lib/markina/history", "namespace histórico isolado", COMPOSE)
    require("  media-history:", "volume histórico persistente", COMPOSE)
    if COMPOSE.count("- media-history:/var/lib/markina/history") != 2:
        raise AssertionError("a mídia histórica deve ser compartilhada somente por API e worker")

    print("deploy-homolog policy: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
