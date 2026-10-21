"""HTTP real em ASGI/PostgreSQL: autenticação e ownership não são mockados."""

import asyncio
import json
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import admin_account, main
from app.auth import (
    AdminSecurityChallenge,
    AuditEvent,
    InfinitePayCredential,
    InfinitePaySettings,
    ProviderPayment,
    TenantAdmin,
)
from app.infinitepay_binding import api_key_configured, api_key_for_tenant
from app.infinitepay_credentials import credential_key, rotate_secrets
from app.integration_secrets import IntegrationSecretError
from tests.test_integration_secrets import secret_keyring  # noqa: F401
from tests.test_tenant_configuration import PASSWORD
from tests.test_tenant_configuration import client_db as _client_db
from tests.test_tenant_configuration import configured as _configured
from tests.test_tenant_configuration import graph as _graph
from tests.test_tenant_configuration import links as _links

client_db, configured, graph, links = _client_db, _configured, _graph, _links


@pytest.fixture(autouse=True)
def secure_runtime(monkeypatch, secret_keyring, client_db):  # noqa: F811
    monkeypatch.delenv("INFINITEPAY_TENANT_BINDINGS", raising=False)
    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")

    def session():
        with Session(client_db.bind, expire_on_commit=False) as db:
            yield db

    main.app.dependency_overrides[main.db_session] = session
    yield
    main.app.dependency_overrides.clear()


def request(row, path="", body=None, *, client=False, authenticated=True, origin=None):
    host = f"http://{row['tenant'].canonical_host}"
    headers = {"origin": origin or host}
    if authenticated:
        headers["cookie"] = row["customer_request" if client else "admin_request"].headers["cookie"]

    async def invoke():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url=host) as api:
            return await api.request("POST" if body is not None else "GET",
                                     f"/admin/settings/infinitepay{path}", json=body, headers=headers)

    return asyncio.run(invoke())


def issue(row, *, key=None, handle="synthetic_tag", version=None, enabled=True):
    if version is None:
        version = request(row).json()["version"]
    body = {"current_password": PASSWORD, "expected_version": version,
            "configuration": {"handle": handle} if handle else None,
            "checkout_ready": bool(handle), "card_enabled": bool(handle and enabled)}
    if key is not None:
        body["api_key"] = key
    return request(row, "/challenge", body)


def confirm(row, challenge):
    return request(row, "/confirm", {"challenge_id": challenge.json()["challenge_id"], "code": "123456"})


def save(row, key, handle="synthetic_tag"):
    challenge = issue(row, key=key, handle=handle)
    assert challenge.status_code == 202, challenge.text
    response = confirm(row, challenge)
    assert response.status_code == 200, response.text
    return response


def test_two_tenants_store_only_ciphertext_and_read_own_status(client_db, configured, caplog):
    first, second = configured
    keys = ("synthetic-credential-A", "synthetic-credential-B")
    for row, key, tag in zip(configured, keys, ("tag_a", "tag_b"), strict=True):
        challenge = issue(row, key=key, handle=tag)
        assert challenge.status_code == 202, challenge.text
        assert set(challenge.json()["proposal"]) == {"handle", "version", "checkout_ready", "card_enabled"}
        assert key not in challenge.text and "ciphertext" not in challenge.text
        stored = client_db.get(AdminSecurityChallenge, UUID(challenge.json()["challenge_id"]))
        assert key not in stored.encrypted_target
        response = confirm(row, challenge)
        assert response.status_code == 200, response.text
        assert response.json()["credential_status"] == "stored"
        assert response.json()["credential_validation"] == "unavailable"
        assert response.json()["ownership_verified"] is False
        assert response.headers["cache-control"] == "no-store"
        assert key not in response.text
    client_db.expire_all()
    rows = list(client_db.scalars(select(InfinitePayCredential)))
    assert len(rows) == 2
    for row, key in zip(configured, keys, strict=True):
        secret = next(item for item in rows if item.tenant_id == row["tenant"].id)
        assert key.encode() not in secret.ciphertext and secret.nonce
        assert api_key_for_tenant(row["tenant"].id, db=client_db) == key
    assert request(first, f"?tenant_id={second['tenant'].id}").json()["handle"] == "tag_a"
    assert all(key not in caplog.text for key in keys)
    audit_text = json.dumps([(event.event, event.subject) for event in client_db.scalars(select(AuditEvent))])
    assert all(key not in audit_text for key in keys)


def test_http_rejects_missing_role_csrf_idor_and_foreign_challenge(client_db, configured):
    first, second = configured
    assert request(first, authenticated=False).status_code == 403
    assert request(first, client=True).status_code == 403
    payload = {"current_password": PASSWORD, "expected_version": 0,
               "configuration": {"handle": "tag_a"}, "api_key": "synthetic-secret"}
    assert request(first, "/challenge", payload, origin="https://foreign.test").status_code == 403
    payload["tenant_id"] = str(second["tenant"].id)
    response = request(first, "/challenge", payload)
    assert response.status_code == 422 and "synthetic-secret" not in response.text
    challenge = issue(first, key="synthetic-secret-A")
    assert challenge.status_code == 202
    assert confirm(second, challenge).status_code == 401
    assert request(second, "/resend", {"challenge_id": challenge.json()["challenge_id"]}).status_code == 401
    client_db.expire_all()
    stored = client_db.get(AdminSecurityChallenge, UUID(challenge.json()["challenge_id"]))
    assert stored.used_at is None and stored.attempts == 0
    link = client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == first["tenant"].id))
    link.active = False
    client_db.commit()
    assert confirm(first, challenge).status_code in (401, 403)
    assert not list(client_db.scalars(select(InfinitePayCredential)))


def test_secret_validation_and_missing_master_fail_without_leaks(client_db, configured, monkeypatch):
    first = configured[0]
    response = issue(first, key="x" * 600)
    assert response.status_code == 422 and "x" * 600 not in response.text
    assert issue(first, key="bad\nheader").status_code == 422
    assert issue(first).status_code == 409
    monkeypatch.delenv("INTEGRATION_SECRET_KEYS")
    response = issue(first, key="synthetic-private-value")
    assert response.status_code == 503 and "synthetic-private-value" not in response.text
    assert request(first).json()["credential_storage_available"] is False
    assert not list(client_db.scalars(select(InfinitePayCredential)))
    assert not list(client_db.scalars(select(InfinitePaySettings)))


def test_replace_disconnect_no_fallback_and_other_tenant_unchanged(client_db, configured, monkeypatch):
    first, second = configured
    save(first, "synthetic-old-a")
    save(second, "synthetic-b", "tag_b")
    client_db.expire_all()
    previous = client_db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == first["tenant"].id)).credential_id
    save(first, "synthetic-new-a")
    client_db.expire_all()
    assert credential_key(client_db, tenant_id=first["tenant"].id, credential_id=previous) == "synthetic-old-a"
    with pytest.raises(IntegrationSecretError):
        credential_key(client_db, tenant_id=second["tenant"].id, credential_id=previous)
    disconnect = issue(first, handle=None)
    assert confirm(first, disconnect).status_code == 200
    client_db.expire_all()
    assert all(item.ciphertext is None and item.revoked_at for item in client_db.scalars(
        select(InfinitePayCredential).where(InfinitePayCredential.tenant_id == first["tenant"].id)))
    monkeypatch.setenv("INFINITEPAY_TENANT_BINDINGS", json.dumps({str(first["tenant"].id): "A"}))
    monkeypatch.setenv("INFINITEPAY_BINDING_A_CREDENTIAL_ENV", "development")
    monkeypatch.setenv("INFINITEPAY_BINDING_A_API_KEY", "synthetic-legacy-fallback")
    assert not api_key_configured(first["tenant"].id, db=client_db)
    assert api_key_for_tenant(second["tenant"].id, db=client_db) == "synthetic-b"


def test_pending_payment_blocks_disconnect_but_keeps_previous_key(client_db, configured):
    first = configured[0]
    save(first, "synthetic-old")
    client_db.expire_all()
    settings = client_db.scalar(select(InfinitePaySettings))
    previous = settings.credential_id
    late_disconnect = issue(first, handle=None)
    assert late_disconnect.status_code == 202
    payment = ProviderPayment(tenant_id=first["tenant"].id, client_id=first["client"].id,
        checkout_key=str(uuid4()), cart_revision="synthetic", total_cents=5, handle_snapshot=settings.handle,
        configuration_version=settings.version, verification_profile="infinitepay-public-v1",
        credential_id=previous, state="verification_required")
    client_db.add(payment)
    client_db.commit()
    assert confirm(first, late_disconnect).status_code == 409
    assert issue(first, handle=None).status_code == 409
    save(first, "synthetic-new")
    client_db.refresh(payment)
    assert payment.credential_id == previous and payment.state == "verification_required"
    assert credential_key(client_db, tenant_id=first["tenant"].id, credential_id=previous) == "synthetic-old"
    challenge = issue(first, enabled=False)
    assert confirm(first, challenge).json()["card_enabled"] is False


def test_master_rotation_preserves_identity_and_failure_never_falls_back(client_db, configured, monkeypatch):
    first = configured[0]
    save(first, "synthetic-original")
    client_db.expire_all()
    setting = client_db.scalar(select(InfinitePaySettings))
    identity = setting.credential_id
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "new")
    assert rotate_secrets(client_db, tenant_id=first["tenant"].id) == {
        "checked": 1, "requiring_rotation": 1, "applied": False}
    assert client_db.get(InfinitePayCredential, identity).key_id == "old"
    rotate_secrets(client_db, tenant_id=first["tenant"].id, apply=True)
    client_db.commit()
    assert api_key_for_tenant(first["tenant"].id, db=client_db) == "synthetic-original"
    assert setting.credential_id == identity
    client_db.get(InfinitePayCredential, identity).ciphertext = b"tampered" * 3
    client_db.commit()
    assert request(first).json()["credential_status"] == "unavailable"
    assert not api_key_configured(first["tenant"].id, db=client_db)


def test_rotation_cli_defaults_to_dry_run_and_requires_explicit_confirmation(client_db, configured, monkeypatch, capsys):
    from app import rotate_infinitepay_secrets as cli

    first, second = configured
    save(first, "synthetic-cli-a")
    save(second, "synthetic-cli-b")
    tenant = str(first["tenant"].id)
    monkeypatch.setattr(cli, "SessionLocal", lambda: Session(client_db.bind, expire_on_commit=False))
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "new")
    assert cli.main(["--tenant-id", tenant]) == 0
    assert json.loads(capsys.readouterr().out) == {"tenant_id": tenant, "checked": 1,
        "requiring_rotation": 1, "applied": False}
    client_db.expire_all()
    assert all(row.key_id == "old" for row in client_db.scalars(select(InfinitePayCredential)))
    with pytest.raises(SystemExit):
        cli.main(["--tenant-id", tenant, "--apply"])
    capsys.readouterr()
    assert cli.main(["--tenant-id", tenant, "--apply", "--confirmation", tenant]) == 0
    report = capsys.readouterr().out
    assert "synthetic-cli" not in report
    client_db.expire_all()
    versions = {row.tenant_id: row.key_id for row in client_db.scalars(select(InfinitePayCredential))}
    assert versions == {first["tenant"].id: "new", second["tenant"].id: "old"}
    assert credential_key(client_db, tenant_id=first["tenant"].id,
        credential_id=client_db.scalar(select(InfinitePaySettings.credential_id)
            .where(InfinitePaySettings.tenant_id == first["tenant"].id))) == "synthetic-cli-a"


def test_rotation_cli_error_is_neutral_and_transaction_rolls_back(client_db, configured, monkeypatch, capsys):
    from app import rotate_infinitepay_secrets as cli

    first = configured[0]
    save(first, "synthetic-first")
    save(first, "synthetic-second")
    rows = list(client_db.scalars(select(InfinitePayCredential)))
    rows[-1].ciphertext = b"tampered" * 3
    client_db.commit()
    monkeypatch.setattr(cli, "SessionLocal", lambda: Session(client_db.bind, expire_on_commit=False))
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "new")
    tenant = str(first["tenant"].id)
    assert cli.main(["--tenant-id", tenant, "--apply", "--confirmation", tenant]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "error": "Recifragem não concluída; nenhuma alteração foi aplicada."}
    client_db.expire_all()
    assert all(row.key_id == "old" for row in client_db.scalars(select(InfinitePayCredential)))


def test_callback_with_A_identifiers_checks_only_B_credential_and_cannot_confirm_B(client_db, configured, monkeypatch):
    first, _second = configured
    payments = []
    for row, key, tag in zip(configured, ("synthetic-a", "synthetic-b"), ("tag_a", "tag_b"), strict=True):
        save(row, key, tag)
        client_db.expire_all()
        settings = client_db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == row["tenant"].id))
        payment = ProviderPayment(tenant_id=row["tenant"].id, client_id=row["client"].id,
            checkout_key=str(uuid4()), cart_revision="synthetic", total_cents=5, handle_snapshot=tag,
            configuration_version=settings.version, credential_id=settings.credential_id,
            verification_profile="infinitepay-public-v1", state="awaiting_payment")
        client_db.add(payment)
        client_db.flush()
        row["order"].provider_payment_id = payment.id
        payments.append(payment)
        client_db.commit()
    seen = []
    original_client = httpx.Client

    def provider(request):
        seen.append((request.headers["x-api-key"], json.loads(request.content)))
        # A transação de A não corresponde a pedido/recebedor de B no provedor.
        return httpx.Response(200, json={"success": True, "paid": False})

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(provider)))
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")

    async def invoke():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="https://pick.example.test") as api:
            return await api.get("/infinitepay/return", params={"order_nsu": str(payments[1].id),
                "transaction_nsu": "transaction-from-A", "slug": "slug-from-A", "tenant_id": str(first["tenant"].id)})

    response = asyncio.run(invoke())
    assert response.status_code == 303
    client_db.expire_all()
    assert all(payment.state == "awaiting_payment" and payment.provider_transaction_nsu is None for payment in payments)
    assert all(row["order"].payment_status == "pending" for row in configured)
    assert seen == [("synthetic-b", {"handle": "tag_b", "order_nsu": str(payments[1].id),
        "transaction_nsu": "transaction-from-A", "slug": "slug-from-A"})]
