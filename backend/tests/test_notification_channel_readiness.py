"""Capacidade WhatsApp isolada por tenant; sem conexão de rede ou commit."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import whatsapp_channel as channel
from app.messaging import WhatsAppDeliveryError


@pytest.mark.parametrize("state,connected,expected", [
    ("open", "+5511999991234", True),
    ("open", "+5511999999876", False),
    ("close", "+5511999991234", False),
    ("connecting", "+5511999991234", False),
])
def test_live_identity_is_checked_instead_of_cached_ready(monkeypatch, state, connected, expected):
    tenant = uuid4()
    calls = []
    provider = SimpleNamespace(
        binding=SimpleNamespace(name="evolution"),
        validate=lambda: calls.append("validated"),
        connection_status=lambda: SimpleNamespace(state=state, connected_phone_e164=connected),
    )

    def own_provider(db, *, tenant_id):
        assert tenant_id == tenant
        return provider

    monkeypatch.setattr(channel, "provider_for", own_provider)
    monkeypatch.setattr(channel, "channel_settings", lambda db, *, tenant_id: SimpleNamespace(
        status="ready", expected_phone_e164="+5511999991234" if tenant_id == tenant else None))
    assert channel.notification_channel_ready(object(), tenant_id=tenant) is expected
    assert calls == ["validated"]


def test_missing_phone_or_transport_error_blocks_only_capability(monkeypatch):
    def unavailable():
        raise WhatsAppDeliveryError("synthetic", transient=True)

    monkeypatch.setattr(channel, "provider_for", lambda *a, **k: SimpleNamespace(
        binding=SimpleNamespace(name="evolution"), connection_status=unavailable))
    monkeypatch.setattr(channel, "channel_settings", lambda *a, **k: SimpleNamespace(
        status="ready", expected_phone_e164="+5511999991234"))
    assert not channel.notification_channel_ready(object(), tenant_id=uuid4())


@pytest.mark.parametrize("environment,expected", [("development", True), ("test", True), ("production", False)])
def test_sandbox_cannot_unlock_production(monkeypatch, environment, expected):
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setattr(channel, "provider_for", lambda *a, **k: SimpleNamespace(binding=SimpleNamespace(name="sandbox")))
    monkeypatch.setattr(channel, "channel_settings", lambda *a, **k: SimpleNamespace(status="sandbox"))
    assert channel.notification_channel_ready(object(), tenant_id=uuid4()) is expected


def test_ready_tenant_does_not_unlock_another_without_a_number(monkeypatch):
    ready_tenant, pending_tenant = uuid4(), uuid4()
    seen = []

    def provider_for(db, *, tenant_id):
        seen.append(tenant_id)
        return SimpleNamespace(binding=SimpleNamespace(name="evolution"), validate=lambda: None,
                               connection_status=lambda: SimpleNamespace(state="open", connected_phone_e164="+5511999991234"))

    monkeypatch.setattr(channel, "provider_for", provider_for)
    monkeypatch.setattr(channel, "channel_settings", lambda db, *, tenant_id: SimpleNamespace(
        status="ready", expected_phone_e164="+5511999991234" if tenant_id == ready_tenant else None))
    assert channel.notification_channel_ready(object(), tenant_id=ready_tenant)
    assert not channel.notification_channel_ready(object(), tenant_id=pending_tenant)
    assert seen == [ready_tenant, pending_tenant]
