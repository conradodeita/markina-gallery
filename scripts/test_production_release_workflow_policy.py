"""Verifica a separação entre preflight somente-leitura e gate de produção."""

import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)
INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-facial-services.sh").read_bytes()
APP_INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-app-services.sh").read_bytes()
APP_RUNBOOK = (ROOT / "docs/DEPLOY-PROD-APP.md").read_text(encoding="utf-8")
CLASSIFIER = (ROOT / "scripts/classify_prod_release.py").read_text(encoding="utf-8")


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


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
    rollback_preflight = WORKFLOW.split("  production-app-rollback-preflight:", 1)[1].split(
        "  production-app-rollback:", 1
    )[0]
    rollback_release = WORKFLOW.split("  production-app-rollback:", 1)[1]

    require("environment: production-preflight", "environment sem revisor para preflight", preflight)
    require("fetch-depth: 0", "histórico para comparar o baseline autorizado", preflight)
    require("check_prod_facial_release_gates.py --maintenance", "gate próprio da manutenção autorizada", preflight)
    require("20261016_0082_facial_conditional_consent.py", "única migration aditiva aprovada", preflight)
    require("environment: production", "environment protegido no release", release)
    require("needs.release-scope.outputs.scope == 'facial'", "fluxo facial isolado", preflight)
    require("needs.release-scope.outputs.scope == 'app'", "preflight API/web condicionado ao classificador", app_preflight)
    require("inputs.operation == 'app-release'", "release manual somente por escolha explícita", app_preflight)
    require("APP_SCOPE_BASE_SHA: ${{ needs.release-scope.outputs.base_sha }}", "dispatch usa base SHA explícita", app_preflight)
    require('python scripts/check_prod_app_release_scope.py --base "$APP_SCOPE_BASE_SHA" --target "$GITHUB_SHA"', "dispatch valida manifesto e diff", app_preflight)
    require("MARKINA_APP_TARGET_SHA=$GITHUB_SHA", "inventário API/web restrito", app_preflight)
    require("environment: production", "aprovação protegida para API/web", app_release)
    require("scripts/deploy-prod-app-services.sh", "release API/web dedicado", app_release)
    require("workflow_dispatch:", "rollback manual explícito", WORKFLOW)
    require("default: none", "dispatch manual permanece inerte por padrão", WORKFLOW)
    require("inputs.operation == 'app-rollback'", "rollback exige escolha explícita", rollback_preflight)
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
    require('git hash-object "$script_file"', "integridade do script conferida sem gravá-lo no Git", WRAPPER)
    app_inventory_text = APP_INVENTORY_SCRIPT.replace(b"\r\n", b"\n")
    app_blob_header = f"blob {len(app_inventory_text)}\0".encode()
    app_blob_sha = hashlib.sha1(app_blob_header + app_inventory_text).hexdigest()
    require(f'APP_SCRIPT_BLOB_SHA="{app_blob_sha}"', "wrapper fixa o script API/web exato", WRAPPER)
    require("MARKINA_APP_TARGET_SHA=([0-9a-f]{40})", "wrapper aceita somente SHA app completo", WRAPPER)
    require("MARKINA_APP_ROLLBACK_SHA=([0-9a-f]{40})", "wrapper aceita apenas SHA para inventário de rollback", WRAPPER)
    if "--mode release" in WRAPPER or '"$SSH_ORIGINAL_COMMAND"' in WRAPPER:
        raise AssertionError("wrapper não pode encaminhar comando arbitrário nem release")
    if "bash -s" in WRAPPER or "git fetch" in WRAPPER:
        raise AssertionError("wrapper não executa stdin nem altera refs locais do checkout")

    script = INVENTORY_SCRIPT.decode("utf-8")
    app_script = APP_INVENTORY_SCRIPT.decode("utf-8")
    manifest = json.loads((ROOT / "openspec/changes/improve-client-face-reference-capture/production-gates.json").read_text(encoding="utf-8"))
    maintenance = manifest["maintenance_release"]
    app_manifest = json.loads((ROOT / "openspec/changes/add-production-app-release-workflow/runtime-gates.json").read_text(encoding="utf-8"))
    if app_manifest.get("production_baseline_sha") != "b4f15abd6a71585082758062feba7fcfcc225587":
        raise AssertionError("baseline de produção diverge do inventário registrado")
    if app_manifest.get("expected_database_revision") != "20261017_0084":
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
    require('git -C "$git_dir" config extensions.partialClone origin', "filtro de blobs habilitado no repositório temporário", script)
    require('git -C "$git_dir" fetch --quiet --no-tags --filter=blob:none origin refs/heads/main', "commits da main buscados sem blobs em diretório temporário", script)
    require('[[ "$target_sha" == "$TARGET_SHA" ]]', "alvo buscado permanece igual ao HEAD verificado", script)
    require('git -C "$git_dir" merge-base --is-ancestor "$CHECKOUT_SHA" "$target_sha"', "candidato descende do baseline ativo", script)
    require("require_existing_facial_runtime", "manutenção não ativa runtime desligado", script)
    for path, expected in maintenance["runtime_blobs"].items():
        actual = subprocess.run(["git", "hash-object", "--", path], cwd=ROOT, check=True,
                                capture_output=True, text=True).stdout.strip()
        face_blob = base64.b64decode("".join(expected), validate=True).hex()
        if path in {"backend/app/main.py", "frontend/app/globals.css"}:
            if actual != app_manifest["runtime_blobs"].get(path):
                raise AssertionError("runtime compartilhado diverge do manifesto app exato")
        elif actual != face_blob:
            raise AssertionError("arquivo de runtime diverge do blob revisado")
    for path, expected in app_manifest["runtime_blobs"].items():
        actual = subprocess.run(["git", "hash-object", "--", path], cwd=ROOT, check=True,
                                capture_output=True, text=True).stdout.strip()
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
    require("runtime_snapshot", "releitura de hashes após recriação", release_script)
    require('alembic upgrade "$TARGET_DATABASE_REVISION"', "migration única aplicada após aprovação", release_script)
    require('"$EXPECTED_DATABASE_REVISION" != "$TARGET_DATABASE_REVISION"', "não reaplica migration já publicada", release_script)
    require('--retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5', "smoke tolera transição com orçamento limitado", release_script)
    require('migrated_revision" == "$TARGET_DATABASE_REVISION"', "revisão nova confirmada", release_script)
    if not (release_script.index('alembic upgrade') < release_script.index("compose up")):
        raise AssertionError("migration deve concluir antes da recriação de serviços")

    require('EXPECTED_DATABASE_REVISION="20261017_0084"', "schema atual da aplicação fixado", app_script)
    require('readonly SERVICES=(api web)', "release app inclui somente API e web", app_script)
    require('compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"',
            "release app não recria dependências", app_script)
    for fragment, label in (
        ("20261017_0084", "schema app documentado"),
        ("b4f15abd6a71585082758062feba7fcfcc225587", "baseline app documentado"),
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
