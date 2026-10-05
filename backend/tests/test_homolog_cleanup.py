from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import homolog_cleanup
from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    AssetFileCleanup,
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Base,
    BrandingSettings,
    Client,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryMembership,
    FolderProcessingSettings,
    GlobalPixSettings,
    NotificationSetting,
    ParentGallery,
    PaymentCommunication,
    PaymentMessageTemplate,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PreviewAdjustmentSettings,
    ProgressivePricingPreset,
    PushSubscription,
    Role,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    Tenant,
    WhatsAppChannelSettings,
    WhatsAppDelivery,
    engine,
)
from app.homolog_cleanup import (
    CONFIRMATION,
    WITHOUT_BACKUP_CONFIRMATION,
    execute,
    inventory,
)
from tests.tenant_fixtures import FIXTURE_TENANT_ID, fixture_admin, fixture_session


@pytest.fixture(autouse=True)
def ensure_isolated_test_schema(legacy_tenant_fixture) -> None:
    Base.metadata.create_all(engine)


def test_inventory_requires_homolog_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="homologação"):
        inventory(db)


def test_inventory_returns_only_counts_without_pii(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "history"))
    monkeypatch.setenv("FACIAL_REFERENCE_ROOT", str(tmp_path / "facial-references"))
    for name in ("source", "derivatives", "history", "facial-references"):
        (tmp_path / name).mkdir()
    with SessionLocal() as db:
        result = inventory(db)
    assert result["environment"] == "homolog"
    assert set(result) == {
        "environment", "photographer_count", "destructive_cleanup",
        "database", "media", "preserved",
    }
    assert result["destructive_cleanup"] == {"status": "single_photographer_only"}
    assert all(type(value) is int for value in result["database"].values())
    assert all(type(value) is int for value in result["preserved"].values())


def test_inventory_aggregates_multiple_photographers_without_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = {name: tmp_path / name for name in homolog_cleanup.EXPECTED_MEDIA_ROOTS}
    for root in roots.values():
        root.mkdir()
    (roots["source"] / "source.jpg").write_bytes(b"source")
    (roots["derivatives"] / "preview.jpg").write_bytes(b"preview")
    monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: roots)
    synthetic = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(synthetic)
    second_tenant_id = uuid4()
    with Session(synthetic) as db:
        db.add(Tenant(id=second_tenant_id, status="active"))
        db.commit()
        result = inventory(db)
    assert result["photographer_count"] == 2
    assert result["destructive_cleanup"] == {
        "status": "unavailable_multiple_photographers"
    }
    assert result["media"]["source"] == {"files": 1, "bytes": 6}
    assert result["media"]["derivatives"] == {"files": 1, "bytes": 7}
    assert all(type(value) is int for value in result["database"].values())
    assert all(type(value) is int for value in result["preserved"].values())
    rendered = str(result)
    assert str(FIXTURE_TENANT_ID) not in rendered
    assert str(second_tenant_id) not in rendered
    synthetic.dispose()


def test_inventory_counts_folder_settings_as_operational_without_exposing_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = {"MEDIA_SOURCE_ROOT": "source", "MEDIA_DERIVATIVES_ROOT": "derivatives",
             "MEDIA_HISTORY_ROOT": "history", "FACIAL_REFERENCE_ROOT": "facial-references"}
    for key, name in roots.items():
        root = tmp_path / name
        root.mkdir()
        monkeypatch.setenv(key, str(root))
    synthetic = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(synthetic)
    with Session(synthetic) as db:
        gallery = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Galeria sintética")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, name="Pasta sintética")
        db.add(folder)
        db.flush()
        settings = FolderProcessingSettings(tenant_id=FIXTURE_TENANT_ID, folder_id=folder.id, preview_mode="custom",
                                            facial_mode="off", preview_exposure_tenths=5)
        db.add(settings)
        db.commit()
        assert db.get(FolderProcessingSettings, folder.id) is not None
        result = inventory(db)
    assert result["database"]["folder_processing_settings"] == 1
    assert "folder_processing_settings" not in result["preserved"]
    assert "custom" not in str(result) and "off" not in str(result)


def test_inventory_aborts_for_unclassified_database_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE unknown_cleanup_data (id integer PRIMARY KEY)"))
    try:
        with SessionLocal() as db, pytest.raises(RuntimeError, match="desconhecidas"):
            inventory(db)
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE unknown_cleanup_data"))


def test_media_inventory_does_not_follow_symlink_targets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = [tmp_path / name for name in ("source", "derivatives", "history", "facial-references")]
    for name, root in zip(("MEDIA_SOURCE_ROOT", "MEDIA_DERIVATIVES_ROOT", "MEDIA_HISTORY_ROOT", "FACIAL_REFERENCE_ROOT"), roots):
        root.mkdir()
        monkeypatch.setenv(name, str(root))
    (roots[0] / "inside.jpg").write_bytes(b"inside")
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"outside-is-larger")
    try:
        (roots[0] / "link.jpg").symlink_to(outside)
    except OSError:
        pass
    with SessionLocal() as db:
        result = inventory(db)
    assert result["media"]["source"] == {"files": 1, "bytes": 6}


def test_media_cleanup_rejects_root_outside_markina_volume(tmp_path: Path) -> None:
    marker = tmp_path / "must-remain.jpg"
    marker.write_bytes(b"preserve")
    with pytest.raises(RuntimeError, match="fora do volume exclusivo"):
        homolog_cleanup._clear_media_root(tmp_path)
    assert marker.read_bytes() == b"preserve"


def test_execute_requires_literal_confirmation_before_database_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "homologation")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="Confirmação literal"):
        execute(db, "invalid")


def test_execute_refuses_multitenant_before_reading_media_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect

    from app.tenancy import TenantContextError

    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setattr(
        homolog_cleanup, "media_roots", lambda: pytest.fail("Não ler raízes de mídia")
    )
    dialect = postgresql_dialect()
    connection = SimpleNamespace(
        get_execution_options=dict,
        dialect=dialect,
    )
    db = MagicMock()
    db.bind = SimpleNamespace(dialect=dialect)
    db.connection.return_value = connection
    db.scalars.return_value = [Tenant(status="active"), Tenant(status="active")]
    with pytest.raises(TenantContextError):
        execute(db, CONFIRMATION)


@pytest.mark.skipif(engine.dialect.name == "postgresql", reason="banco atual é PostgreSQL")
def test_execute_rejects_non_postgresql_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="PostgreSQL exclusivo"):
        execute(db, CONFIRMATION)


@pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="validação destrutiva exige TEST_POSTGRES_DATABASE_URL descartável",
)
def test_execute_on_postgresql_removes_operational_data_and_preserves_admin_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    Base.metadata.create_all(engine)
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = tuple(tmp_path / name for name in ("source", "derivatives", "history", "facial-references"))
    monkeypatch.setattr(homolog_cleanup, "EXPECTED_MEDIA_ROOTS", dict(zip(
        ("source", "derivatives", "history", "facial_references"), roots
    )))
    for name, root in zip(("MEDIA_SOURCE_ROOT", "MEDIA_DERIVATIVES_ROOT", "MEDIA_HISTORY_ROOT", "FACIAL_REFERENCE_ROOT"), roots):
        root.mkdir()
        (root / "test.jpg").write_bytes(b"photo")
        monkeypatch.setenv(name, str(root))
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with SessionLocal() as db:
        admin = fixture_admin(AdminUser(
            email="admin@example.test",
            password_hash="stored-hash",
            email_verified=True,
            totp_secret="TOTP-FACTOR",
        ))
        client = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Cliente teste", phone_e164="+5511999999999")
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Galeria teste")
        db.add_all((admin, client, parent))
        db.flush()
        admin_session = fixture_session(
            token_hash="admin-session",
            role=Role.ADMIN.value,
            subject_id=admin.id,
            expires_at=expires_at,
        )
        admin_challenge = AdminSecurityChallenge(
            purpose="change_password_otp",
            admin_id=admin.id,
            subject_fingerprint="a" * 64,
            secret_hash="challenge-hash",
            expires_at=expires_at,
        )
        client_session = fixture_session(
            token_hash="client-session",
            role=Role.CLIENT.value,
            subject_id=client.id,
            expires_at=expires_at,
        )
        client_challenge = AuthChallenge(
            kind="client_otp",
            subject_fingerprint="b" * 64,
            secret_hash="otp-hash",
            expires_at=expires_at,
        tenant_id=FIXTURE_TENANT_ID)
        branding = BrandingSettings(tenant_id=FIXTURE_TENANT_ID, watermark_text="PREFERÊNCIA PRESERVADA")
        pix = GlobalPixSettings(tenant_id=FIXTURE_TENANT_ID, admin_user_id=admin.id, version=3)
        template = PaymentMessageTemplate(tenant_id=FIXTURE_TENANT_ID, kind="confirmed", body="Mensagem preservada")
        preset = ProgressivePricingPreset(tenant_id=FIXTURE_TENANT_ID, code="TEST", name="Tabela preservada")
        channel = WhatsAppChannelSettings(tenant_id=FIXTURE_TENANT_ID, environment="homolog", status="ready")
        notification = NotificationSetting(tenant_id=FIXTURE_TENANT_ID,
            event_type="first_access", whatsapp_body="Mensagem global",
            push_title="Aviso", push_body="Corpo do aviso",
        )
        adjustment = PreviewAdjustmentSettings(tenant_id=FIXTURE_TENANT_ID, enabled=False)
        admin_push = PushSubscription(tenant_id=FIXTURE_TENANT_ID,
            endpoint_fingerprint="a" * 64, encrypted_subscription="admin-ciphertext",
            role="admin", subject_id=admin.id, admin_subject_id=admin.id,
        )
        client_push = PushSubscription(tenant_id=FIXTURE_TENANT_ID,
            endpoint_fingerprint="b" * 64, encrypted_subscription="client-ciphertext",
            role="client", subject_id=client.id, client_subject_id=client.id,
        )
        db.add_all(
            (
                admin_session,
                admin_challenge,
                client_session,
                client_challenge,
                branding,
                pix,
                template,
                preset,
                channel,
                notification,
                adjustment,
                admin_push,
                client_push,
            )
        )
        folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, name="Pasta teste")
        derived = DerivedGallery(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada teste",
        )
        db.add_all((folder, derived))
        db.flush()
        db.add(FolderProcessingSettings(tenant_id=FIXTURE_TENANT_ID, folder_id=folder.id, preview_mode="custom",
                                        preview_exposure_tenths=5))
        photo = PhotoAsset(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="test.jpg",
            storage_key="test/test.jpg",
        )
        membership = DerivedGalleryMembership(tenant_id=FIXTURE_TENANT_ID,
            derived_gallery_id=derived.id,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )
        db.add_all((photo, membership))
        db.flush()
        selection = PhotoSelection(tenant_id=FIXTURE_TENANT_ID,
            derived_gallery_id=derived.id,
            photo_asset_id=photo.id,
            client_id=client.id,
        )
        order = SaleOrder(tenant_id=FIXTURE_TENANT_ID,
            derived_gallery_id=derived.id,
            client_id=client.id,
            derived_gallery_id_snapshot=derived.id,
            derived_gallery_name_snapshot=derived.name,
            parent_gallery_id_snapshot=parent.id,
            parent_gallery_name_snapshot=parent.name,
            total_cents=1000,
            checkout_key="checkout-test",
        )
        db.add_all((selection, order))
        db.flush()
        item = SaleOrderItem(tenant_id=FIXTURE_TENANT_ID,
            sale_order_id=order.id, photo_asset_id=photo.id,
            filename_snapshot="test.jpg", unit_price_cents=1000,
        )
        db.add(item)
        db.flush()
        db.add_all((
            CommercialHistoryMedia(tenant_id=FIXTURE_TENANT_ID,
                sale_order_item_id=item.id, status="ready",
                preview_storage_key="synthetic/history-preview.jpg",
            ),
            AuditEvent(tenant_id=FIXTURE_TENANT_ID, event="gallery.access", subject=str(client.id)),
            AuditEvent(event="admin_totp.validated", subject=str(admin.id)),
            AssetFileCleanup(tenant_id=FIXTURE_TENANT_ID, paths=["synthetic/test.jpg"]),
        ))
        db.add(
            PaymentCommunication(tenant_id=FIXTURE_TENANT_ID,
                sale_order_id=order.id,
                client_id=client.id,
                idempotency_key="payment-test",
            )
        )
        db.add(
            WhatsAppDelivery(tenant_id=FIXTURE_TENANT_ID,
                kind="payment",
                source_type="sale_order",
                source_id=str(order.id),
                template_kind="confirmed",
                idempotency_key="whatsapp-test",
            )
        )
        db.commit()
        before = inventory(db)
        preserved_before = before["preserved"]
        assert before["database"]["commercial_history_media"] == 1
        assert before["database"]["client_gallery_audit_events"] == 1
        assert before["preserved"]["admin_security_audit_events"] == 1
        assert before["database"]["asset_file_cleanup"] == 1
        assert before["database"]["folder_processing_settings"] == 1
        result = execute(db, WITHOUT_BACKUP_CONFIRMATION)

        assert all(value == 0 for value in result["database"].values())
        assert result["preserved"] == preserved_before
        assert db.scalar(select(AdminUser)).totp_secret == "TOTP-FACTOR"
        assert db.scalar(select(BrandingSettings)).watermark_text == "PREFERÊNCIA PRESERVADA"
        assert db.scalar(select(GlobalPixSettings)).version == 3
        assert db.scalar(select(AuthSession).where(AuthSession.role == Role.ADMIN.value))
        assert not db.scalar(select(AuthSession).where(AuthSession.role == Role.CLIENT.value))
        assert db.scalar(select(PushSubscription).where(PushSubscription.role == "admin"))
        assert not db.scalar(select(PushSubscription).where(PushSubscription.role == "client"))
        assert db.scalar(select(NotificationSetting)).whatsapp_body == "Mensagem global"
        assert db.scalar(select(PreviewAdjustmentSettings)).enabled is False
        repeated = execute(db, WITHOUT_BACKUP_CONFIRMATION)
        assert repeated["database"] == result["database"]
        assert repeated["preserved"] == preserved_before

    assert all(root.is_dir() and not list(root.iterdir()) for root in roots)
