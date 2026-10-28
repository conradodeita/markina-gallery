"""Coleta sanitizada do inventário APP_ENV em produção, sem efeitos colaterais."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from types import ModuleType
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path("/opt/markina-gallery")
STATE = Path("/var/lib/markina-gallery/deploy-state")
REPOSITORY = "https://github.com/conradodeita/markina-gallery.git"
REPOSITORY_NAME = "conradodeita/markina-gallery"
CONTRACT_PATH = "backend/app/environment_transition_inventory.py"
CONTRACT_BLOB_SHA = "f0dd1cb77b9a5c70ff05591d56cef3a5156f1a05"
APP_ENV_CONSUMER_SERVICES = {
    "api",
    "worker",
    "face-search-worker",
    "face-index-worker",
    "face-maintenance-worker",
}
SHA = re.compile(r"[0-9a-f]{40}\Z")
IMAGE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ALLOWED_REMOTE_ROOTS = (ROOT.resolve(), STATE.resolve())
SAFE_FAILURE_CODES = frozenset({
    "ambiente_container_duplicado",
    "ambiente_container_invalido",
    "api_ausente",
    "banco_inventario_invalido",
    "banco_mudou_durante_coleta",
    "candidato_nao_e_main",
    "checkout_sujo",
    "comando_indisponivel",
    "compose_ausente",
    "compose_divergente",
    "compose_fora_do_escopo",
    "compose_invalido",
    "compose_indisponivel",
    "compose_mudou_durante_coleta",
    "contagens_indisponiveis",
    "container_fora_do_projeto",
    "container_id_invalido",
    "container_restart_count_invalido",
    "contrato_divergente",
    "contrato_excessivo",
    "contrato_invalido",
    "contrato_indisponivel",
    "fonte_divergente",
    "inspect_invalido",
    "keyring_divergente",
    "keyring_indisponivel",
    "keyring_mudou_durante_coleta",
    "main_indisponivel",
    "portas_container_invalidas",
    "repositorio_divergente",
    "runtime_mudou_durante_coleta",
    "schema_indisponivel",
    "servico_duplicado",
    "servico_invalido",
    "servicos_ausentes",
    "sha_invalido",
    "versao_api_invalida",
    "whatsapp_inventario_invalido",
})
UNKNOWN_FAILURE_CODE = "falha_interna"


class InventoryError(RuntimeError):
    """Categoria constante; nunca contém conteúdo do comando ou do ambiente."""


def sanitized_failure_code(error: BaseException) -> str:
    """Retorna apenas um código constante, validado contra a allowlist."""
    if isinstance(error, InventoryError) and error.args:
        category = error.args[0]
        if isinstance(category, str) and category in SAFE_FAILURE_CODES:
            return category
    return UNKNOWN_FAILURE_CODE


def require(condition: bool, category: str) -> None:
    if not condition:
        raise InventoryError(category)


def run(*args: str, data: str | None = None, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            list(args),
            input=data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=ROOT,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise InventoryError("comando_indisponivel") from None
    if result.returncode != 0:
        raise InventoryError("comando_indisponivel")
    return result.stdout.strip()


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def verify_main(target_sha: str) -> None:
    require(bool(SHA.fullmatch(target_sha)), "sha_invalido")
    origin = run("git", "remote", "get-url", "origin")
    require(
        origin in {REPOSITORY, REPOSITORY[:-4], "git@github.com:conradodeita/markina-gallery.git"},
        "repositorio_divergente",
    )
    require(not run("git", "status", "--porcelain"), "checkout_sujo")
    values = run("git", "ls-remote", REPOSITORY, "refs/heads/main").split()
    require(len(values) == 2 and bool(SHA.fullmatch(values[0])), "main_indisponivel")
    require(values[0] == target_sha, "candidato_nao_e_main")


def load_contract(target_sha: str) -> ModuleType:
    url = f"https://raw.githubusercontent.com/{REPOSITORY_NAME}/{target_sha}/{CONTRACT_PATH}"
    request = Request(url, headers={"Accept": "text/plain", "User-Agent": "markina-app-env-inventory"})
    try:
        with urlopen(request, timeout=20) as response:
            location = urlsplit(response.geturl())
            require(
                location.scheme == "https"
                and location.hostname == "raw.githubusercontent.com"
                and location.username is None
                and location.password is None,
                "fonte_divergente",
            )
            content = response.read(256_001)
    except InventoryError:
        raise
    except (URLError, TimeoutError, OSError):
        raise InventoryError("contrato_indisponivel") from None
    require(len(content) <= 256_000, "contrato_excessivo")
    require(git_blob_sha(content) == CONTRACT_BLOB_SHA, "contrato_divergente")
    module = ModuleType("markina_environment_transition_inventory")
    module.__file__ = CONTRACT_PATH
    try:
        exec(compile(content, CONTRACT_PATH, "exec"), module.__dict__)  # noqa: S102 - SHA e blob exatos validados antes da execução
    except Exception:  # noqa: BLE001 - saída constante sem conteúdo do contrato
        raise InventoryError("contrato_invalido") from None
    return module


def env_map(container: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    values = (container.get("Config") or {}).get("Env") or []
    require(isinstance(values, list), "ambiente_container_invalido")
    for item in values:
        require(isinstance(item, str) and "=" in item, "ambiente_container_invalido")
        name, value = item.split("=", 1)
        require(name and name not in result, "ambiente_container_duplicado")
        result[name] = value
    return result


def host_bindings(container: dict) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    ports = (container.get("NetworkSettings") or {}).get("Ports") or {}
    require(isinstance(ports, dict), "portas_container_invalidas")
    for bindings in ports.values():
        if not bindings:
            continue
        require(isinstance(bindings, list), "portas_container_invalidas")
        for binding in bindings:
            require(isinstance(binding, dict), "portas_container_invalidas")
            host_ip = binding.get("HostIp")
            host_port = binding.get("HostPort")
            require(isinstance(host_ip, str), "portas_container_invalidas")
            try:
                port_number = int(host_port)
            except (TypeError, ValueError):
                raise InventoryError("portas_container_invalidas") from None
            require(1 <= port_number <= 65535, "portas_container_invalidas")
            result.append({"host_ip": host_ip, "host_port": port_number})
    return result


def active_containers() -> tuple[dict[str, dict], int]:
    identifiers = run(
        "docker", "ps", "-q", "--filter", "label=com.docker.compose.project=markina-gallery"
    ).splitlines()
    require(bool(identifiers), "servicos_ausentes")
    try:
        inspected = json.loads(run("docker", "inspect", *identifiers, timeout=45))
    except (ValueError, TypeError):
        raise InventoryError("inspect_invalido") from None
    require(isinstance(inspected, list), "inspect_invalido")
    services: dict[str, dict] = {}
    unknown = 0
    for container in inspected:
        require(isinstance(container, dict), "inspect_invalido")
        config = container.get("Config") or {}
        labels = config.get("Labels") or {}
        require(labels.get("com.docker.compose.project") == "markina-gallery", "container_fora_do_projeto")
        name = labels.get("com.docker.compose.service")
        require(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,62}", name), "servico_invalido")
        if name in services:
            raise InventoryError("servico_duplicado")
        env = env_map(container)
        state = container.get("State") or {}
        restart_count = container.get("RestartCount", 0)
        require(type(restart_count) is int and restart_count >= 0, "container_restart_count_invalido")
        image = container.get("Image")
        app_version = env.get("APP_VERSION")
        if app_version is not None and not SHA.fullmatch(app_version):
            app_version = None
            unknown += 1
        if not isinstance(image, str) or not IMAGE.fullmatch(image):
            image = None
            unknown += 1
        state_status = state.get("Status")
        health_value = (state.get("Health") or {}).get("Status")
        health = health_value if health_value in {"healthy", "unhealthy", "starting"} else "none"
        if health == "starting":
            health = "unknown"
        services[name] = {
            "id": container.get("Id"),
            "restart_count": restart_count,
            "name": name,
            "status": "running" if state_status == "running" else "unknown",
            "health": health,
            "image_digest": image,
            "revision": app_version,
            "ports": host_bindings(container),
            "environment": env,
            "compose_files": labels.get("com.docker.compose.project.config_files"),
        }
        require(isinstance(services[name]["id"], str) and services[name]["id"], "container_id_invalido")
    require("api" in services, "api_ausente")
    return services, unknown


def database_probe(api_container_id: str) -> dict:
    program = r'''import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text

query = text("""
SELECT json_build_object(
  'schema_revision', (SELECT CASE WHEN count(*) = 1 THEN min(version_num) ELSE NULL END FROM alembic_version),
  'credential_counts', json_build_object(
    'mercadopago_access_token', (SELECT count(*) FROM mercadopago_account WHERE access_token_envelope IS NOT NULL),
    'mercadopago_webhook_secret', (SELECT count(*) FROM mercadopago_account WHERE webhook_secret_envelope IS NOT NULL)
  ),
  'biometric_counts', json_build_object(
    'active_jobs', (SELECT count(*) FROM facial_job WHERE status IN ('queued', 'processing')),
    'photo_embeddings', (SELECT count(*) FROM photo_face_embedding WHERE payload_ciphertext IS NOT NULL),
    'search_notifications', (SELECT count(*) FROM facial_search_notification_outbox WHERE payload_ciphertext IS NOT NULL),
    'search_reference_locators', (SELECT count(*) FROM facial_search_request WHERE reference_locator_ciphertext IS NOT NULL)
  ),
  'whatsapp_bindings', json_build_object(
    'channel_bindings', (SELECT coalesce(json_agg(json_build_object(
        'environment_category', environment_category, 'status', status, 'count', amount
      ) ORDER BY environment_category, status), '[]'::json)
      FROM (
        SELECT CASE
          WHEN environment IS NULL OR btrim(environment) = '' THEN 'ausente'
          WHEN lower(btrim(environment)) = 'production' THEN 'production'
          WHEN lower(btrim(environment)) IN ('development', 'homolog', 'homologation', 'staging', 'test')
            THEN 'outro_ambiente_conhecido'
          ELSE 'outro_valor'
        END AS environment_category, status, count(*) AS amount
        FROM whatsapp_channel_settings GROUP BY 1, 2
      ) q),
    'settings_total', (SELECT count(*) FROM notification_setting),
    'settings_enabled', (SELECT count(*) FROM notification_setting WHERE whatsapp_enabled)
  )
)::text
""")

try:
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as connection:
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        connection.exec_driver_sql("SET LOCAL statement_timeout='15s'")
        payload = json.loads(connection.execute(query).scalar_one())
        connection.rollback()
    root = Path(os.environ.get("FACIAL_REFERENCE_ROOT", "./media/facial-references"))
    reference_count = 0
    unknown_entries = 0
    if root.exists():
        if root.is_symlink() or not root.is_dir():
            raise RuntimeError
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.is_symlink():
                    raise RuntimeError
                if entry.is_file(follow_symlinks=False) and entry.name.endswith(".reference"):
                    reference_count += 1
                else:
                    unknown_entries += 1
    payload["biometric_counts"]["reference_files"] = reference_count
    payload["unknown_reference_entries"] = unknown_entries
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
except Exception:
    sys.exit(2)
'''
    output = run("docker", "exec", "-i", api_container_id, "python", "-B", "-", data=program, timeout=45)
    try:
        payload = json.loads(output)
    except (ValueError, TypeError):
        raise InventoryError("banco_inventario_invalido") from None
    require(isinstance(payload, dict), "banco_inventario_invalido")
    return payload


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def runtime_snapshot_digest(services: dict[str, dict]) -> str:
    return digest({
        name: {
            "container_id": service["id"],
            "restart_count": service["restart_count"],
            "status": service["status"],
            "health": service["health"],
            "image_digest": service["image_digest"],
            "revision": service["revision"],
            "ports": service["ports"],
            "compose_files": service["compose_files"],
            "environment_digest": digest(service["environment"]),
        }
        for name, service in services.items()
    })


def verify_keyring(api_env: dict[str, str], worker_env: dict[str, str]) -> str:
    key_path = STATE / "integration-secrets.env"
    try:
        state_info = STATE.lstat()
        require(stat.S_ISDIR(state_info.st_mode), "keyring_indisponivel")
        key_info = key_path.lstat()
        require(
            stat.S_ISREG(key_info.st_mode)
            and not key_path.is_symlink()
            and key_info.st_nlink == 1
            and key_info.st_uid == os.getuid()
            and stat.S_IMODE(key_info.st_mode) == 0o600
            and key_info.st_size <= 1_048_576,
            "keyring_indisponivel",
        )
        raw = key_path.read_bytes()
    except OSError:
        raise InventoryError("keyring_indisponivel") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InventoryError("keyring_indisponivel") from None
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name in values:
            raise InventoryError("keyring_indisponivel")
        values[name] = value
    required = (
        "INTEGRATION_SECRET_ENV",
        "INTEGRATION_SECRET_ACTIVE_KEY_ID",
        "INTEGRATION_SECRET_KEYS",
    )
    for name in required:
        if (not values.get(name)
                or values[name] != api_env.get(name)
                or values[name] != worker_env.get(name)):
            raise InventoryError("keyring_divergente")
    return hashlib.sha256(raw).hexdigest()


def binding_mismatches(services: dict[str, dict]) -> int:
    api_env = services["api"]["environment"]
    worker = services.get("worker")
    if worker is None:
        return 1
    worker_env = worker["environment"]
    mismatch = int(api_env.get("INTEGRATION_SECRET_ENV") != api_env.get("APP_ENV"))
    mismatch += int(any(
        api_env.get(name) != worker_env.get(name)
        for name in (
            "WHATSAPP_PROVIDER",
            "WHATSAPP_CREDENTIAL_ENV",
            "WHATSAPP_API_URL",
            "WHATSAPP_API_KEY",
            "WHATSAPP_INSTANCE",
            "WHATSAPP_WEBHOOK_URL",
            "WHATSAPP_WEBHOOK_SECRET",
            "WHATSAPP_OTP_ENCRYPTION_KEY",
            "WHATSAPP_PHOTOGRAPHER_PHONE_E164",
            "TRANSACTIONAL_WHATSAPP_ENABLED",
            "EMAIL_PROVIDER",
            "EMAIL_CREDENTIAL_ENV",
            "EMAIL_PAYLOAD_ENCRYPTION_KEY",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_FROM_ADDRESS",
            "WEB_PUSH_ENABLED",
            "WEB_PUSH_VAPID_PUBLIC_KEY",
            "WEB_PUSH_VAPID_PRIVATE_KEY",
            "WEB_PUSH_VAPID_SUBJECT",
            "PUSH_SUBSCRIPTION_ENCRYPTION_KEY",
            "INTEGRATION_SECRET_ENV",
            "INTEGRATION_SECRET_ACTIVE_KEY_ID",
            "INTEGRATION_SECRET_KEYS",
        )
    ))
    facial_keys = (
        "FACIAL_PROCESSING_ENABLED",
        "FACIAL_CREDENTIAL_ENV",
        "FACIAL_AEAD_ACTIVE_KEY_ID",
        "FACIAL_AEAD_KEYS_JSON",
        "FACIAL_REFERENCE_ROOT",
    )
    for name in ("face-search-worker", "face-index-worker", "face-maintenance-worker"):
        service = services.get(name)
        if service is None:
            mismatch += 1
            continue
        env = service["environment"]
        if any(api_env.get(key) != env.get(key) for key in facial_keys):
            mismatch += 1
    return mismatch


def live_payment_gate(api_env: dict[str, str], worker_env: dict[str, str]) -> bool | None:
    values = (
        api_env.get("MERCADOPAGO_ALLOW_LIVE_PAYMENTS"),
        worker_env.get("MERCADOPAGO_ALLOW_LIVE_PAYMENTS"),
    )
    if any(value == "true" for value in values):
        return True
    return False if all(value == "false" for value in values) else None


def compose_digest(services: dict[str, dict]) -> str:
    paths: set[Path] = set()
    for service in services.values():
        raw = service.get("compose_files")
        require(isinstance(raw, str) and raw.strip(), "compose_ausente")
        for item in raw.split(","):
            path = Path(item.strip())
            if not path.is_absolute():
                path = ROOT / path
            try:
                resolved = path.resolve(strict=True)
            except OSError:
                raise InventoryError("compose_indisponivel") from None
            require(any(resolved == root or root in resolved.parents for root in ALLOWED_REMOTE_ROOTS),
                    "compose_fora_do_escopo")
            require(resolved.is_file() and not path.is_symlink(), "compose_invalido")
            paths.add(resolved)
    require(bool(paths), "compose_ausente")
    entries = []
    for path in sorted(paths, key=str):
        try:
            entries.append(hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            raise InventoryError("compose_indisponivel") from None
    return digest(entries)


def integration_evidence(
    api_env: dict[str, str], whatsapp_binding_counts: list[dict[str, object]],
) -> dict[str, dict[str, bool | None]]:
    def provider_state(name: str, sandbox_name: str, active_name: str) -> bool | None:
        value = api_env.get(name, "").strip().lower()
        if value == sandbox_name:
            return False
        if value == active_name:
            return True
        return None

    whatsapp_enabled = provider_state("WHATSAPP_PROVIDER", "sandbox", "evolution")
    if any(item["status"] != "sandbox" for item in whatsapp_binding_counts):
        whatsapp_enabled = True
    email_enabled = provider_state("EMAIL_PROVIDER", "sandbox", "smtp")
    facial_enabled = api_env.get("FACIAL_PROCESSING_ENABLED", "").strip().lower()
    facial_state = True if facial_enabled == "true" else False if facial_enabled == "false" else None
    target = "production"
    return {
        "whatsapp": {
            "enabled": whatsapp_enabled,
            "credential_matches_target": (
                api_env.get("WHATSAPP_CREDENTIAL_ENV", "").strip().lower() == target
                if whatsapp_enabled is True else None
            ),
            "provider_validated_for_target": None,
        },
        "smtp": {
            "enabled": email_enabled,
            "credential_matches_target": (
                api_env.get("EMAIL_CREDENTIAL_ENV", "").strip().lower() == target
                if email_enabled is True else None
            ),
            "provider_validated_for_target": None,
        },
        "facial": {
            "enabled": facial_state,
            "credential_matches_target": (
                api_env.get("FACIAL_CREDENTIAL_ENV", "").strip().lower() == target
                if facial_state is True else None
            ),
            "provider_validated_for_target": None,
        },
    }


def collect(target_sha: str, contract: ModuleType) -> dict:
    services, active_unknown = active_containers()
    unknown_count = active_unknown
    runtime_before = runtime_snapshot_digest(services)
    api_env = services["api"]["environment"]
    app_version = api_env.get("APP_VERSION")
    require(isinstance(app_version, str) and bool(SHA.fullmatch(app_version)), "versao_api_invalida")
    revisions: set[str] = set()
    for name, service in services.items():
        env = service["environment"]
        if name in APP_ENV_CONSUMER_SERVICES:
            if "APP_ENV" not in env or env.get("APP_ENV") != api_env.get("APP_ENV"):
                unknown_count += 1
        elif "APP_ENV" in env:
            unknown_count += 1
        version = env.get("APP_VERSION")
        if version:
            if not SHA.fullmatch(version):
                unknown_count += 1
            else:
                revisions.add(version)
    if revisions != {app_version}:
        unknown_count += 1

    probe = database_probe(services["api"]["id"])
    schema_revision = probe.get("schema_revision")
    require(isinstance(schema_revision, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", schema_revision),
            "schema_indisponivel")
    biometric_counts = probe.get("biometric_counts")
    credential_counts = probe.get("credential_counts")
    require(isinstance(biometric_counts, dict) and isinstance(credential_counts, dict),
            "contagens_indisponiveis")
    unknown_count += int(probe.get("unknown_reference_entries", 0))
    api_env_values = api_env
    service_records = []
    for name, service in services.items():
        service_records.append({key: service[key] for key in (
            "name", "status", "health", "image_digest", "revision", "ports"
        )})
    expected_services = contract.EXPECTED_SERVICES
    for name in expected_services - services.keys():
        service_records.append({
            "name": name,
            "status": "missing",
            "health": "none",
            "image_digest": None,
            "revision": None,
            "ports": [],
        })

    whatsapp_bindings = probe.get("whatsapp_bindings")
    require(isinstance(whatsapp_bindings, dict), "whatsapp_inventario_invalido")
    whatsapp_binding_counts = whatsapp_bindings.get("channel_bindings")
    require(isinstance(whatsapp_binding_counts, list), "whatsapp_inventario_invalido")
    worker_env = services.get("worker", {}).get("environment", {})
    keyring_digest = verify_keyring(api_env, worker_env)
    unknown_count += binding_mismatches(services)
    compose_hash = compose_digest(services)
    final_services, final_unknown = active_containers()
    require(
        runtime_snapshot_digest(final_services) == runtime_before
        and final_unknown == active_unknown,
        "runtime_mudou_durante_coleta",
    )
    final_probe = database_probe(final_services["api"]["id"])
    require(digest(final_probe) == digest(probe), "banco_mudou_durante_coleta")
    final_keyring_digest = verify_keyring(
        final_services["api"]["environment"],
        final_services.get("worker", {}).get("environment", {}),
    )
    require(final_keyring_digest == keyring_digest, "keyring_mudou_durante_coleta")
    require(compose_digest(final_services) == compose_hash, "compose_mudou_durante_coleta")
    digests = {
        "compose": compose_hash,
        "email_settings": digest({key: value for key, value in api_env_values.items()
                                   if key.startswith(("EMAIL_", "SMTP_"))}),
        "environment_file": digest(api_env_values),
        "facial_settings": digest({key: value for key, value in api_env_values.items()
                                    if key.startswith("FACIAL_")}),
        "integration_keyring": keyring_digest,
        "runtime_manifest": digest({
            "collector_sha": target_sha,
            "service_records": service_records,
            "runtime_snapshot": runtime_before,
        }),
        "whatsapp_bindings": digest(whatsapp_bindings),
    }
    gate = live_payment_gate(api_env, worker_env)
    inventory = contract.build_environment_inventory(
        source_environment=api_env.get("APP_ENV"),
        target_environment="production",
        code_revision=app_version,
        schema_revision=schema_revision,
        services=service_records,
        configuration_digests=digests,
        credential_counts=credential_counts,
        biometric_counts=biometric_counts,
        integration_evidence=integration_evidence(api_env, whatsapp_binding_counts),
        live_payment_gate=gate,
        unknown_consumer_count=unknown_count,
        whatsapp_binding_counts=whatsapp_binding_counts,
    )
    rendered = contract.render_environment_inventory(inventory)
    inventory = json.loads(rendered)
    return {
        "target_sha": target_sha,
        "collection_status": "complete",
        "inventory": inventory,
        "blockers": inventory["blockers"],
        "approval_fingerprint": inventory["approval_fingerprint"],
        "failure_category": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("app-env-inventory",))
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    verify_main(args.sha)
    try:
        contract = load_contract(args.sha)
        report = collect(args.sha, contract)
    except Exception as error:  # noqa: BLE001 - falha de fonte gera envelope sanitizado, sem detalhe bruto
        # Fonte ausente ou inconsistente é reportada de forma sanitizada e sem
        # fingerprint. Somente um código constante allowlisted pode identificar
        # a classe; nunca incluir mensagem, comando, caminho ou valor bruto.
        report = {
            "target_sha": args.sha,
            "collection_status": "incomplete",
            "inventory": None,
            "blockers": ["coleta_incompleta"],
            "approval_fingerprint": None,
            "failure_category": sanitized_failure_code(error),
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except InventoryError as error:
        raise SystemExit("app-env-inventory: " + str(error)) from None
    except Exception:  # noqa: BLE001 - evitar traceback com dados internos
        raise SystemExit("app-env-inventory: coleta_indisponivel") from None
