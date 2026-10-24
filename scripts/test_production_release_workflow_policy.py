"""Verifica a separação entre preflight somente-leitura e gate de produção."""

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from check_prod_app_release_scope import evaluate, git
from classify_prod_release import classify
from check_infinitepay_retirement_scope import (
    evaluate as evaluate_retirement_scope,
    evaluate_followup_scope as evaluate_retirement_followup_scope,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)
INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-facial-services.sh").read_bytes()
APP_INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-app-services.sh").read_bytes()
RETIREMENT_INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-infinitepay-retirement.sh").read_bytes()
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
        if classify(changed) != "protected" or reason not in {
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
        "  infinitepay-retirement-release:", 1
    )[0]
    retirement_release = WORKFLOW.split("  infinitepay-retirement-release:", 1)[1].split(
        "  production-preflight:", 1
    )[0]
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
    require("MARKINA_APP_TARGET_SHA=$GITHUB_SHA", "inventário API/web restrito", app_preflight)
    require("environment: production", "aprovação protegida para API/web", app_release)
    require("scripts/deploy-prod-app-services.sh", "release API/web dedicado", app_release)
    require("workflow_dispatch:", "rollback manual explícito", WORKFLOW)
    require("- infinitepay-retirement", "operação manual de aposentadoria", WORKFLOW)
    require("inputs.operation == 'infinitepay-retirement'", "preflight limitado à operação selecionada", retirement_scope)
    require("check_infinitepay_retirement_scope.py", "gate exato antes do inventário", retirement_scope)
    require("environment: production-preflight", "inventário usa somente credencial read-only", retirement_preflight)
    require("MARKINA_RETIREMENT_TARGET_SHA=$GITHUB_SHA", "comando do inventário aposentadoria restrito", retirement_preflight)
    require("retirement_inventory_policy.py", "validação local do inventário minimizado", retirement_preflight)
    require("secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY", "inventário não usa credencial mutável", retirement_preflight)
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
    if app_manifest.get("production_baseline_sha") != "d7944baef5191ade6ac26fa86cd631bd5ad464d1":
        raise AssertionError("baseline web diverge do inventário registrado")
    emergency = app_manifest.get("emergency_api", {})
    if emergency.get("baseline_sha") != "fe1f3bc6e1a483bd1ac5f4e71149f903e724873f":
        raise AssertionError("baseline API diverge do inventário registrado")
    if emergency.get("input_blobs") != {"backend/requirements-push.txt": "2e23bf84e3eae38396218bada0ee37d3da722843"}:
        raise AssertionError("somente os quatro pins autorizados podem mudar")
    require("scripts/prepare_emergency_api_image.py", "homologação de imagem API antes da troca", app_script)
    if app_manifest.get("expected_database_revision") != "20261021_0086":
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

    require('EXPECTED_DATABASE_REVISION="20261021_0086"', "schema atual da aplicação fixado", app_script)
    require('readonly SERVICES=(api web)', "release app inclui somente API e web", app_script)
    require('compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"',
            "release app não recria dependências", app_script)
    for fragment, label in (
        ("20261021_0086", "schema app documentado"),
        ("d7944baef5191ade6ac26fa86cd631bd5ad464d1", "baseline app documentado"),
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
