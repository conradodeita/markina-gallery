"""Validate a minimized production inventory before retirement approval."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

EXPECTED_HOST = "clearbudget-vnic"
EXPECTED_ROOT = "/opt/markina-gallery"
EXPECTED_PROJECT = "markina-gallery"
EXPECTED_URL = "https://markina.pickyourpic.com.br"
EXPECTED_SCHEMA = "20261021_0086"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _strict_keys(value: Any, expected: set[str], label: str) -> bool:
    return isinstance(value, dict) and set(value) == expected


def evaluate(inventory: dict[str, Any]) -> tuple[bool, str, str | None]:
    """Return readiness, refusal reason, and fingerprint of sanitized evidence."""
    top_keys = {
        "host", "project", "root", "target_sha", "main_sha", "checkout_sha",
        "active_sha", "database_revision", "public_url", "nginx_bind",
        "services", "compose_hashes", "binding", "https_health",
    }
    if not _strict_keys(inventory, top_keys, "inventory"):
        return False, "inventario_com_campos_ausentes_ou_extras", None
    for key in ("target_sha", "main_sha", "checkout_sha", "active_sha"):
        if not isinstance(inventory[key], str) or not SHA1.fullmatch(inventory[key]):
            return False, f"sha_invalido:{key}", None
    if inventory["target_sha"] != inventory["main_sha"]:
        return False, "alvo_nao_e_head_da_main", None
    if inventory["checkout_sha"] != inventory["active_sha"]:
        return False, "checkout_nao_corresponde_ao_runtime", None
    for key, expected in (("host", EXPECTED_HOST), ("project", EXPECTED_PROJECT),
                          ("root", EXPECTED_ROOT), ("public_url", EXPECTED_URL),
                          ("database_revision", EXPECTED_SCHEMA)):
        if inventory[key] != expected:
            return False, f"inventario_diverge:{key}", None
    if inventory["nginx_bind"] != "127.0.0.1:8080->80/tcp":
        return False, "bind_nginx_diverge", None
    hashes = inventory["compose_hashes"]
    if not _strict_keys(hashes, {"api", "web", "worker"}, "compose_hashes") or any(
        not isinstance(value, str) or not SHA256.fullmatch(value)
        for value in hashes.values()
    ):
        return False, "hash_compose_invalido", None
    services = inventory["services"]
    if not isinstance(services, dict) or not services or any(
        not isinstance(name, str) or not name or not isinstance(state, str)
        or state not in {"healthy", "running"}
        for name, state in services.items()
    ):
        return False, "servico_ausente_ou_nao_saudavel", None
    if not {"api", "web", "worker", "db", "redis", "nginx"}.issubset(services):
        return False, "servicos_criticos_ausentes", None
    if any(services[name] != "healthy" for name in ("api", "web", "worker", "db", "redis", "nginx")):
        return False, "servico_critico_nao_saudavel", None
    if not _strict_keys(inventory["https_health"], {"healthz", "api_health", "web"}, "https_health") \
            or any(value is not True for value in inventory["https_health"].values()):
        return False, "smoke_https_falhou", None
    binding = inventory["binding"]
    if not _strict_keys(binding, {"path", "type", "symlink", "mode", "size_bytes", "link_count",
                                  "mtime_ns", "inode", "device", "uid",
                                  "compose_consumers", "host_references", "target_references"}, "binding"):
        return False, "metadados_binding_incompletos", None
    path = binding["path"]
    if not isinstance(path, str):
        return False, "caminho_binding_fora_do_projeto", None
    if "\\" in path:
        candidate = PureWindowsPath(path)
        root = PureWindowsPath(EXPECTED_ROOT)
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            return False, "caminho_binding_fora_do_projeto", None
        if not candidate.is_absolute() or not relative.parts:
            return False, "caminho_binding_fora_do_projeto", None
    elif not PurePosixPath(path).is_absolute() or not path.startswith(EXPECTED_ROOT.rstrip("/") + "/"):
        return False, "caminho_binding_fora_do_projeto", None
    if binding["type"] != "regular_file" or binding["symlink"] is not False:
        return False, "binding_nao_e_arquivo_regular", None
    if binding["mode"] not in ("0600", "0640") or not isinstance(binding["size_bytes"], int) \
            or isinstance(binding["size_bytes"], bool) or binding["size_bytes"] <= 0:
        return False, "metadados_binding_invalidos", None
    if not isinstance(binding["link_count"], int) or isinstance(binding["link_count"], bool) \
            or binding["link_count"] != 1:
        return False, "binding_compartilhado_por_hardlink", None
    if binding["compose_consumers"] != ["markina-gallery/api"]:
        return False, "binding_compartilhado_ou_consumidor_desconhecido", None
    if binding["host_references"] != [] or binding["target_references"] != []:
        return False, "binding_referenciado_por_outro_arquivo", None
    # Include only minimized operational metadata in the approval fingerprint.
    canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
    return True, "inventario_apto_a_apresentacao", hashlib.sha256(canonical).hexdigest()


def binding_removal_allowed(
    approved_inventory: dict[str, Any],
    current_binding: dict[str, Any],
    *,
    runtime_healthy: bool,
    compose_consumers: list[str],
    host_references: list[str],
    target_references: list[str],
) -> tuple[bool, str]:
    ready, _, _ = evaluate(approved_inventory)
    if not ready:
        return False, "inventario_aprovado_invalido"
    approved = approved_inventory["binding"]
    identity = ("path", "type", "symlink", "mode", "size_bytes", "link_count", "mtime_ns", "inode", "device", "uid")
    if not _strict_keys(current_binding, set(approved), "current_binding"):
        return False, "metadados_binding_atual_incompletos"
    if any(current_binding[key] != approved[key] for key in identity):
        return False, "binding_mudou_apos_inventario"
    if current_binding["type"] != "regular_file" or current_binding["symlink"] is not False \
            or current_binding["link_count"] != 1:
        return False, "binding_atual_nao_exclusivo"
    if not runtime_healthy:
        return False, "runtime_nao_saudavel"
    if compose_consumers or host_references or target_references:
        return False, "binding_ainda_referenciado"
    return True, "binding_exclusivo_apto_a_remocao"


def main() -> int:
    try:
        inventory = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("retirement_inventory_ready=false")
        print("criterio=json_invalido")
        return 1
    if not isinstance(inventory, dict):
        print("retirement_inventory_ready=false")
        print("criterio=inventario_invalido")
        return 1
    ready, reason, fingerprint = evaluate(inventory)
    print(f"retirement_inventory_ready={'true' if ready else 'false'}")
    print(f"criterio={reason}")
    if not ready:
        return 1
    print("inventario_sanitizado=" + json.dumps(inventory, sort_keys=True, separators=(",", ":")))
    print(f"approval_fingerprint={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
