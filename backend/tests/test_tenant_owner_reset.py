"""Reset proprietário ensaiado exclusivamente em schema PostgreSQL descartável."""
import importlib.util
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

module_spec = importlib.util.spec_from_file_location(
    "owner_reset", Path(__file__).resolve().parents[2] / "scripts" / "reset_homolog_owner.py")
reset = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(reset)
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app import auth, homolog_cleanup
from app.system_monitor import models as monitor

OWNER_EMAIL = "owner@example.test"


@pytest.fixture
def graph(monkeypatch, tmp_path):
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requer PostgreSQL descartável explicitamente configurado")
    engine = create_engine(url)
    schema = "owner_reset_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    auth.Base.metadata.create_all(scoped)
    monkeypatch.setenv("APP_ENV", "homolog")
    media = {name: tmp_path / name for name in reset.MEDIA_ROOTS}
    for name, root in media.items():
        root.mkdir()
        (root / "test-acervo.jpg").write_bytes(b"synthetic operational media")
        monkeypatch.setenv(reset.ROOT_ENV[name], str(root))
    monkeypatch.setattr(reset, "MEDIA_ROOTS", media)
    brand = tmp_path / "branding"
    brand.mkdir()
    monkeypatch.setattr(reset, "BRANDING_ROOT", brand)
    monkeypatch.setenv("BRANDING_ASSETS_ROOT", str(brand))
    with Session(scoped, expire_on_commit=False) as db:
        admins, tenants = [], []
        for i in range(5):
            tenant = auth.Tenant(status="active")
            admin = auth.AdminUser(email=OWNER_EMAIL if i == 0 else f"test-{i}@example.test",
                                   password_hash=f"synthetic-password-{i}", totp_secret=f"synthetic-totp-{i}",
                                   email_verified=True)
            db.add_all([tenant, admin])
            db.flush()
            db.add(auth.TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id, active=True))
            db.flush()
            db.add_all([
                auth.AuthSession(tenant_id=tenant.id, role="admin", subject_id=admin.id,
                                 admin_subject_id=admin.id, token_hash=f"synthetic-session-{i}",
                                 expires_at=auth.now() + timedelta(days=7)),
                auth.NotificationSetting(tenant_id=tenant.id, event_type="first_access",
                                         whatsapp_body=f"synthetic-preference-{i}",
                                         push_title="Synthetic title", push_body="Synthetic body"),
                auth.WhatsAppChannelSettings(tenant_id=tenant.id, environment="homolog", status="ready"),
            ])
            client = auth.Client(tenant_id=tenant.id, full_name="Synthetic client", phone_e164=f"+551199999990{i}")
            gallery = auth.ParentGallery(tenant_id=tenant.id, name="Synthetic gallery")
            db.add_all([client, gallery])
            db.flush()
            folder = auth.PhotoFolder(tenant_id=tenant.id, parent_gallery_id=gallery.id, name="Synthetic folder")
            derived = auth.DerivedGallery(tenant_id=tenant.id, parent_gallery_id=gallery.id,
                                          client_id=client.id, name="Synthetic private gallery")
            db.add_all([folder, derived])
            db.flush()
            photo = auth.PhotoAsset(tenant_id=tenant.id, parent_gallery_id=gallery.id,
                                    folder_id=folder.id, filename="synthetic.jpg", storage_key=f"tenant-{i}/synthetic.jpg")
            db.add(photo)
            db.flush()
            gallery.cover_photo_id = photo.id
            order = auth.SaleOrder(tenant_id=tenant.id, derived_gallery_id=derived.id, client_id=client.id,
                                  derived_gallery_id_snapshot=derived.id, derived_gallery_name_snapshot=derived.name,
                                  parent_gallery_id_snapshot=gallery.id, parent_gallery_name_snapshot=gallery.name,
                                  total_cents=1000, checkout_key=f"synthetic-checkout-{i}")
            db.add(order)
            db.flush()
            item = auth.SaleOrderItem(tenant_id=tenant.id, sale_order_id=order.id, photo_asset_id=photo.id,
                                     photo_asset_id_snapshot=photo.id, filename_snapshot="synthetic.jpg", unit_price_cents=1000)
            payment = auth.ProviderPayment(tenant_id=tenant.id, client_id=client.id, checkout_key=f"synthetic-card-{i}",
                                           cart_revision="a" * 64, total_cents=1000, handle_snapshot=f"synthetic-tag-{i}",
                                           configuration_version=1, verification_profile="synthetic",
                                           state="awaiting_payment")
            db.add_all([item, payment])
            db.flush()
            db.add_all([
                auth.CommercialHistoryMedia(tenant_id=tenant.id, sale_order_item_id=item.id, status="ready",
                                            preview_storage_key=f"synthetic-history-{i}.jpg"),
                auth.ProviderPaymentAttempt(tenant_id=tenant.id, client_id=client.id, payment_id=payment.id),
                auth.AuthSession(tenant_id=tenant.id, role="client", subject_id=client.id, client_subject_id=client.id,
                                 token_hash=f"synthetic-client-session-{i}", expires_at=auth.now() + timedelta(days=7)),
                monitor.MonitorGrant(admin_user_id=admin.id, permission="metrics", active=True,
                                     authorization_reference="synthetic-owner-reset"),
            ])
            admins.append(admin)
            tenants.append(tenant)
        owner, tenant = admins[0], tenants[0]
        key = f"tenants/{tenant.id}/branding/owner-logo.png"
        (brand / key).parent.mkdir(parents=True)
        (brand / key).write_bytes(b"official-owner-logo-synthetic")
        other_file = brand / f"tenants/{tenants[1].id}/branding/other-logo.png"
        other_file.parent.mkdir(parents=True)
        other_file.write_bytes(b"other-brand-synthetic")
        db.add_all([
            auth.BrandingSettings(tenant_id=tenant.id, logo_key=key, login_title="Preserved title",
                                  watermark_text="Preserved protection"),
            auth.BrandingSettings(tenant_id=tenants[1].id, logo_key=other_file.relative_to(brand).as_posix()),
            auth.InstallationOperator(admin_user_id=owner.id, active=True, authorization_reference="synthetic-reset",
                                      granted_at=auth.now(), updated_at=auth.now()),
            monitor.PlatformOwner(singleton=1, admin_user_id=owner.id, authorization_reference="synthetic-reset"),
            auth.FacialEmbeddingExperimentSetting(singleton=1, updated_by_admin_id=owner.id, enabled=True),
            auth.GlobalPixSettings(tenant_id=tenant.id, admin_user_id=owner.id, version=3),
            auth.AuditEvent(tenant_id=tenant.id, event="admin_security.synthetic", subject="synthetic-owner-audit"),
            auth.AuditEvent(tenant_id=tenants[1].id, event="admin_security.synthetic", subject="synthetic-other-audit"),
            monitor.MonitorSample(minute=auth.now().replace(second=0, microsecond=0), payload={"synthetic": True}),
        ])
        db.commit()
        yield db, admins, tenants, media, brand, key
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_reset_five_accounts_preserves_owner_settings_credentials_and_brand(graph):
    db, admins, _tenants, media, brand, key = graph
    report = reset.inventory(db, OWNER_EMAIL)
    assert report["delete"]["tenant"] == 4
    assert report["delete"]["admin_user"] == 4
    assert report["delete"]["client"] == 5
    assert report["delete"]["sale_order"] == 5
    assert report["delete"]["sale_order_item"] == report["delete"]["commercial_history_media"] == 5
    assert report["delete"]["provider_payment"] == report["delete"]["provider_payment_attempt"] == 5
    assert report["owner_branding_files"] == 1
    assert OWNER_EMAIL not in str(report)
    result = reset.execute(db, OWNER_EMAIL, reset.CONFIRMATION)
    assert result["owner_state_preserved"]
    assert not any(result["delete"].values())
    assert count(db, auth.AdminUser) == count(db, auth.Tenant) == count(db, auth.TenantAdmin) == 1
    assert count(db, auth.Client) == count(db, auth.SaleOrder) == count(db, auth.ParentGallery) == 0
    assert count(db, auth.ProviderPayment) == count(db, auth.ProviderPaymentAttempt) == 0
    assert count(db, auth.SaleOrderItem) == count(db, auth.CommercialHistoryMedia) == 0
    db.expire_all()
    owner = db.get(auth.AdminUser, admins[0].id)
    assert owner.password_hash == "synthetic-password-0"
    assert owner.totp_secret == "synthetic-totp-0"
    assert db.scalar(select(auth.NotificationSetting.whatsapp_body)) == "synthetic-preference-0"
    assert db.scalar(select(auth.AuthSession.token_hash)) == "synthetic-session-0"
    assert count(db, monitor.MonitorSample) == 1
    assert count(db, monitor.MonitorGrant) == 1
    assert (brand / key).read_bytes() == b"official-owner-logo-synthetic"
    assert not any(any(root.iterdir()) for root in media.values())
    assert result["media"]["branding"]["files"] == 1
    assert reset.execute(db, OWNER_EMAIL, reset.CONFIRMATION)["owner_state_preserved"]


@pytest.mark.parametrize("bad", ["confirmation", "owner", "production", "membership", "schema", "column", "reference", "actual_reference"])
def test_reset_refuses_divergences_before_first_mutation(graph, monkeypatch, bad):
    db, admins, tenants, media, brand, key = graph
    email, confirmation = OWNER_EMAIL, reset.CONFIRMATION
    if bad == "confirmation":
        confirmation = "invalid"
    elif bad == "owner":
        email = admins[1].email
    elif bad == "production":
        monkeypatch.setenv("APP_ENV", "production")
    elif bad == "membership":
        db.add(auth.TenantAdmin(tenant_id=tenants[1].id, admin_user_id=admins[0].id))
        db.commit()
    elif bad == "schema":
        db.execute(text('CREATE TABLE "' + db.connection().get_execution_options()["schema_translate_map"][None]
                             + '".unknown_reset_table (id integer)'))
        db.commit()
    elif bad == "column":
        db.execute(text('ALTER TABLE "' + db.connection().get_execution_options()["schema_translate_map"][None]
                        + '".admin_user ADD COLUMN unknown_reset_column text'))
        db.commit()
    elif bad == "reference":
        db.get(auth.FacialEmbeddingExperimentSetting, 1).updated_by_admin_id = admins[1].id
        db.commit()
    elif bad == "actual_reference":
        schema = db.connection().get_execution_options()["schema_translate_map"][None]
        owner_membership = db.scalar(select(auth.TenantAdmin).where(auth.TenantAdmin.admin_user_id == admins[0].id))
        client_session_id = db.scalar(select(auth.AuthSession.id).where(auth.AuthSession.role == "client"))
        db.add(auth.AdminSecurityChallenge(tenant_id=owner_membership.tenant_id, admin_id=admins[0].id,
                                           session_id=client_session_id, purpose="change_password_otp",
                                           subject_fingerprint="a" * 64, target_fingerprint="b" * 64,
                                           secret_hash="synthetic-secret-hash", expires_at=auth.now() + timedelta(minutes=5)))
        db.flush()
        db.execute(text(f'ALTER TABLE "{schema}".admin_security_challenge '
                        'ADD CONSTRAINT test_actual_session_reference FOREIGN KEY (session_id) '
                        f'REFERENCES "{schema}".auth_session (id)'))
        db.commit()
    with pytest.raises(reset.ResetPolicyError):
        reset.execute(db, email, confirmation)
    db.rollback()
    assert count(db, auth.Client) == count(db, auth.AdminUser) == 5
    assert all((root / "test-acervo.jpg").exists() for root in media.values())
    assert (brand / key).read_bytes() == b"official-owner-logo-synthetic"


def test_failure_after_commit_is_partial_and_retry_preserves_owner(graph, monkeypatch):
    db, admins, _tenants, media, _brand, _key = graph
    actual = reset.clear_root
    phases = []
    def failed(root, preserved=None):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(reset, "clear_root", failed)
    with pytest.raises(OSError):
        reset.execute(db, OWNER_EMAIL, reset.CONFIRMATION, progress=phases.append)
    assert phases == ["database_committed"]
    assert count(db, auth.Client) == 0
    assert all((root / "test-acervo.jpg").exists() for root in media.values())
    monkeypatch.setattr(reset, "clear_root", actual)
    result = reset.execute(db, OWNER_EMAIL, reset.CONFIRMATION)
    assert result["owner_state_preserved"]
    assert db.get(auth.AdminUser, admins[0].id).totp_secret == "synthetic-totp-0"


def test_media_link_is_unlinked_without_following_external_target(graph, tmp_path):
    db, _admins, _tenants, media, _brand, _key = graph
    outside = tmp_path / "outside"
    outside.mkdir()
    external = outside / "must-remain.txt"
    external.write_bytes(b"outside-markina")
    try:
        (media["source"] / "external-link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Host sem permissão para criar symlink; exercitado no CI Linux")
    reset.execute(db, OWNER_EMAIL, reset.CONFIRMATION)
    assert external.read_bytes() == b"outside-markina"


def test_legacy_cleanup_still_refuses_multiple_photographers(graph, monkeypatch):
    db, _admins, _tenants, _media, _brand, _key = graph
    monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: pytest.fail("Não tocar mídia"))
    with pytest.raises(RuntimeError):
        homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
    assert count(db, auth.AdminUser) == count(db, auth.Client) == 5
