"""Valida e resume o recibo sanitizado do inventário APP_ENV."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.environment_transition_inventory import render_environment_inventory
from scripts.app_env_transition_inventory import (
    SAFE_FAILURE_CODES,
    UNKNOWN_FAILURE_CODE,
    validate_biometric_origin,
)

SHA = re.compile(r"[0-9a-f]{40}\Z")
FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
REPORT_FIELDS = {
    "target_sha",
    "collection_status",
    "inventory",
    "blockers",
    "approval_fingerprint",
    "failure_category",
}


def validate_report(lines: list[str], target_sha: str) -> dict:
    if not SHA.fullmatch(target_sha) or len(lines) != 1:
        raise ValueError("relatorio_invalido")
    try:
        report = json.loads(lines[0])
    except (TypeError, json.JSONDecodeError):
        raise ValueError("relatorio_invalido") from None
    if not isinstance(report, dict) or set(report) not in (
        REPORT_FIELDS, REPORT_FIELDS | {"biometric_origin"},
    ):
        raise ValueError("relatorio_invalido")
    if report["target_sha"] != target_sha:
        raise ValueError("relatorio_invalido")

    if report["collection_status"] == "incomplete":
        if ("biometric_origin" in report or report["inventory"] is not None
                or report["blockers"] != ["coleta_incompleta"]
                or report["approval_fingerprint"] is not None
                or not isinstance(report["failure_category"], str)
                or report["failure_category"] not in SAFE_FAILURE_CODES | {UNKNOWN_FAILURE_CODE}):
            raise ValueError("relatorio_invalido")
        return report

    if (report["collection_status"] != "complete"
            or not isinstance(report["inventory"], dict)
            or report["failure_category"] is not None):
        raise ValueError("relatorio_invalido")
    try:
        rendered = render_environment_inventory(report["inventory"])
    except (TypeError, ValueError):
        raise ValueError("relatorio_invalido") from None
    inventory = json.loads(rendered)
    if "biometric_origin" in report:
        try:
            validate_biometric_origin(report["biometric_origin"],
                                     inventory["biometric_counts"]["photo_embeddings"])
        except RuntimeError:
            raise ValueError("relatorio_invalido") from None
    if report["blockers"] != inventory["blockers"]:
        raise ValueError("relatorio_invalido")
    fingerprint = inventory["approval_fingerprint"]
    if report["approval_fingerprint"] != fingerprint:
        raise ValueError("relatorio_invalido")
    if fingerprint is not None and not FINGERPRINT.fullmatch(fingerprint):
        raise ValueError("relatorio_invalido")
    return report


def summary(report: dict) -> str:
    lines = [
        "## Inventário APP_ENV de produção (somente leitura)",
        "",
        f"- Commit solicitado: `{report['target_sha']}`",
        f"- Coleta: `{report['collection_status']}`",
    ]
    inventory = report["inventory"]
    if inventory is None:
        lines.extend([
            "- Fontes: incompletas; o relatório não autoriza alteração.",
            f"- Categoria sanitizada: `{report['failure_category']}`",
            "- Fingerprint: indisponível",
        ])
    else:
        lines.extend([
            f"- Código ativo: `{inventory['code_revision']}`",
            f"- Schema: `{inventory['schema_revision']}`",
            f"- Ambiente de origem: `{inventory['source_environment_category']}`",
            f"- Ambiente alvo: `{inventory['target_environment_category']}`",
            f"- Gate de pagamentos reais fechado: `{inventory['live_payment_gate_closed']}`",
            f"- Integrações externas: `{json.dumps(inventory['integration_states'], sort_keys=True)}`",
            f"- Contagens de credenciais: `{json.dumps(inventory['credential_counts'], sort_keys=True)}`",
            f"- Contagens biométricas: `{json.dumps(inventory['biometric_counts'], sort_keys=True)}`",
            f"- Vínculos WhatsApp por categoria/estado: `{json.dumps(inventory['whatsapp_binding_counts'], sort_keys=True)}`",
            f"- Consumidores desconhecidos: `{inventory['unknown_consumer_count']}`",
            f"- Serviços desconhecidos: `{inventory['unknown_service_count']}`",
            "",
            "| Serviço | Estado | Saúde | Revisão | Imagem | Portas |",
            "|---|---|---|---|---|---|",
        ])
        for service in inventory["services"]:
            ports = ", ".join(
                f"{port['binding']}:{port['port']}" for port in service["ports"]
            ) or "—"
            lines.append(
                f"| {service['name']} | {service['status']} | {service['health']} "
                f"| `{service['revision'] or '—'}` | `{service['image_digest'] or '—'}` | {ports} |"
            )
        fingerprint = inventory["approval_fingerprint"]
        lines.extend([
            "",
            f"- Fingerprint: `{fingerprint or 'indisponível'}`",
        ])
    blockers = report["blockers"]
    if "biometric_origin" in report:
        lines.extend(["", "### Diagnóstico de índices (contagens; não autoriza transição)",
                      f"`{json.dumps(report['biometric_origin'], sort_keys=True)}`"])
    lines.extend(["", "### Bloqueios"])
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- Nenhum")
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("uso: app_env_transition_inventory_report.py INPUT SHA OUTPUT SUMMARY")
    input_path = Path(sys.argv[1])
    target_sha = sys.argv[2]
    output_path = Path(sys.argv[3])
    summary_path = Path(sys.argv[4])
    report = validate_report(input_path.read_text(encoding="utf-8").splitlines(), target_sha)
    fingerprint = report["approval_fingerprint"] or ""
    output_path.write_text(f"approval_fingerprint={fingerprint}\n", encoding="utf-8")
    with summary_path.open("a", encoding="utf-8") as output:
        output.write(summary(report))


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        raise SystemExit("relatorio APP_ENV inválido") from None
