"""Contrato de inventário sanitizado para transições de ambiente."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

ENVIRONMENT_CATEGORIES = {
    "ausente",
    "production",
    "outro_ambiente_conhecido",
    "outro_valor",
}
KNOWN_NON_PRODUCTION_ENVIRONMENTS = {
    "development",
    "homolog",
    "homologation",
    "staging",
    "test",
}
INTEGRATION_STATES = {"validado_destino", "desativado", "nao_classificado"}
INTEGRATION_NAMES = {"facial", "smtp", "whatsapp"}
INTEGRATION_EVIDENCE_FIELDS = {
    "enabled",
    "credential_matches_target",
    "provider_validated_for_target",
}
CREDENTIAL_COUNTERS = {
    "mercadopago_access_token",
    "mercadopago_webhook_secret",
}
BIOMETRIC_COUNTERS = {
    "active_jobs",
    "photo_embeddings",
    "reference_files",
    "search_notifications",
    "search_reference_locators",
}
WHATSAPP_ENVIRONMENT_CATEGORIES = {
    "ausente",
    "production",
    "outro_ambiente_conhecido",
    "outro_valor",
}
WHATSAPP_CHANNEL_STATUSES = {
    "sandbox",
    "pending_pairing",
    "connecting",
    "ready",
    "mismatch",
    "disconnected",
    "error",
}
CONFIG_DIGEST_NAMES = {
    "compose",
    "email_settings",
    "environment_file",
    "facial_settings",
    "integration_keyring",
    "runtime_manifest",
    "whatsapp_bindings",
}
SERVICE_STATUSES = {"exited", "missing", "running", "unknown"}
SERVICE_HEALTH = {"healthy", "none", "unhealthy", "unknown"}
KNOWN_SERVICES = {
    "api",
    "db",
    "evolution-api",
    "evolution-db",
    "evolution-redis",
    "face-gemma-index-worker",
    "face-index-worker",
    "face-maintenance-worker",
    "face-search-worker",
    "nginx",
    "preview-adjustment-worker",
    "raw-development-worker",
    "redis",
    "web",
    "worker",
}
EXPECTED_SERVICES = KNOWN_SERVICES.copy()
RETIRED_SERVICES = {"face-gemma-index-worker", "raw-development-worker"}
EXPECTED_PORTS = {
    name: ([{"binding": "loopback", "port": 8080}] if name == "nginx" else [])
    for name in EXPECTED_SERVICES
}
BLOCKER_CATEGORIES = {
    "ambiente_origem_invalido",
    "consumidor_nao_classificado",
    "dados_biometricos_vinculados_a_origem",
    "gate_pagamentos_nao_fechado",
    "integracao_nao_classificada",
    "inventario_servicos_incompleto",
    "portas_divergentes",
    "servico_indisponivel",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IMAGE_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SCHEMA_REVISION = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SERVICE_NAME = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")


class EnvironmentInventoryError(ValueError):
    """Erro com categoria constante; não inclui entrada ou valor sensível."""


def _require(condition: bool, category: str) -> None:
    if not condition:
        raise EnvironmentInventoryError(category)


def environment_category(value: str | None) -> str:
    """Classifica APP_ENV sem retornar seu conteúdo arbitrário."""
    _require(value is None or isinstance(value, str), "ambiente_invalido")
    if value is None or not value.strip():
        return "ausente"
    normalized = value.strip().lower()
    if normalized == "production":
        return "production"
    if normalized in KNOWN_NON_PRODUCTION_ENVIRONMENTS:
        return "outro_ambiente_conhecido"
    return "outro_valor"


def _count_map(values: Mapping[str, Any], expected: set[str], category: str) -> dict[str, int]:
    _require(isinstance(values, Mapping) and set(values) == expected, category)
    result: dict[str, int] = {}
    for key in sorted(expected):
        value = values[key]
        _require(type(value) is int and value >= 0, category)
        result[key] = value
    return result


def _whatsapp_binding_counts(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    _require(isinstance(values, Sequence) and not isinstance(values, (str, bytes)),
             "contagens_whatsapp_invalidas")
    result = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        _require(isinstance(value, Mapping)
                 and set(value) == {"environment_category", "status", "count"},
                 "contagens_whatsapp_invalidas")
        environment = value["environment_category"]
        status = value["status"]
        count = value["count"]
        _require(isinstance(environment, str) and environment in WHATSAPP_ENVIRONMENT_CATEGORIES
                 and isinstance(status, str) and status in WHATSAPP_CHANNEL_STATUSES
                 and type(count) is int and count > 0, "contagens_whatsapp_invalidas")
        key = (environment, status)
        _require(key not in seen, "contagens_whatsapp_duplicadas")
        seen.add(key)
        result.append({"environment_category": environment, "status": status, "count": count})
    return sorted(result, key=lambda item: (item["environment_category"], item["status"]))


def classify_external_integrations(
    evidence: Mapping[str, Mapping[str, bool | None]],
) -> dict[str, str]:
    """Classifica binds sem receber, copiar ou validar valores de credenciais."""
    _require(isinstance(evidence, Mapping) and set(evidence) == INTEGRATION_NAMES,
             "classificacao_integracoes_incompleta")
    states: dict[str, str] = {}
    for name in sorted(INTEGRATION_NAMES):
        item = evidence[name]
        _require(isinstance(item, Mapping) and set(item) == INTEGRATION_EVIDENCE_FIELDS,
                 "evidencia_integracao_invalida")
        enabled = item["enabled"]
        credential_matches = item["credential_matches_target"]
        provider_validated = item["provider_validated_for_target"]
        _require(all(value is None or type(value) is bool
                     for value in (enabled, credential_matches, provider_validated)),
                 "evidencia_integracao_invalida")
        if enabled is False:
            states[name] = "desativado"
        elif enabled is True and credential_matches is True and provider_validated is True:
            states[name] = "validado_destino"
        else:
            states[name] = "nao_classificado"
    return states


def _service_summaries(values: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    _require(isinstance(values, Sequence) and not isinstance(values, (str, bytes)), "servicos_invalidos")
    summaries: list[dict[str, Any]] = []
    unknown = 0
    seen: set[str] = set()
    for value in values:
        _require(isinstance(value, Mapping), "servicos_invalidos")
        _require(
            set(value) == {"name", "status", "health", "image_digest", "revision", "ports"},
            "servicos_invalidos",
        )
        name = value["name"]
        _require(isinstance(name, str) and _SERVICE_NAME.fullmatch(name) is not None, "servicos_invalidos")
        _require(name not in seen, "servicos_duplicados")
        seen.add(name)
        if name not in KNOWN_SERVICES:
            unknown += 1
            continue

        status, health = value["status"], value["health"]
        _require(
            isinstance(status, str) and status in SERVICE_STATUSES
            and isinstance(health, str) and health in SERVICE_HEALTH,
            "estado_servico_invalido",
        )
        digest, revision = value["image_digest"], value["revision"]
        _require(digest is None or (isinstance(digest, str) and bool(_IMAGE_DIGEST.fullmatch(digest))), "digest_invalido")
        _require(revision is None or (isinstance(revision, str) and bool(_GIT_SHA.fullmatch(revision))), "revisao_servico_invalida")
        ports = value["ports"]
        _require(isinstance(ports, Sequence) and not isinstance(ports, (str, bytes)), "portas_invalidas")
        normalized_ports = []
        for port in ports:
            _require(isinstance(port, Mapping) and set(port) == {"host_ip", "host_port"}, "portas_invalidas")
            host_ip, host_port = port["host_ip"], port["host_port"]
            _require(isinstance(host_ip, str) and type(host_port) is int
                     and 1 <= host_port <= 65535, "portas_invalidas")
            binding = "loopback" if host_ip in {"127.0.0.1", "::1"} else (
                "public_all" if host_ip in {"0.0.0.0", "::"} else "unknown"
            )
            normalized_ports.append({"binding": binding, "port": host_port})
        summaries.append({
            "name": name,
            "status": status,
            "health": health,
            "image_digest": digest,
            "revision": revision,
            "ports": sorted(normalized_ports, key=lambda item: (item["binding"], item["port"])),
        })
    summaries.sort(key=lambda item: item["name"])
    return summaries, unknown


def build_environment_inventory(
    *,
    source_environment: str | None,
    target_environment: str,
    code_revision: str,
    schema_revision: str,
    services: Sequence[Mapping[str, Any]],
    configuration_digests: Mapping[str, str],
    credential_counts: Mapping[str, int],
    biometric_counts: Mapping[str, int],
    whatsapp_binding_counts: Sequence[Mapping[str, Any]],
    integration_evidence: Mapping[str, Mapping[str, bool | None]],
    live_payment_gate: bool | None,
    unknown_consumer_count: int,
) -> dict[str, Any]:
    """Constrói recibo redigido e fingerprint somente quando os gates passam.

    Chamadores devem fornecer metadados agregados; segredos, payloads, IDs e
    caminhos não fazem parte do contrato. Valores arbitrários de APP_ENV são
    classificados e nunca copiados para o recibo.
    """
    source_category = environment_category(source_environment)
    target_category = environment_category(target_environment)
    _require(target_category == "production", "destino_nao_permitido")
    _require(isinstance(code_revision, str) and _GIT_SHA.fullmatch(code_revision), "revisao_codigo_invalida")
    _require(isinstance(schema_revision, str) and _SCHEMA_REVISION.fullmatch(schema_revision), "revisao_schema_invalida")

    _require(isinstance(configuration_digests, Mapping) and set(configuration_digests) == CONFIG_DIGEST_NAMES,
             "fingerprints_configuracao_incompletos")
    digests: dict[str, str] = {}
    for name in sorted(CONFIG_DIGEST_NAMES):
        digest = configuration_digests[name]
        _require(isinstance(digest, str) and _SHA256.fullmatch(digest), "fingerprint_configuracao_invalido")
        digests[name] = digest

    credentials = _count_map(credential_counts, CREDENTIAL_COUNTERS, "contagens_credenciais_invalidas")
    biometrics = _count_map(biometric_counts, BIOMETRIC_COUNTERS, "contagens_biometricas_invalidas")
    whatsapp_bindings = _whatsapp_binding_counts(whatsapp_binding_counts)
    states = classify_external_integrations(integration_evidence)

    service_summaries, unknown_service_count = _service_summaries(services)
    seen_services = {item["name"] for item in service_summaries}
    _require(type(unknown_consumer_count) is int and unknown_consumer_count >= 0, "consumidores_invalidos")
    _require(live_payment_gate is None or type(live_payment_gate) is bool, "gate_pagamentos_invalido")

    blockers: set[str] = set()
    if source_category in {"ausente", "production", "outro_valor"}:
        blockers.add("ambiente_origem_invalido")
    if live_payment_gate is not False:
        blockers.add("gate_pagamentos_nao_fechado")
    if unknown_consumer_count or unknown_service_count:
        blockers.add("consumidor_nao_classificado")
    if seen_services != EXPECTED_SERVICES:
        blockers.add("inventario_servicos_incompleto")
    if any(state == "nao_classificado" for state in states.values()):
        blockers.add("integracao_nao_classificada")
    if any(value > 0 for value in biometrics.values()):
        blockers.add("dados_biometricos_vinculados_a_origem")
    if any(
        (item["name"] in RETIRED_SERVICES and item["status"] != "missing")
        or (item["name"] not in RETIRED_SERVICES
            and (item["status"] != "running" or item["health"] != "healthy"))
        for item in service_summaries
    ):
        blockers.add("servico_indisponivel")
    if any(item["ports"] != EXPECTED_PORTS[item["name"]] for item in service_summaries):
        blockers.add("portas_divergentes")

    snapshot = {
        "format_version": 1,
        "source_environment_category": source_category,
        "target_environment_category": target_category,
        "code_revision": code_revision,
        "schema_revision": schema_revision,
        "services": service_summaries,
        "configuration_digests": digests,
        "credential_counts": credentials,
        "biometric_counts": biometrics,
        "whatsapp_binding_counts": whatsapp_bindings,
        "integration_states": states,
        "live_payment_gate_closed": live_payment_gate is False,
        "unknown_consumer_count": unknown_consumer_count,
        "unknown_service_count": unknown_service_count,
    }
    fingerprint = None
    if not blockers:
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        fingerprint = hashlib.sha256(canonical).hexdigest()
    return {**snapshot, "blockers": sorted(blockers), "approval_fingerprint": fingerprint}


def render_environment_inventory(inventory: Mapping[str, Any]) -> str:
    """Renderiza somente um objeto produzido pelo contrato sanitizado."""
    _require(isinstance(inventory, Mapping), "inventario_invalido")
    expected = {
        "format_version", "source_environment_category", "target_environment_category",
        "code_revision", "schema_revision", "services", "configuration_digests",
        "credential_counts", "biometric_counts", "integration_states",
        "whatsapp_binding_counts",
        "live_payment_gate_closed", "unknown_consumer_count", "unknown_service_count",
        "blockers", "approval_fingerprint",
    }
    _require(set(inventory) == expected, "inventario_invalido")
    _require(inventory["format_version"] == 1, "inventario_invalido")
    _require(isinstance(inventory["source_environment_category"], str)
             and inventory["source_environment_category"] in ENVIRONMENT_CATEGORIES
             and inventory["target_environment_category"] == "production", "inventario_invalido")
    _require(isinstance(inventory["code_revision"], str)
             and bool(_GIT_SHA.fullmatch(inventory["code_revision"])), "inventario_invalido")
    _require(isinstance(inventory["schema_revision"], str)
             and bool(_SCHEMA_REVISION.fullmatch(inventory["schema_revision"])), "inventario_invalido")
    _require(isinstance(inventory["configuration_digests"], Mapping)
             and set(inventory["configuration_digests"]) == CONFIG_DIGEST_NAMES
             and all(isinstance(value, str) and bool(_SHA256.fullmatch(value))
                     for value in inventory["configuration_digests"].values()), "inventario_invalido")
    _count_map(inventory["credential_counts"], CREDENTIAL_COUNTERS, "inventario_invalido")
    _count_map(inventory["biometric_counts"], BIOMETRIC_COUNTERS, "inventario_invalido")
    _whatsapp_binding_counts(inventory["whatsapp_binding_counts"])
    _require(isinstance(inventory["integration_states"], Mapping)
             and set(inventory["integration_states"]) == INTEGRATION_NAMES
             and all(isinstance(value, str) and value in INTEGRATION_STATES
                     for value in inventory["integration_states"].values()), "inventario_invalido")
    _require(type(inventory["live_payment_gate_closed"]) is bool, "inventario_invalido")
    for key in ("unknown_consumer_count", "unknown_service_count"):
        _require(type(inventory[key]) is int and inventory[key] >= 0, "inventario_invalido")
    _require(isinstance(inventory["blockers"], list)
             and all(isinstance(value, str) and value in BLOCKER_CATEGORIES
                     for value in inventory["blockers"]), "inventario_invalido")
    fingerprint = inventory["approval_fingerprint"]
    _require(fingerprint is None or (isinstance(fingerprint, str) and bool(_SHA256.fullmatch(fingerprint))),
             "inventario_invalido")
    _require(isinstance(inventory["services"], list), "inventario_invalido")
    seen: set[str] = set()
    for service in inventory["services"]:
        _require(isinstance(service, Mapping)
                 and set(service) == {"name", "status", "health", "image_digest", "revision", "ports"},
                 "inventario_invalido")
        name = service["name"]
        _require(isinstance(name, str) and name in KNOWN_SERVICES and name not in seen,
                 "inventario_invalido")
        seen.add(name)
        _require(isinstance(service["status"], str) and service["status"] in SERVICE_STATUSES
                 and isinstance(service["health"], str) and service["health"] in SERVICE_HEALTH,
                 "inventario_invalido")
        digest, revision = service["image_digest"], service["revision"]
        _require(digest is None or (isinstance(digest, str) and bool(_IMAGE_DIGEST.fullmatch(digest))),
                 "inventario_invalido")
        _require(revision is None or (isinstance(revision, str) and bool(_GIT_SHA.fullmatch(revision))),
                 "inventario_invalido")
        _require(isinstance(service["ports"], list), "inventario_invalido")
        for port in service["ports"]:
            _require(isinstance(port, Mapping) and set(port) == {"binding", "port"}
                     and isinstance(port["binding"], str)
                     and port["binding"] in {"loopback", "public_all", "unknown"}
                     and type(port["port"]) is int and 1 <= port["port"] <= 65535,
                     "inventario_invalido")
    blockers = inventory["blockers"]
    _require((bool(blockers) and fingerprint is None) or (not blockers and fingerprint is not None),
             "inventario_invalido")
    if fingerprint is not None:
        snapshot = {key: value for key, value in inventory.items()
                    if key not in {"blockers", "approval_fingerprint"}}
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode()
        _require(hashlib.sha256(canonical).hexdigest() == fingerprint, "inventario_invalido")
    return json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2)
