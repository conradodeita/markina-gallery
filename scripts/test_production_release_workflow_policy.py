"""Verifica a separação entre preflight somente-leitura e gate de produção."""

import hashlib
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)
INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-facial-services.sh").read_bytes()


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def main() -> None:
    preflight = WORKFLOW.split("  production-preflight:", 1)[1].split(
        "  production-release:", 1
    )[0]
    release = WORKFLOW.split("  production-release:", 1)[1]

    require("environment: production-preflight", "environment sem revisor para preflight", preflight)
    require("fetch-depth: 0", "histórico para comparar o baseline autorizado", preflight)
    require("check_prod_facial_release_gates.py --maintenance", "gate próprio da manutenção autorizada", preflight)
    require("20261016_0082_facial_conditional_consent.py", "única migration aditiva aprovada", preflight)
    require("environment: production", "environment protegido no release", release)
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
    require("--mode inventory", "wrapper fixa modo somente-leitura", WRAPPER)
    blob_header = f"blob {len(INVENTORY_SCRIPT)}\0".encode()
    blob_sha = hashlib.sha1(blob_header + INVENTORY_SCRIPT).hexdigest()
    require(
        f'INVENTORY_SCRIPT_BLOB_SHA="{blob_sha}"',
        "wrapper fixa o conteúdo exato do script somente-leitura",
        WRAPPER,
    )
    require(
        'https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$target_sha/scripts/deploy-prod-facial-services.sh',
        "script buscado por SHA imutável após merge",
        WRAPPER,
    )
    require('git hash-object "$script_file"', "integridade do script conferida sem gravá-lo no Git", WRAPPER)
    if "--mode release" in WRAPPER or '"$SSH_ORIGINAL_COMMAND"' in WRAPPER:
        raise AssertionError("wrapper não pode encaminhar comando arbitrário nem release")
    if "bash -s" in WRAPPER or "git fetch" in WRAPPER:
        raise AssertionError("wrapper não executa stdin nem altera refs locais do checkout")

    script = INVENTORY_SCRIPT.decode("utf-8")
    manifest = json.loads((ROOT / "openspec/changes/improve-client-face-reference-capture/production-gates.json").read_text(encoding="utf-8"))
    maintenance = manifest["maintenance_release"]
    require('baseline_file="${1:-$STATE_DIR/facial-last-healthy.sha}"', "baseline operacional usa o último release saudável", script)
    require("verify_maintenance_baseline", "checkout ativo confere com o marcador de release", script)
    require("target_descends_from_checkout", "ancestralidade verificada em repositório temporário", script)
    require('git -C "$git_dir" config extensions.partialClone origin', "filtro de blobs habilitado no repositório temporário", script)
    require('git -C "$git_dir" fetch --quiet --no-tags --filter=blob:none origin refs/heads/main', "commits da main buscados sem blobs em diretório temporário", script)
    require('[[ "$target_sha" == "$TARGET_SHA" ]]', "alvo buscado permanece igual ao HEAD verificado", script)
    require('git -C "$git_dir" merge-base --is-ancestor "$CHECKOUT_SHA" "$target_sha"', "candidato descende do baseline ativo", script)
    require("require_existing_facial_runtime", "manutenção não ativa runtime desligado", script)
    for path, expected in maintenance["runtime_blobs"].items():
        data = (ROOT / path).read_bytes()
        actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if actual != base64.b64decode("".join(expected), validate=True).hex():
            raise AssertionError("arquivo de runtime diverge do blob revisado")
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
    require("compose exec -T nginx nginx -t", "validação confinada ao nginx Markina", release_script)
    require("compose exec -T nginx nginx -s reload", "renovação dos upstreams Markina", release_script)
    if not (release_script.index("compose up") < release_script.index("runtime_snapshot")
            < release_script.index("nginx -s reload") < release_script.index("smoke HTTPS")):
        raise AssertionError("pós-condições precisam preceder o smoke final")

    print("production release workflow policy: ok")


if __name__ == "__main__":
    main()
