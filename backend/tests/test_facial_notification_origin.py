"""Origem pública de notificações; somente URLs e dados sintéticos."""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from test_facial_search_worker import Messenger, _base, _create_request, _settings

from app.facial.crypto import FacialCipher
from app.facial.notifications import (
    enqueue_search_notification,
    notification_public_origin,
    process_next_search_notification,
)
from app.messaging import WhatsAppConfigurationError


@pytest.fixture(autouse=True)
def isolated_origins(monkeypatch):
    monkeypatch.delenv("PUBLIC_APP_ORIGIN", raising=False)
    monkeypatch.delenv("MARKINA_PUBLIC_URL", raising=False)


@pytest.mark.parametrize(
    "service",
    [
        "api",
        "worker",
        "face-search-worker",
        "face-index-worker",
        "face-maintenance-worker",
    ],
)
def test_compose_passes_deploy_origin_to_notification_workers(service):
    compose_path = Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert (
        compose["services"][service]["environment"]["PUBLIC_APP_ORIGIN"] == "${PUBLIC_APP_ORIGIN:-}"
    )


def test_canonical_origin_wins_over_local_legacy_default(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina-homolog.example/")
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "http://localhost:3000")
    assert notification_public_origin("staging") == "https://markina-homolog.example"


def test_legacy_public_origin_remains_compatible(monkeypatch):
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "https://gallery.example/")
    assert notification_public_origin("production") == "https://gallery.example"


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "http://localhost:3000",
        "https://localhost",
        "https://localhost.",
        "https://photos.localhost",
        "https://photos.local",
        "https://worker.internal",
        "https://127.0.0.1",
        "https://127.1",
        "https://10.0.0.1",
        "https://169.254.169.254",
        "https://[::1]",
        "https://[::ffff:127.0.0.1]",
        "https://[fc00::1]",
        "http://gallery.example",
        "https://user:password@gallery.example",
        "https://@gallery.example",
        "https://gallery.example/path",
        "https://gallery.example?query=1",
        "https://gallery.example#fragment",
        "https://gallery.example:99999",
        "https://gallery.example:invalid",
        "https://gallery.example:0",
        "https://[broken",
        "https://gallery. example",
        "https://gallery.example\\localhost",
    ],
)
@pytest.mark.parametrize("environment", ["staging", "homologation", "production"])
def test_deployed_environment_rejects_unsafe_origins(monkeypatch, origin, environment):
    monkeypatch.setenv("MARKINA_PUBLIC_URL", origin)
    with pytest.raises(WhatsAppConfigurationError):
        notification_public_origin(environment)


def test_invalid_canonical_origin_does_not_fall_back(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://localhost")
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "https://valid.example")
    with pytest.raises(WhatsAppConfigurationError):
        notification_public_origin("staging")


@pytest.mark.parametrize("environment", ["development", "test", "local"])
def test_local_execution_allows_local_http(monkeypatch, environment):
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "http://localhost:3000")
    assert notification_public_origin(environment) == "http://localhost:3000"


@pytest.mark.parametrize("valid", [True, False])
def test_outbox_sends_public_link_once_or_rejects_before_provider(tmp_path, monkeypatch, valid):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv(
        "PUBLIC_APP_ORIGIN", "https://markina-homolog.example" if valid else "https://localhost"
    )
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "http://localhost:3000")
    engine, db, gallery, client, _folder = _base(tmp_path)
    settings = _settings(tmp_path)
    request = _create_request(db, gallery, client, settings)
    request.status = "ready"
    settings = replace(settings, environment="staging")
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    notification = enqueue_search_notification(
        db, request=request, result_status="ready", cipher=cipher, settings=settings
    )
    db.commit()
    provider = Messenger()
    assert process_next_search_notification(db, provider=provider, cipher=cipher, settings=settings)
    db.refresh(notification)
    if valid:
        assert provider.calls == [
            (
                client.phone_e164,
                f"Sua busca na galeria foi concluída. Confira as possibilidades em https://markina-homolog.example/public-galleries/{gallery.id}",
                notification.idempotency_key,
            )
        ]
        assert notification.status == "sent"
        assert not process_next_search_notification(
            db, provider=provider, cipher=cipher, settings=settings
        )
        assert len(provider.calls) == 1
    else:
        assert provider.calls == []
        assert notification.status == "queued"
        assert notification.last_error_category == "channel_unavailable"
    assert request.status == "ready"
    db.close()
    engine.dispose()
