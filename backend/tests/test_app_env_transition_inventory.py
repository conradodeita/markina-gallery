"""Guarda a matriz de consumidores de ambiente usada pela transição controlada."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "backend" / "app"
COMPOSE = ROOT / "docker" / "docker-compose.yml"

MARKER = re.compile(
    r"\bAPP_ENV\b|INTEGRATION_SECRET_ENV|CREDENTIAL_ENV|"
    r"INTEGRATION_SECRET_(?:KEYS|ACTIVE_KEY_ID)|FACIAL_AEAD|"
    r"PUSH_SUBSCRIPTION_ENCRYPTION_KEY|WHATSAPP_OTP_ENCRYPTION_KEY"
)

EXPECTED_REFERENCE_LINE_COUNTS = {
    "backend/app/admin_security.py": 1,
    "backend/app/auth.py": 2,
    "backend/app/email_delivery.py": 4,
    "backend/app/environment_transition_inventory.py": 2,
    "backend/app/facial/config.py": 6,
    "backend/app/facial/reference_store.py": 1,
    "backend/app/gallery_access.py": 2,
    "backend/app/homolog_cleanup.py": 3,
    "backend/app/integration_secrets.py": 4,
    "backend/app/main.py": 3,
    "backend/app/mercadopago_settings.py": 1,
    "backend/app/messaging.py": 3,
    "backend/app/push_subscriptions.py": 2,
    "backend/app/system_monitor/report.py": 1,
    "backend/app/tenant_hosts.py": 1,
    "backend/app/whatsapp_binding.py": 5,
    "backend/app/whatsapp_channel.py": 1,
    "backend/app/whatsapp_delivery.py": 1,
}

EXPECTED_COMPOSE_SERVICES = {
    "api",
    "face-index-worker",
    "face-maintenance-worker",
    "face-search-worker",
    "worker",
}


def test_environment_and_credential_consumers_match_reviewed_matrix() -> None:
    observed: dict[str, int] = {}
    for path in SOURCE_ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        count = sum(bool(MARKER.search(line)) for line in path.read_text(encoding="utf-8").splitlines())
        if count:
            observed[relative] = count

    assert observed == EXPECTED_REFERENCE_LINE_COUNTS


def test_compose_environment_consumers_match_reviewed_matrix() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    observed = {
        name
        for name, service in compose["services"].items()
        if "APP_ENV" in service.get("environment", {})
    }

    assert observed == EXPECTED_COMPOSE_SERVICES
