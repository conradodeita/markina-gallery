"""Verifica a separação entre preflight somente-leitura e gate de produção."""

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from check_infinitepay_retirement_scope import (
    evaluate as evaluate_retirement_scope,
)
from check_infinitepay_retirement_scope import (
    evaluate_followup_scope as evaluate_retirement_followup_scope,
)
from check_prod_app_release_scope import evaluate, git
from classify_prod_release import classify

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)
INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-facial-services.sh").read_bytes()
APP_INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-app-services.sh").read_bytes()
RETIREMENT_INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-infinitepay-retirement.sh").read_bytes()
ORDERS_INVENTORY_SCRIPT = (ROOT / "scripts/orders_pilot_release.py").read_bytes()
APP_ENV_INVENTORY_SCRIPT = (ROOT / "scripts/app_env_transition_inventory.py").read_bytes()
APP_ENV_INVENTORY_CONTRACT = (ROOT / "backend/app/environment_transition_inventory.py").read_bytes()
PREVIEW_MIGRATION_INVENTORY = (ROOT / "scripts/preview_adjustment_migration_inventory.py").read_bytes()
PREVIEW_MIGRATION_DEPLOY = (ROOT / "scripts/deploy-prod-preview-adjustment-migration.sh").read_text(encoding="utf-8")
PREVIEW_MIGRATION_WRAPPER_INSTALL = (ROOT / "scripts/install-prod-preview-migration-wrapper.sh").read_text(encoding="utf-8")
RETIREMENT_BINDING_SCRIPT = (ROOT / "scripts/retirement_binding_removal.py").read_text(encoding="utf-8")
APP_RUNBOOK = (ROOT / "docs/DEPLOY-PROD-APP.md").read_text(encoding="utf-8")
CLASSIFIER = (ROOT / "scripts/classify_prod_release.py").read_text(encoding="utf-8")


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def release_candidate_snapshot(root: Path, manifest: dict, *, target: str = "HEAD") -> tuple[str, bool, str]:
    """Prove the admitted snapshot and independently test publication of HEAD."""
    path = "openspec/changes/add-production-app-release-workflow/runtime-gates.json"
    source = git(root, "log", "-1", "--format=%H", target, "--", path)
    if not source or json.loads(git(root, "show", f"{source}:{path}")) != manifest:
        raise AssertionError("manifesto diverge do snapshot ancestral comprovado")
    baseline = manifest["production_baseline_sha"]
    if evaluate(root, baseline, source, manifest) != (True, "somente_api_web"):
        changed = set(git(root, "diff", "--name-only", baseline, source).splitlines())
        compose_diff = git(root, "diff", "--no-ext-diff", "--unified=0", baseline, source,
                           "--", "docker/docker-compose.yml")
        original_retirement = evaluate_retirement_scope(changed, compose_diff)[0]
        parent = git(root, "rev-parse", f"{source}^")
        integrated_followup = evaluate_retirement_followup_scope(root, parent, source)[0]
        if classify(changed) != "protected" or not (original_retirement or integrated_followup):
            raise AssertionError("snapshot do manifesto não é candidato API/web nem change de aposentadoria aprovada")
    ready, reason = evaluate(root, baseline, target, manifest)
    if not ready:
        changed = set(git(root, "diff", "--name-only", baseline, target).splitlines())
        if classify(changed) not in {"protected", "dependencies"} or reason not in {
            "api_fora_do_escopo", "arquivo_fora_do_escopo", "runtime_diverge_do_blob_aprovado",
        }:
            raise AssertionError(f"candidato não comprova a recusa protegida esperada: {reason}")
    return source, ready, reason


def main() -> None:
    require("base_sha={baseline}", "classificador exporta a base de produção", CLASSIFIER)
    require("base_sha: ${{ steps.classify.outputs.base_sha }}", "workflow encaminha a base de produção", WORKFLOW)
    if 'echo "base_sha=$base_sha"' in WORKFLOW:
        raise AssertionError("workflow não pode sobrescrever a base de produção com o pai do evento")
    require(
        "Classificar delta desde o SHA saudável registrado",
        "classificador documenta a base real do runtime",
        WORKFLOW,
    )
    preflight = WORKFLOW.split("  production-preflight:", 1)[1].split(
        "  production-release:", 1
    )[0]
    release = WORKFLOW.split("  production-release:", 1)[1]
    app_preflight = WORKFLOW.split("  production-app-preflight:", 1)[1].split(
        "  production-app-release:", 1
    )[0]
    app_release = WORKFLOW.split("  production-app-release:", 1)[1]
    retirement_scope = WORKFLOW.split("  infinitepay-retirement-scope:", 1)[1].split(
        "  infinitepay-retirement-preflight:", 1
    )[0]
    retirement_preflight = WORKFLOW.split("  infinitepay-retirement-preflight:", 1)[1].split(
        "  infinitepay-retirement-release-approval:", 1
    )[0]
    retirement_release_approval = WORKFLOW.split("  infinitepay-retirement-release-approval:", 1)[1].split(
        "  infinitepay-retirement-release:", 1
    )[0]
    retirement_release = WORKFLOW.split("  infinitepay-retirement-release:", 1)[1].split(
        "  production-preflight:", 1
    )[0]
    rollback_preflight = WORKFLOW.split("  production-app-rollback-preflight:", 1)[1].split(
        "  production-app-rollback:", 1
    )[0]
    rollback_release = WORKFLOW.split("  production-app-rollback:", 1)[1]
    orders_preflight = WORKFLOW.split("  orders-pilot-preflight:", 1)[1].split(
        "  app-env-transition-inventory:", 1
    )[0]
    app_env_preflight = WORKFLOW.split("  app-env-transition-inventory:", 1)[1]
    orders_wrapper_install = WORKFLOW.split("  orders-live-inventory-wrapper-install:", 1)[1].split(
        "  orders-pilot-preflight:", 1
    )[0]
    preview_wrapper_install = WORKFLOW.split("  preview-adjustment-migration-wrapper-install:", 1)[1].split(
        "  preview-adjustment-migration-scope:", 1
    )[0]
    preview_scope = WORKFLOW.split("  preview-adjustment-migration-scope:", 1)[1].split(
        "  preview-adjustment-migration-preflight:", 1
    )[0]
    preview_preflight = WORKFLOW.split("  preview-adjustment-migration-preflight:", 1)[1].split(
        "  preview-adjustment-migration-release-approval:", 1
    )[0]
    preview_approval = WORKFLOW.split("  preview-adjustment-migration-release-approval:", 1)[1].split(
        "  preview-adjustment-migration-release:", 1
    )[0]
    preview_release = WORKFLOW.split("  preview-adjustment-migration-release:", 1)[1].split(
        "  production-preflight:", 1
    )[0]

    require("environment: production-preflight", "environment sem revisor para preflight", preflight)
    require("fetch-depth: 0", "histórico para comparar o baseline autorizado", preflight)
    require("check_prod_facial_release_gates.py --maintenance", "gate próprio da manutenção autorizada", preflight)
    require("20261016_0082_facial_conditional_consent.py", "única migration aditiva aprovada", preflight)
    require("environment: production", "environment protegido no release", release)
    require("needs.release-scope.outputs.scope == 'facial'", "fluxo facial isolado", preflight)
    require("needs.release-scope.outputs.scope == 'app'", "preflight API/web condicionado ao classificador", app_preflight)
    require("MARKINA_APP_TARGET_SHA=$GITHUB_SHA", "inventário API/web restrito", app_preflight)
    require("environment: production", "aprovação protegida para API/web", app_release)
    require("scripts/deploy-prod-app-services.sh", "release API/web dedicado", app_release)
    require("workflow_dispatch:", "rollback manual explícito", WORKFLOW)
    require("- infinitepay-retirement-preflight", "operação manual de preflight", WORKFLOW)
    require("- infinitepay-retirement-release", "operação manual de release", WORKFLOW)
    require("- orders-pilot-inventory", "operação manual de inventário Orders", WORKFLOW)
    require("- orders-live-inventory-wrapper-install", "operação manual de atualização do inventário read-only Orders", WORKFLOW)
    require("- app-env-transition-inventory", "operação manual de inventário APP_ENV", WORKFLOW)
    require("inputs.operation == 'app-env-transition-inventory'", "coletor APP_ENV somente manual na main", app_env_preflight)
    require("environment: production-preflight", "coletor APP_ENV usa somente credenciais read-only", app_env_preflight)
    require("needs: [backend, frontend, openspec, homolog-inventory-policy, gitleaks]",
            "coletor APP_ENV aguarda gates de CI", app_env_preflight)
    require('"MARKINA_APP_ENV_INVENTORY_TARGET_SHA=$GITHUB_SHA" </dev/null',
            "coletor envia somente SHA e stdin fechado", app_env_preflight)
    require('"$PRODUCTION_SSH_USER@$PRODUCTION_SSH_HOST"',
            "coletor conecta somente ao destino SSH configurado", app_env_preflight)
    require("scripts/app_env_transition_inventory_report.py", "workflow valida e resume recibo sanitizado", app_env_preflight)
    require("PRODUCTION_SSH_PRIVATE_KEY: ${{ secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY }}",
            "chave SSH somente nos passos necessários", app_env_preflight)
    require("unset PRODUCTION_SSH_PRIVATE_KEY PRODUCTION_SSH_KNOWN_HOSTS", "chaves removidas antes de resumir", app_env_preflight)
    if "\n    env:\n      PRODUCTION_SSH_HOST" in app_env_preflight:
        raise AssertionError("segredos de preflight não podem ser variáveis globais do job")
    if any(token in app_env_preflight.lower() for token in (
        "environment: production\n", "docker compose", "alembic upgrade", "compose pause", "compose stop",
    )):
        raise AssertionError("inventário APP_ENV usa credencial mutável ou altera serviço/schema")
    require("MARKINA_APP_ENV_INVENTORY_TARGET_SHA=([0-9a-f]{40})", "wrapper valida SHA APP_ENV completo", WRAPPER)
    require('script_name="app_env_transition_inventory.py"', "wrapper seleciona coletor APP_ENV fixo", WRAPPER)
    require('APP_ENV_INVENTORY_BLOB_SHA=', "wrapper fixa blob do coletor APP_ENV", WRAPPER)
    require('inventory_mode="app-env-inventory"', "wrapper fixa modo APP_ENV somente-leitura", WRAPPER)
    require('python3 -B - "$inventory_mode" --sha "$target_sha"', "wrapper limita coletor a modo e SHA", WRAPPER)
    app_env_blob = APP_ENV_INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    app_env_blob_sha = hashlib.sha1(f"blob {len(app_env_blob)}\0".encode() + app_env_blob).hexdigest()
    require(f'APP_ENV_INVENTORY_BLOB_SHA="{app_env_blob_sha}"', "wrapper fixa conteúdo exato do coletor", WRAPPER)
    contract_blob = APP_ENV_INVENTORY_CONTRACT.replace(b"\r\n", b"\n")
    contract_blob_sha = hashlib.sha1(f"blob {len(contract_blob)}\0".encode() + contract_blob).hexdigest()
    require(f'CONTRACT_BLOB_SHA = "{contract_blob_sha}"', "coletor fixa contrato sanitizado exato", APP_ENV_INVENTORY_SCRIPT.decode("utf-8"))
    for forbidden in ("mercadopago.com", "smtp.", "whatsapp.com", "INSERT INTO", "UPDATE ", "DELETE FROM"):
        if forbidden.lower() in APP_ENV_INVENTORY_SCRIPT.decode("utf-8").lower():
            raise AssertionError(f"coletor APP_ENV contém operação/provedor externo: {forbidden}")
    require("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY", "consulta ao banco é transação somente-leitura", APP_ENV_INVENTORY_SCRIPT.decode("utf-8"))
    require('"collection_status": "incomplete"', "fonte ausente produz relatório sanitizado incompleto", APP_ENV_INVENTORY_SCRIPT.decode("utf-8"))
    require('"approval_fingerprint": None', "fonte incompleta não produz fingerprint", APP_ENV_INVENTORY_SCRIPT.decode("utf-8"))
    require("inputs.operation == 'orders-live-inventory-wrapper-install'", "instalador Orders só manual na main", orders_wrapper_install)
    require("environment: production", "wrapper Orders usa ambiente protegido", orders_wrapper_install)
    require("needs: [ci-scope, backend, frontend, runtime-images, openspec, homolog-inventory-policy, gitleaks]",
            "wrapper Orders depende dos gates de CI", orders_wrapper_install)
    require("scripts/install-prod-preview-migration-wrapper.sh", "wrapper Orders instala artefato root-owned protegido", orders_wrapper_install)
    if any(token in orders_wrapper_install.lower() for token in ("docker ", "docker-compose", "alembic upgrade", "orders_pilot_release.py")):
        raise AssertionError("instalador do wrapper Orders não pode alterar serviços ou executar helpers de inventário")
    require("- preview-adjustment-migration-preflight", "preflight manual da migration 0090", WORKFLOW)
    require("- preview-adjustment-migration-release", "release manual da migration 0090", WORKFLOW)
    require("- preview-adjustment-migration-wrapper-install", "instalação manual do wrapper restrito", WORKFLOW)
    require("inputs.operation == 'preview-adjustment-migration-wrapper-install'", "instalador só manual na main", preview_wrapper_install)
    require("environment: production", "instalador usa proteção de produção", preview_wrapper_install)
    require("needs: [ci-scope, backend, frontend, runtime-images, openspec, homolog-inventory-policy, gemma-runtime, gitleaks, preview-adjustment-migration-scope]", "instalador espera CI completo e escopo", preview_wrapper_install)
    require("scripts/install-prod-preview-migration-wrapper.sh", "instalação executa helper dedicado", preview_wrapper_install)
    if "PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY" in preview_wrapper_install or "docker" in preview_wrapper_install.lower():
        raise AssertionError("instalador não pode usar chave read-only nem tocar Docker")
    require('^MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA=([0-9a-f]{40})$', "wrapper aceita SHA de suporte completo", WRAPPER)
    for fragment, label in (
        ("https://github.com/conradodeita/markina-gallery.git", "instalador limita repositório esperado"),
        ('$(hostname -s)" == clearbudget-vnic', "instalador limita host esperado"),
        ('sudo -n install -o root -g root -m 0600 -- "$WRAPPER" "$backup"', "backup do wrapper root-owned"),
        ('sudo -n install -o root -g root -m 0755 -- "$temporary" "$staging"', "novo wrapper instalado root-owned"),
        ('sudo -n mv -T -- "$staging" "$WRAPPER"', "wrapper trocado atomicamente"),
        ('grep -Fq \'restrict,command="/usr/local/sbin/markina-gallery-preflight-ssh-wrapper"\'', "authorized_keys restrito preservado"),
        ('SSH_ORIGINAL_COMMAND=\'id\' "$WRAPPER"', "recusa de comando arbitrário verificada"),
    ):
        require(fragment, label, PREVIEW_MIGRATION_WRAPPER_INSTALL)
    if any(token in PREVIEW_MIGRATION_WRAPPER_INSTALL.lower() for token in ("docker ", "docker-compose", "alembic upgrade", "authorized_keys\" >", "authorized_keys\" >>")):
        raise AssertionError("instalador excede o escopo de troca do wrapper")
    for operation in ("preview-adjustment-migration-wrapper-install", "preview-adjustment-migration-preflight", "preview-adjustment-migration-release"):
        require(f"inputs.operation == '{operation}'", f"operação {operation} limitada ao workflow manual", preview_scope)
    require("check_preview_adjustment_migration_scope.py", "escopo e CI do candidato verificados", preview_scope)
    require("0dd015a62447e0c8d4c6af16b381140c8118f2ec", "SHA exato do runtime", preview_scope)
    require("environment: production-preflight", "preflight com credencial somente-leitura", preview_preflight)
    require("MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA=$GITHUB_SHA", "preflight identifica o helper integrado", preview_preflight)
    require("inputs.operation == 'preview-adjustment-migration-release'", "release repete o preflight manual", preview_preflight)
    if "environment: production\n" in preview_preflight or "--mode release" in preview_preflight:
        raise AssertionError("preflight da migration não pode acessar credencial ou modo mutável")
    require("REQUESTED_APPROVAL_FINGERPRINT: ${{ inputs.approval_fingerprint }}", "gate usa fingerprint enviado pelo operador", preview_approval)
    require("PREFLIGHT_FINGERPRINT: ${{ needs.preview-adjustment-migration-preflight.outputs.approval_fingerprint }}", "gate usa inventário recém-coletado", preview_approval)
    require('os.environ["REQUESTED_APPROVAL_FINGERPRINT"] == os.environ["PREFLIGHT_FINGERPRINT"]', "gate compara fingerprints integralmente", preview_approval)
    require("needs.preview-adjustment-migration-release-approval.outputs.approved == 'true'", "release depende da aprovação exata", preview_release)
    require("environment: production", "release protegido", preview_release)
    require("scripts/deploy-prod-preview-adjustment-migration.sh", "release chama executor dedicado", preview_release)
    require('^MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA=([0-9a-f]{40})$', "wrapper aceita apenas SHA exato para leitura", WRAPPER)
    require('PREVIEW_MIGRATION_INVENTORY_BLOB_SHA=', "wrapper fixa blob do helper read-only", WRAPPER)
    require('script_name="preview_adjustment_migration_inventory.py"', "wrapper seleciona helper somente-leitura", WRAPPER)
    if "PENDING_PREVIEW_" in WRAPPER or "PENDING_PREVIEW_" in PREVIEW_MIGRATION_DEPLOY:
        raise AssertionError("pins do fluxo de migration precisam ser fechados antes da integração")
    inventory_blob = subprocess.run(
        ["git", "hash-object", "--", "scripts/preview_adjustment_migration_inventory.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    require(f'PREVIEW_MIGRATION_INVENTORY_BLOB_SHA="{inventory_blob}"', "wrapper fixa blob do inventário exato", WRAPPER)
    for path, constant in (
        ("scripts/preview_adjustment_migration_inventory.py", "INVENTORY_BLOB_SHA"),
        ("scripts/preview_adjustment_migration_release_flow.py", "FLOW_BLOB_SHA"),
        ("scripts/preview_adjustment_migration_release.py", "RELEASE_BLOB_SHA"),
    ):
        blob = subprocess.run(["git", "hash-object", "--", path], cwd=ROOT,
                              check=True, capture_output=True, text=True).stdout.strip()
        require(f'{constant}="{blob}"', f"executor fixa blob de {path}", PREVIEW_MIGRATION_DEPLOY)
    require('approval_fingerprint="$6"', "executor exige fingerprint como argumento explícito", PREVIEW_MIGRATION_DEPLOY)
    require("TARGET_SHA=\"0dd015a62447e0c8d4c6af16b381140c8118f2ec\"", "executor limita runtime candidato", PREVIEW_MIGRATION_DEPLOY)
    require('python3 -B "$temporary/preview_adjustment_migration_release.py" release', "executor despacha apenas release", PREVIEW_MIGRATION_DEPLOY)
    if "alembic upgrade head" in PREVIEW_MIGRATION_DEPLOY or "docker compose down" in PREVIEW_MIGRATION_DEPLOY:
        raise AssertionError("executor contém operação genérica/destrutiva não permitida")
    require("inputs.operation == 'orders-pilot-inventory'", "inventário Orders só manual", orders_preflight)
    require("environment: production-preflight", "Orders usa somente ambiente read-only", orders_preflight)
    require("MARKINA_ORDERS_TARGET_SHA=$GITHUB_SHA", "Orders envia somente SHA completo", orders_preflight)
    require("inventory_fingerprint", "Orders exige fingerprint remoto", orders_preflight)
    if "environment: production\n" in orders_preflight or "--mode prepare" in orders_preflight or "--mode apply" in orders_preflight:
        raise AssertionError("preflight Orders não pode usar credencial mutável nem executar prepare/apply")
    require("approval_fingerprint:", "campo explícito de aprovação", WORKFLOW)
    require("inputs.operation == 'infinitepay-retirement-preflight'", "operação de preflight", retirement_scope)
    require("inputs.operation == 'infinitepay-retirement-release'", "operação de release", retirement_scope)
    require("check_infinitepay_retirement_scope.py", "gate exato antes do inventário", retirement_scope)
    require("environment: production-preflight", "inventário usa somente credencial read-only", retirement_preflight)
    require("MARKINA_RETIREMENT_TARGET_SHA=$GITHUB_SHA", "comando do inventário aposentadoria restrito", retirement_preflight)
    require("retirement_inventory_policy.py", "validação local do inventário minimizado", retirement_preflight)
    require("secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY", "inventário não usa credencial mutável", retirement_preflight)
    require("inputs.operation == 'infinitepay-retirement-preflight'", "preflight pode ser chamado isoladamente", retirement_preflight)
    require("inputs.operation == 'infinitepay-retirement-release'", "release também repete o preflight", retirement_preflight)
    if "environment: production\n" in retirement_preflight or "--mode release" in retirement_preflight:
        raise AssertionError("preflight não pode usar ambiente/command de release")
    require("inputs.operation == 'infinitepay-retirement-release'", "gate de aprovação só executa no release", retirement_release_approval)
    require("REQUESTED_APPROVAL_FINGERPRINT: ${{ inputs.approval_fingerprint }}", "gate recebe fingerprint informado pelo operador", retirement_release_approval)
    require("PREFLIGHT_FINGERPRINT: ${{ needs.infinitepay-retirement-preflight.outputs.approval_fingerprint }}", "gate recebe fingerprint recém-coletado", retirement_release_approval)
    require("scripts/validate_retirement_approval.py", "release valida formato e igualdade de fingerprint", retirement_release_approval)
    require("uses: actions/checkout@v4", "job disponibiliza o helper versionado", retirement_release_approval)
    require("persist-credentials: false", "checkout do gate não persiste credenciais", retirement_release_approval)
    if retirement_release_approval.index("uses: actions/checkout@v4") > retirement_release_approval.index("python scripts/validate_retirement_approval.py"):
        raise AssertionError("checkout precisa anteceder a execução do helper de aprovação")
    require("approved=true", "gate emite aprovação somente após igualdade", retirement_release_approval)
    require("needs.infinitepay-retirement-release-approval.outputs.approved == 'true'", "release depende do gate explícito", retirement_release)
    require("needs.infinitepay-retirement-preflight.outputs.approval_fingerprint", "release vinculado ao fingerprint read-only", retirement_release)
    require("environment: production", "release de aposentadoria exige aprovação protegida", retirement_release)
    require("scripts/deploy-prod-infinitepay-retirement.sh", "executor dedicado da aposentadoria", retirement_release)
    require("scripts/test_deploy_prod_infinitepay_retirement.sh", "CI testa o despacho de modo da aposentadoria", WORKFLOW)
    require("MARKINA_APP_ROLLBACK_SHA=$GITHUB_SHA", "inventário de rollback read-only", rollback_preflight)
    require("environment: production", "rollback protegido", rollback_release)
    require(
        "secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY",
        "chave dedicada de preflight",
        preflight,
    )
    require(
        "secrets.PRODUCTION_PREFLIGHT_SSH_KNOWN_HOSTS",
        "known_hosts dedicado de preflight",
        preflight,
    )
    require('"MARKINA_TARGET_SHA=$GITHUB_SHA" </dev/null', "comando restrito sem stdin controlado pelo runner", preflight)
    if "< scripts/deploy-prod-facial-services.sh" in preflight or "bash -s" in preflight:
        raise AssertionError("preflight não pode executar script enviado pelo runner")

    require('^MARKINA_TARGET_SHA=([0-9a-f]{40})$', "comando SSH validado por regex estrita", WRAPPER)
    require('inventory_mode="inventory"', "wrapper fixa modo somente-leitura padrão", WRAPPER)
    require('inventory_mode="rollback-inventory"', "wrapper limita o segundo modo a inventário de rollback", WRAPPER)
    require('MARKINA_RETIREMENT_TARGET_SHA=([0-9a-f]{40})', "comando de aposentadoria exige SHA completo", WRAPPER)
    require('MARKINA_ORDERS_TARGET_SHA=([0-9a-f]{40})', "comando Orders exige SHA completo", WRAPPER)
    require('script_name="orders_pilot_release.py"', "wrapper seleciona o helper Orders fixo", WRAPPER)
    require('inventory_runtime="python"', "wrapper despacha Orders somente para Python", WRAPPER)
    require('python3 -B - "$inventory_mode" --sha "$target_sha"', "wrapper força inventory Orders com SHA", WRAPPER)
    require('script_name="deploy-prod-infinitepay-retirement.sh"', "wrapper aponta para o inventário de aposentadoria", WRAPPER)
    require('--mode "$inventory_mode"', "wrapper não encaminha modo enviado pelo cliente", WRAPPER)
    inventory_text = INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    blob_header = f"blob {len(inventory_text)}\0".encode()
    blob_sha = hashlib.sha1(blob_header + inventory_text).hexdigest()
    require(
        f'FACIAL_SCRIPT_BLOB_SHA="{blob_sha}"',
        "wrapper fixa o conteúdo exato do script somente-leitura",
        WRAPPER,
    )
    require(
        'https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$target_sha/scripts/$script_name',
        "script selecionado por SHA imutável após merge",
        WRAPPER,
    )
    require('script_name="deploy-prod-facial-services.sh"', "wrapper mantém caminho facial", WRAPPER)
    require('script_name="deploy-prod-app-services.sh"', "wrapper inclui caminho app isolado", WRAPPER)
    require('git hash-object --stdin', "integridade do script conferida sem gravá-lo no Git", WRAPPER)
    app_inventory_text = APP_INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    app_blob_header = f"blob {len(app_inventory_text)}\0".encode()
    app_blob_sha = hashlib.sha1(app_blob_header + app_inventory_text).hexdigest()
    require(f'APP_SCRIPT_BLOB_SHA="{app_blob_sha}"', "wrapper fixa o script API/web exato", WRAPPER)
    retirement_inventory_text = RETIREMENT_INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    retirement_blob_header = f"blob {len(retirement_inventory_text)}\0".encode()
    retirement_blob_sha = hashlib.sha1(retirement_blob_header + retirement_inventory_text).hexdigest()
    require(f'RETIREMENT_SCRIPT_BLOB_SHA="{retirement_blob_sha}"', "wrapper fixa o inventário de aposentadoria exato", WRAPPER)
    orders_inventory_text = ORDERS_INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    orders_blob_header = f"blob {len(orders_inventory_text)}\0".encode()
    orders_blob_sha = hashlib.sha1(orders_blob_header + orders_inventory_text).hexdigest()
    require(f'ORDERS_SCRIPT_BLOB_SHA="{orders_blob_sha}"', "wrapper fixa o helper Orders exato", WRAPPER)
    require("MARKINA_APP_TARGET_SHA=([0-9a-f]{40})", "wrapper aceita somente SHA app completo", WRAPPER)
    require("MARKINA_APP_ROLLBACK_SHA=([0-9a-f]{40})", "wrapper aceita apenas SHA para inventário de rollback", WRAPPER)
    if "--mode release" in WRAPPER or '"$SSH_ORIGINAL_COMMAND"' in WRAPPER:
        raise AssertionError("wrapper não pode encaminhar comando arbitrário nem release")
    if "mktemp" in WRAPPER or "git fetch" in WRAPPER:
        raise AssertionError("wrapper não cria temporários nem altera refs locais do checkout")

    require("printf '%s\\n' \"$script_body\" | MARKINA_EXPECTED_REPOSITORY=", "somente conteúdo validado alimenta stdin", WRAPPER)
    script = INVENTORY_SCRIPT.decode("utf-8")
    app_script = APP_INVENTORY_SCRIPT.decode("utf-8")
    retirement_script = RETIREMENT_INVENTORY_SCRIPT.decode("utf-8")
    require('MODE" == inventory', "script remoto aceita somente modo de inventário", retirement_script)
    require('"20261021_0086"', "preflight confere schema anterior exato", retirement_script)
    require("compose_binding_metadata", "preflight coleta apenas metadados do binding", retirement_script)
    require("compose config --environment", "preflight resolve somente a variável de caminho do binding", retirement_script)
    require(
        "config --no-env-resolution --no-interpolate --no-path-resolution --no-normalize --format json",
        "preflight preserva referências env_file sem resolver seu conteúdo",
        retirement_script,
    )
    require("MARKINA_RETIREMENT_BINDING_PATH_OVERRIDE", "preflight passa somente o caminho resolvido ao parser", retirement_script)
    require("nenhuma mutação foi executada", "preflight confirma operação read-only", retirement_script)
    release_script = retirement_script.split("release() {", 1)[1].split("main() {", 1)[0]
    require('if [[ "$MODE" == inventory ]]; then', "modo release despacha para a rotina mutável apenas após o gate", retirement_script)
    require("verify_restore_receipt", "restauração anterior testada é gate", release_script)
    receipt_verifier = retirement_script.split("verify_restore_receipt() {", 1)[1].split("\n}\n", 1)[0]
    require(
        'sudo -n python3 - "$receipt" "$BACKUP_DIR"',
        "recibo root-only validado sem prompt e sem alterar permissões",
        receipt_verifier,
    )
    require(
        'info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600',
        "verificador confirma owner root e modo 0600 sem seguir symlink",
        receipt_verifier,
    )
    if "chmod " in receipt_verifier or "chown " in receipt_verifier:
        raise AssertionError("verificador não pode alterar owner ou permissões do recibo")
    require("pg_dump -Fc", "backup custom consistente antes da migration", retirement_script)
    require("pg_restore --list", "arquivo de backup validado", retirement_script)
    require("retirement_financial_evidence.py", "evidência agregada pré/pós migration", retirement_script)
    require("retirement_pix_evidence.py", "continuidade do PIX próprio verificada antes/depois", retirement_script)
    require("alembic upgrade 20261022_0087", "somente migration de aposentadoria", release_script)
    require("compose stop api", "API antiga pausada antes da migration destrutiva", release_script)
    require("compose stop --timeout 180 worker", "worker antigo tem janela explícita para finalizar ciclo", release_script)
    require("{{.State.Status}}:{{.State.ExitCode}}", "release aborta se o worker não sair limpo", release_script)
    require("compose build api web worker", "imagem do worker atualizada com o schema", release_script)
    require("compose up -d --no-deps --force-recreate --wait --wait-timeout 120 api web worker", "API/web/worker publicados e aguardados", release_script)
    require("remove_binding_after_health", "binding removido somente após saúde", release_script)
    require("retirement_host_references.py", "varredura recursiva das configurações compartilhadas", retirement_script)
    host_references_blob = git(ROOT, "hash-object", "--", "scripts/retirement_host_references.py")
    require(
        f'HOST_REFERENCES_SCRIPT_BLOB_SHA="{host_references_blob}"',
        "scanner remoto fixa o blob versionado exato",
        retirement_script,
    )
    require(
        'raw.githubusercontent.com/$EXPECTED_REPOSITORY/$TARGET_SHA/scripts/retirement_host_references.py',
        "scanner remoto é buscado da revisão aprovada",
        retirement_script,
    )
    require('python3 -c "$host_references_source"', "scanner remoto não depende do checkout de produção", retirement_script)
    require("docker ps -aq", "inventário de containers completos para mounts externos", retirement_script)
    require("sudo -n python3", "varredura privilegiada sem prompt interativo", retirement_script)
    financial_source = (ROOT / "scripts/retirement_financial_evidence.py").read_text(encoding="utf-8")
    if "checkout_url" in financial_source or "credential_id" in financial_source:
        raise AssertionError("evidência não pode depender de colunas removidas pela migration")
    if "upgrade head" in release_script or "alembic downgrade" in release_script:
        raise AssertionError("release não pode executar migration adicional ou downgrade")
    if not (release_script.index("verify_restore_receipt") < release_script.index("compose build api web worker")
            < release_script.index("compose stop api") < release_script.index("compose stop --timeout 180 worker")
            < release_script.index("create_backup")
            < release_script.index("pre_evidence=\"$(financial_evidence)\"")
            < release_script.index("pre_pix=\"$(pix_evidence)\"")
            < release_script.index("MIGRATION_STARTED=true") < release_script.index("alembic upgrade 20261022_0087")
            < release_script.index("compose up -d --no-deps") < release_script.index("remove_binding_after_health")):
        raise AssertionError("ordem protegida do release/migration/limpeza diverge")
    if "rm -rf" in RETIREMENT_BINDING_SCRIPT or "rmtree" in RETIREMENT_BINDING_SCRIPT:
        raise AssertionError("limpeza do binding deve remover somente um arquivo")
    manifest = json.loads((ROOT / "openspec/changes/improve-client-face-reference-capture/production-gates.json").read_text(encoding="utf-8"))
    maintenance = manifest["maintenance_release"]
    app_manifest = json.loads((ROOT / "openspec/changes/add-production-app-release-workflow/runtime-gates.json").read_text(encoding="utf-8"))
    if app_manifest.get("production_baseline_sha") != "1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8":
        raise AssertionError("baseline web diverge do inventário registrado")
    if "emergency_api" in app_manifest:
        raise AssertionError("contrato API emergencial não pode permanecer após a publicação convencional comprovada")
    require("scripts/prepare_emergency_api_image.py", "homologação de imagem API antes da troca", app_script)
    if app_manifest.get("expected_database_revision") != "20261022_0087":
        raise AssertionError("revisão de banco app diverge do inventário registrado")
    require("facial-last-healthy.sha", "marcador da última versão facial saudável", script)
    require('baseline_file="${1:-$STATE_DIR/facial-last-healthy.sha}"', "baseline facial usa o marcador operacional", script)
    require("verify_maintenance_baseline", "checkout ativo confere marcador de release", script)
    require('git merge-base --is-ancestor "$baseline_sha" "$CHECKOUT_SHA"', "descendência após release app", script)
    if 'git diff --quiet "$baseline_sha" "$CHECKOUT_SHA" -- "${FACIAL_BASELINE_FILES[@]}"' in script:
        raise AssertionError("baseline não pode bloquear runtime facial revisado pelo manifesto")
    require('git merge-base --is-ancestor "$baseline_sha" "$CHECKOUT_SHA"', "checkout descende do último release saudável", script)
    require("check_prod_facial_release_gates.py --maintenance", "manifesto confere escopo e blobs exatos", preflight)
    require("target_descends_from_checkout", "ancestralidade verificada em repositório temporário", script)
    require('verify_reviewed_docker_changes "$git_dir"', "Compose alvo conferido no repositório temporário", script)
    require('verify_reviewed_docker_changes "$PROJECT_ROOT"', "Compose revisado conferido antes de release", script)
    require('git -C "$git_dir" config extensions.partialClone origin', "filtro de blobs habilitado no repositório temporário", script)
    require('git -C "$git_dir" fetch --quiet --no-tags --filter=blob:none origin refs/heads/main', "commits da main buscados sem blobs em diretório temporário", script)
    require('[[ "$target_sha" == "$TARGET_SHA" ]]', "alvo buscado permanece igual ao HEAD verificado", script)
    require('git -C "$git_dir" merge-base --is-ancestor "$CHECKOUT_SHA" "$target_sha"', "candidato descende do baseline ativo", script)
    require("require_existing_facial_runtime", "manutenção não ativa runtime desligado", script)
    runtime_source, candidate_ready, candidate_reason = release_candidate_snapshot(ROOT, app_manifest)
    print(f"publication_candidate_ready={str(candidate_ready).lower()} / {candidate_reason}")
    for path, expected in maintenance["runtime_blobs"].items():
        actual = git(ROOT, "rev-parse", f"{runtime_source}:{path}")
        face_blob = base64.b64decode("".join(expected), validate=True).hex()
        if path in app_manifest["runtime_blobs"]:
            if actual != app_manifest["runtime_blobs"][path]:
                raise AssertionError("runtime compartilhado diverge do manifesto app exato")
        elif actual != face_blob:
            baseline_blob = subprocess.run(
                ["git", "rev-parse", f'{app_manifest["production_baseline_sha"]}:{path}'],
                cwd=ROOT, check=True, capture_output=True, text=True,
            ).stdout.strip()
            if actual != baseline_blob:
                raise AssertionError("runtime facial diverge do blob revisado e da versão já implantada")
    for path, expected in app_manifest["runtime_blobs"].items():
        actual = git(ROOT, "rev-parse", f"{runtime_source}:{path}")
        if actual != expected:
            raise AssertionError("arquivo de runtime app diverge do blob revisado")
    require("config --no-interpolate --hash", "hash usa JSON resolvido sem nova interpolação", script)
    if "compose config --hash" in script:
        raise AssertionError("hash direto omite env_file no Compose do host")
    require('APP_VERSION="$COMPOSE_APP_VERSION" docker compose', "metadado operacional preservado", script)
    require('--wait --wait-timeout 120', "espera de saúde limitada", script)
    require('EXPECTED_DATABASE_REVISION="20261016_0082"', "revisão já publicada do banco fixada", script)
    require('TARGET_DATABASE_REVISION="20261016_0082"', "revisão de destino fixada", script)
    release_script = script.split("release() {", 1)[1].split("main() {", 1)[0]
    require('fingerprint_with_baseline_compose "$baseline_compose_yaml"', "drift relê ambiente com Compose anterior", release_script)
    if not (release_script.index('baseline_compose_yaml="$(git show') < release_script.index('git switch --detach')
            < release_script.index('compose build') < release_script.index('fingerprint_with_baseline_compose') < release_script.index('compose up')):
        raise AssertionError("Compose anterior deve ser preservado em memória para a conferência antes da recriação")
    require("runtime_snapshot", "releitura de hashes após recriação", release_script)
    require('alembic upgrade "$TARGET_DATABASE_REVISION"', "migration única aplicada após aprovação", release_script)
    require('"$EXPECTED_DATABASE_REVISION" != "$TARGET_DATABASE_REVISION"', "não reaplica migration já publicada", release_script)
    require('--retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5', "smoke tolera transição com orçamento limitado", release_script)
    require('migrated_revision" == "$TARGET_DATABASE_REVISION"', "revisão nova confirmada", release_script)
    if not (release_script.index('alembic upgrade') < release_script.index("compose up")):
        raise AssertionError("migration deve concluir antes da recriação de serviços")

    require('EXPECTED_DATABASE_REVISION="20261022_0087"', "schema atual da aplicação fixado", app_script)
    require('readonly SERVICES=(api web)', "release app inclui somente API e web", app_script)
    require('compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"',
            "release app não recria dependências", app_script)
    for fragment, label in (
        ("20261022_0087", "schema app documentado"),
        ("1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8", "baseline app documentado"),
        ("127.0.0.1:8080", "porta Markina documentada"),
        ("https://markina.pickyourpic.com.br", "domínio documentado"),
        ("worker OTP", "exclusão do worker OTP documentada"),
    ):
        require(fragment, label, APP_RUNBOOK)
    require("compose exec -T nginx nginx -t", "validação confinada ao nginx Markina", release_script)
    require("compose exec -T nginx nginx -s reload", "renovação dos upstreams Markina", release_script)
    if not (release_script.index("compose up") < release_script.index("runtime_snapshot")
            < release_script.index("nginx -s reload") < release_script.index("smoke HTTPS")):
        raise AssertionError("pós-condições precisam preceder o smoke final")

    print("production release workflow policy: ok")


if __name__ == "__main__":
    main()
