from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app import homolog_cleanup
from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    AuthChallenge,
    AuthSession,
    Base,
    BrandingSettings,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    GlobalPixSettings,
    ParentGallery,
    PaymentCommunication,
    PaymentMessageTemplate,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    ProgressivePricingPreset,
    Role,
    SaleOrder,
    SessionLocal,
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


@pytest.fixture(autouse=True)
def ensure_postgresql_test_schema() -> None:
    if engine.dialect.name == "postgresql":
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
    for name in ("source", "derivatives", "history"):
        (tmp_path / name).mkdir()
    with SessionLocal() as db:
        result = inventory(db)
    assert result["environment"] == "homolog"
    assert set(result) == {"environment", "database", "media", "preserved"}
    assert "phone" not in str(result).lower()


def test_media_inventory_does_not_follow_symlink_targets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = [tmp_path / name for name in ("source", "derivatives", "history")]
    for name, root in zip(("MEDIA_SOURCE_ROOT", "MEDIA_DERIVATIVES_ROOT", "MEDIA_HISTORY_ROOT"), roots):
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
    roots = tuple(tmp_path / name for name in ("source", "derivatives", "history"))
    for name, root in zip(("MEDIA_SOURCE_ROOT", "MEDIA_DERIVATIVES_ROOT", "MEDIA_HISTORY_ROOT"), roots):
        root.mkdir()
        (root / "test.jpg").write_bytes(b"photo")
        monkeypatch.setenv(name, str(root))
    cleared_roots: list[Path] = []
    monkeypatch.setattr(homolog_cleanup, "_clear_media_root", cleared_roots.append)

    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with SessionLocal() as db:
        admin = AdminUser(
            email="admin@example.test",
            password_hash="stored-hash",
            email_verified=True,
            totp_secret="TOTP-FACTOR",
        )
        client = Client(full_name="Cliente teste", phone_e164="+5511999999999")
        parent = ParentGallery(name="Galeria teste")
        db.add_all((admin, client, parent))
        db.flush()
        admin_session = AuthSession(
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
        client_session = AuthSession(
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
        )
        branding = BrandingSettings(watermark_text="PREFERÊNCIA PRESERVADA")
        pix = GlobalPixSettings(admin_user_id=admin.id, version=3)
        template = PaymentMessageTemplate(kind="confirmed", body="Mensagem preservada")
        preset = ProgressivePricingPreset(code="TEST", name="Tabela preservada")
        channel = WhatsAppChannelSettings(environment="homolog", status="ready")
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
            )
        )
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Pasta teste")
        derived = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada teste",
        )
        db.add_all((folder, derived))
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="test.jpg",
            storage_key="test/test.jpg",
        )
        membership = DerivedGalleryMembership(
            derived_gallery_id=derived.id,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )
        db.add_all((photo, membership))
        db.flush()
        selection = PhotoSelection(
            derived_gallery_id=derived.id,
            photo_asset_id=photo.id,
            client_id=client.id,
        )
        order = SaleOrder(
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
        db.add(
            PaymentCommunication(
                sale_order_id=order.id,
                client_id=client.id,
                idempotency_key="payment-test",
            )
        )
        db.add(
            WhatsAppDelivery(
                kind="payment",
                source_type="sale_order",
                source_id=str(order.id),
                template_kind="confirmed",
                idempotency_key="whatsapp-test",
            )
        )
        db.commit()
        preserved_before = inventory(db)["preserved"]
        result = execute(db, WITHOUT_BACKUP_CONFIRMATION)

        assert all(value == 0 for value in result["database"].values())
        assert result["preserved"] == preserved_before
        assert db.scalar(select(AdminUser)).totp_secret == "TOTP-FACTOR"
        assert db.scalar(select(BrandingSettings)).watermark_text == "PREFERÊNCIA PRESERVADA"
        assert db.scalar(select(GlobalPixSettings)).version == 3
        assert db.scalar(select(AuthSession).where(AuthSession.role == Role.ADMIN.value))
        assert not db.scalar(select(AuthSession).where(AuthSession.role == Role.CLIENT.value))

    assert cleared_roots == list(roots)
