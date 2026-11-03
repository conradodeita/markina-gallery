"""Contrato fail-closed da restauração facial; execução externa pertence ao adaptador.

Recibos de simulação nunca constituem autorização ou prova de runtime. Este módulo
não altera banco, aprova calibração, suspende rollout nem executa purge.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

PROJECT = "markina-gallery"
SCHEMA = "20261026_0090"
SERVICES = ("api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker")
FACIAL = SERVICES[2:]
REQUIRED = frozenset(SERVICES) | {"web", "nginx", "db", "redis"}
GATES = frozenset({"security", "privacy", "legal_basis", "calibration", "capacity", "recovery", "human_approval"})
GENERAL_RESTORE_MODE = "owner-authorized-general-restore-v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
OPERATION = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
COMMON_MODULE_CHANGES = frozenset({"app/facial/config.py", "app/facial/rollout.py"})
MODULE_CHANGES_BY_SERVICE = {
    "api": COMMON_MODULE_CHANGES,
    "worker": COMMON_MODULE_CHANGES,
    **{service: COMMON_MODULE_CHANGES | {"app/facial/face_worker.py"} for service in FACIAL},
}
MODEL_MANIFEST_SHA256 = "c8322285b6103a50008ce1082a2ba8a99422cfe1731e160837cba11ebdecf075"


class RestorationError(RuntimeError):
    """Erro sanitizado; nunca interpolar resposta de comando ou segredo."""


def require(condition: object, reason: str) -> None:
    if not condition:
        raise RestorationError(reason)


def digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError):
        raise RestorationError("payload_invalido") from None
    return hashlib.sha256(raw).hexdigest()


def fingerprint(inventory: dict) -> str:
    value = {k: v for k, v in inventory.items() if k != "collected_at"}
    return digest(value)


def validate_inventory(inventory: dict, *, now: datetime | None = None) -> None:
    require(inventory.get("format") == 1 and inventory.get("project") == PROJECT, "inventario_escopo_invalido")
    require(inventory.get("schema") == SCHEMA and inventory.get("architecture") == "arm64", "schema_ou_arquitetura_divergente")
    require(bool(SHA.fullmatch(inventory.get("support_sha", ""))), "sha_suporte_invalido")
    try:
        collected = datetime.fromisoformat(inventory["collected_at"])
        age = ((now or datetime.now(timezone.utc)) - collected).total_seconds()
    except (ValueError, TypeError, KeyError):
        raise RestorationError("timestamp_invalido") from None
    require(0 <= age <= 3600, "inventario_vencido")
    services = inventory.get("services", {})
    require(REQUIRED.issubset(services), "inventario_incompleto")
    for name, item in services.items():
        require(isinstance(item, dict) and HEX.fullmatch(item.get("container_id", "")), "container_invalido")
        require(IMAGE.fullmatch(item.get("image_id", "")), "imagem_invalida")
        require(HEX.fullmatch(item.get("configuration_digest", "")), "configuracao_invalida")
        require(item.get("status") in {"running", "exited", "created"}, "estado_invalido")
        if name not in FACIAL:
            require(item.get("status") == "running" and item.get("health") == "healthy", "servico_nao_saudavel")
        expected_ports = {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]} if name == "nginx" else {}
        require(item.get("ports") == expected_ports, "porta_fora_do_escopo")
        if name in SERVICES:
            require(item.get("compose_files"), "proveniencia_ausente")
    for service in ("api", "worker"):
        require(services[service].get("environment") == "production", "ambiente_divergente")
        require(services[service].get("facial_enabled") == "false", "restauracao_exige_runtime_desligado")


def validate_images(inventory: dict, manifest: dict, observations: dict) -> None:
    require(manifest.get("format") == 1 and SHA.fullmatch(manifest.get("support_sha", "")), "manifesto_invalido")
    require(manifest["support_sha"] == inventory["support_sha"], "suporte_divergente")
    policy = manifest.get("activation_policy", "strict")
    require(policy in {"strict", GENERAL_RESTORE_MODE}, "politica_de_ativacao_invalida")
    if policy == GENERAL_RESTORE_MODE:
        require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,199}",
                                 manifest.get("authorization_reference", ""))), "autorizacao_ausente")
    candidates = manifest.get("services", {})
    require(set(candidates) == set(SERVICES) and set(observations) == set(SERVICES), "candidatos_incompletos")
    for service in SERVICES:
        proof = candidates[service]
        require(proof.get("baseline_image_id") == inventory["services"][service]["image_id"], "baseline_divergente")
        require(IMAGE.fullmatch(proof.get("image_id", "")), "candidato_invalido")
        actual = observations[service]
        require(actual == proof.get("runtime"), "runtime_candidato_divergente")
        require(actual.get("architecture") == "arm64" and actual.get("models_verified") is True, "assets_nao_comprovados")
        require(actual.get("opencv") and actual.get("numpy"), "dependencia_facial_ausente")
        baseline = proof.get("baseline_runtime", {})
        require(actual.get("python") == baseline.get("python"), "python_base_alterado")
        baseline_manifest = baseline.get("model_manifest_sha256")
        require((baseline_manifest is None or baseline_manifest == MODEL_MANIFEST_SHA256)
            and actual.get("model_manifest_sha256") == MODEL_MANIFEST_SHA256, "manifesto_de_modelos_alterado")
        before, after = baseline.get("modules", {}), actual.get("modules", {})
        require(before and set(before) == set(after), "modulos_ausentes_ou_adicionados")
        changed = {k for k in before if before[k] != after[k]}
        require(changed <= MODULE_CHANGES_BY_SERVICE[service], "codigo_fora_da_allowlist")
        expected = proof.get("module_changes", {})
        require(set(expected) == changed and all(after[k] == expected[k] for k in changed), "blob_candidato_divergente")
        before_packages, packages = baseline.get("packages", {}), actual.get("packages", {})
        require(before_packages, "pacotes_baseline_ausentes")
        permitted = proof.get("package_changes", {})
        require(set(permitted) <= {"numpy", "opencv-python-headless"}, "pacote_fora_do_escopo")
        require(packages == {**before_packages, **permitted}, "dependencias_fora_do_escopo")


@dataclass(frozen=True)
class Approval:
    fingerprint: str
    allowlist: tuple[str, ...] = ()
    stage: str = "canary"

    def scope_digest(self) -> str:
        try:
            scope = [str(UUID(value)) for value in self.allowlist]
        except (ValueError, TypeError, AttributeError):
            raise RestorationError("allowlist_invalida") from None
        require(scope and len(set(scope)) == len(scope), "allowlist_vazia_ou_duplicada")
        require(self.stage in {"canary", "limited", "general"}, "etapa_invalida")
        return digest(sorted(scope))


def calibration_admission_proven(manifest: dict, proof: dict, stage: str) -> bool:
    if manifest.get("activation_policy", "strict") == "strict":
        return proof.get("calibration_verified") is True
    return (
        manifest.get("activation_policy") == GENERAL_RESTORE_MODE
        and stage == "general"
        and proof.get("calibration_verified") is False
        and proof.get("calibration_waived") is True
        and bool(manifest.get("authorization_reference"))
        and proof.get("authorization_reference") == manifest["authorization_reference"]
    )


class Host(Protocol):
    def lock(self): ...
    def inventory(self) -> dict: ...
    def prove_images(self, manifest: dict) -> dict: ...
    def prepare(self, operation: str, receipt: dict) -> None: ...
    def load(self, operation: str) -> dict: ...
    def journal(self, operation: str, value: dict, *, create: bool = False) -> None: ...
    def read_journal(self, operation: str) -> dict: ...
    def quiesce(self, operation: str, receipt: dict, record: dict) -> None: ...
    def replace(self, operation: str, receipt: dict, service: str, *, enabled: bool, previous: bool = False) -> str | None: ...
    def verify(self, operation: str, receipt: dict, *, enabled: bool, previous: bool = False) -> dict: ...
    def activation_proof(self, operation: str, approval: Approval) -> dict: ...
    def recovery_proof(self, operation: str, receipt: dict) -> None: ...
    def functional_proof(self, operation: str, approval: Approval) -> dict: ...
    def complete(self, operation: str, result: dict) -> None: ...


def prepare(host: Host, operation: str, manifest: dict) -> dict:
    require(OPERATION.fullmatch(operation), "operacao_invalida")
    with host.lock():
        inventory = host.inventory()
        validate_inventory(inventory)
        observed = host.prove_images(manifest)
        validate_images(inventory, manifest, observed)
        require(fingerprint(host.inventory()) == fingerprint(inventory), "drift_durante_preparacao")
        receipt = {"format": 1, "operation": operation, "inventory": inventory, "manifest": copy.deepcopy(manifest)}
        receipt["fingerprint"] = digest(receipt)
        host.prepare(operation, receipt)
        return {"status": "prepared", "operation": operation, "fingerprint": receipt["fingerprint"]}


def execute(host: Host, operation: str, mode: str, approval: Approval) -> dict:
    require(OPERATION.fullmatch(operation) and mode in {"dark", "activate", "verify", "recover"}, "operacao_ou_fase_invalida")
    with host.lock():
        receipt = host.load(operation)
        expected = digest({k: v for k, v in receipt.items() if k != "fingerprint"})
        require(receipt.get("fingerprint") == expected == approval.fingerprint, "recibo_ou_aprovacao_divergente")
        require(receipt.get("operation") == operation, "operacao_divergente")
        if mode == "dark":
            current = host.inventory()
            validate_inventory(current)
            require(fingerprint(current) == fingerprint(receipt["inventory"]), "inventario_mudou")
            validate_images(current, receipt["manifest"], host.prove_images(receipt["manifest"]))
            host.recovery_proof(operation, receipt)
            record = {"format": 1, "phase": "approved", "fingerprint": expected, "replaced": [], "enabled": False}
            host.journal(operation, record, create=True)
        else:
            record = host.read_journal(operation)
            require(record.get("fingerprint") == expected, "journal_divergente")
            phases = {"approved", "applying_dark", "dark_verified", "activating", "runtime_verified", "functional_verified", "recovering", "complete"}
            require(record.get("format") == 1 and record.get("phase") in phases
                and isinstance(record.get("replaced"), list)
                and len(set(record["replaced"])) == len(record["replaced"])
                and set(record["replaced"]) <= set(SERVICES)
                and record.get("intent", "api") in SERVICES
                and record.get("stop_intent", "api") in SERVICES
                and isinstance(record.get("active_ids", {}), dict)
                and set(record.get("active_ids", {})) <= set(SERVICES)
                and isinstance(record.get("previous_ids", {}), dict)
                and set(record.get("previous_ids", {})) <= set(SERVICES), "journal_invalido")
            if mode == "recover" and record["phase"] == "complete" and record.get("enabled") is False:
                observed = host.verify(operation, receipt, enabled=False, previous=True)
                require(observed.get("schema") == SCHEMA and observed.get("peers_unchanged") is True, "recuperacao_nao_confirmada")
                result = {"status": "complete", "operation": operation, "fingerprint": expected, "enabled": False}
                host.complete(operation, result)
                return result
            if mode == "verify":
                require(record["phase"] in {"runtime_verified", "functional_verified", "complete"}
                    and record.get("enabled") is True, "runtime_nao_verificado")
                require(record.get("scope_digest") == approval.scope_digest(), "escopo_de_verificacao_divergente")
                current_proof = host.activation_proof(operation, approval)
                require(current_proof.get("scope_digest") == approval.scope_digest()
                    and current_proof.get("scope_count") == len(approval.allowlist)
                    and calibration_admission_proven(receipt["manifest"], current_proof, approval.stage)
                    and current_proof.get("stage") == approval.stage
                    and current_proof.get("gates") == sorted(GATES), "gate_revogado_ou_divergente")
                observed = host.verify(operation, receipt, enabled=True)
                require(observed.get("schema") == SCHEMA and observed.get("peers_unchanged") is True, "runtime_mudou")
                proof = host.functional_proof(operation, approval)
                require(proof.get("fingerprint") == expected and proof.get("scope_digest") == approval.scope_digest()
                    and proof.get("request_ready") is True and proof.get("reference_purged") is True
                    and HEX.fullmatch(proof.get("ui_artifact_sha256", "")), "jornada_funcional_nao_comprovada")
                record["phase"] = "functional_verified"
                record["functional_proof_digest"] = digest(proof)
                host.journal(operation, record)
                record["phase"] = "complete"
                host.journal(operation, record)
                result = {"status": "complete", "operation": operation, "fingerprint": expected, "enabled": True}
                host.complete(operation, result)
                return result
            if mode == "activate":
                require(record.get("phase") == "dark_verified", "fase_dark_nao_verificada")
                scope = approval.scope_digest()
                proof = host.activation_proof(operation, approval)
                require(proof.get("scope_digest") == scope and proof.get("scope_count") == len(approval.allowlist), "escopo_nao_comprovado")
                require(proof.get("stage") == approval.stage
                        and calibration_admission_proven(receipt["manifest"], proof, approval.stage),
                        "calibracao_ou_dispensa_nao_comprovada")
                require(proof.get("gates") == sorted(GATES), "gates_nao_comprovados")
                record["activation_proof_digest"] = digest(proof)
                record["scope_digest"] = scope
                record["activation_started_at"] = datetime.now(timezone.utc).isoformat()
        record["phase"] = "recovering" if mode == "recover" else ("activating" if mode == "activate" else "applying_dark")
        host.journal(operation, record)
        # A real host must prove cooperative quiescence. Empty queues alone are insufficient.
        host.quiesce(operation, receipt, record)
        if mode == "recover":
            affected = set(record.get("replaced", []))
            if record.get("intent") in SERVICES:
                affected.add(record["intent"])
            targets = tuple(service for service in reversed(SERVICES) if service in affected)
        else:
            targets = SERVICES if mode == "activate" else SERVICES[:2]
        for service in targets:
            record["intent"] = service
            host.journal(operation, record)
            identity = host.replace(operation, receipt, service, enabled=mode == "activate", previous=mode == "recover")
            if mode == "recover":
                if service in record["replaced"]:
                    record["replaced"].remove(service)
                record.setdefault("active_ids", {}).pop(service, None)
                if identity:
                    record.setdefault("previous_ids", {})[service] = identity
            else:
                if service not in record["replaced"]:
                    record["replaced"].append(service)
                if identity:
                    record.setdefault("active_ids", {})[service] = identity
            record.pop("intent", None)
            host.journal(operation, record)
        observed = host.verify(operation, receipt, enabled=mode == "activate", previous=mode == "recover")
        require(observed.get("schema") == SCHEMA and observed.get("peers_unchanged") is True, "verificacao_final_falhou")
        record["phase"] = {"dark": "dark_verified", "activate": "runtime_verified", "recover": "complete"}[mode]
        record["enabled"] = mode == "activate"
        record["verification_digest"] = digest(observed)
        host.journal(operation, record)
        result = {"status": record["phase"], "operation": operation, "fingerprint": expected, "enabled": mode == "activate"}
        if mode == "recover":
            host.complete(operation, result)
        # Runtime health is not functional proof; a successful activation stays runtime_verified.
        return result
