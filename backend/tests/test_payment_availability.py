"""Contratos da jornada paga e meios da própria conta; somente dados sintéticos."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import main
from app.auth import Base, GlobalPixSettings, InfinitePaySettings, MediaDerivative, now
from app.global_pix import normalize_configuration
from app.payment_availability import payment_methods
from tests.test_tenant_configuration import configured as _configured
from tests.test_tenant_configuration import graph as _graph
from tests.test_tenant_configuration import links as _links

configured = _configured
graph = _graph
links = _links


@pytest.fixture
def client_db(tmp_path):
    url = os.getenv("PAYMENT_TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'payment.sqlite'}")
    engine = create_engine(url, poolclass=NullPool)
    schema = None
    if engine.dialect.name == "postgresql":
        assert (engine.url.host, engine.url.port, engine.url.database) == (
            "127.0.0.1", 15471, "pyp_payment_test",
        )
        schema = f"payment_availability_{uuid4().hex}"
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = engine.execution_options(schema_translate_map={None: schema})
    else:
        @event.listens_for(engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            yield db
    finally:
        if schema:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def pix(db, row):
    settings = GlobalPixSettings(tenant_id=row["tenant"].id, admin_user_id=row["admin"].id,
        version=1, **normalize_configuration({"copy_paste": "payment@example.test",
            "receiver_name": "SYNTHETIC", "receiver_city": "SAO PAULO"}))
    db.add(settings)
    db.commit()
    return settings


def card(db, row):
    settings = InfinitePaySettings(tenant_id=row["tenant"].id, admin_user_id=row["admin"].id,
        handle="synthetic_receiver", version=1, status="active", card_enabled=True,
        verification_profile="infinitepay-public-v1", verified_at=now())
    db.add(settings)
    db.commit()
    return settings


def sales_input(required=True):
    return main.ParentGallerySalesInput(payment_required=required, pricing_mode="fixed",
        fixed_unit_price_cents=900, sales_message="Proposta nova")


@pytest.mark.parametrize("method", [None, "pix", "card", "both", "invalid_pix", "inactive_card"])
def test_payment_methods_are_usable_and_owned(client_db, configured, method):
    first, second = configured
    pix(client_db, second)
    card(client_db, second)
    if method in {"pix", "both", "invalid_pix"}:
        settings = pix(client_db, first)
        if method == "invalid_pix":
            settings.copy_paste = "invalid"
    if method in {"card", "both", "inactive_card"}:
        settings = card(client_db, first)
        if method == "inactive_card":
            settings.card_enabled = False
    client_db.commit()
    result = payment_methods(client_db, tenant_id=first["tenant"].id)
    assert result == {
        "pix_available": method in {"pix", "both"},
        "card_available": method in {"card", "both"},
        "available": method in {"pix", "card", "both"},
        "default_method": "pix" if method in {"pix", "both"} else "card" if method == "card" else None,
    }


@pytest.mark.parametrize("foreign_method", [None, "pix", "card"])
def test_paid_sales_without_own_method_rejected_atomically(client_db, configured, foreign_method):
    first, second = configured
    if foreign_method:
        {"pix": pix, "card": card}[foreign_method](client_db, second)
    previous = (first["parent"].fixed_unit_price_cents, first["parent"].sales_message)
    with pytest.raises(HTTPException) as exc:
        main.update_parent_gallery_sales(first["parent"].id, sales_input(),
            first["admin_request"], client_db)
    assert exc.value.status_code == 422
    client_db.rollback()
    assert (first["parent"].fixed_unit_price_cents, first["parent"].sales_message) == previous


@pytest.mark.parametrize("method", ["pix", "card"])
def test_paid_sales_accepts_one_usable_own_method(client_db, configured, method):
    first = configured[0]
    {"pix": pix, "card": card}[method](client_db, first)
    result = main.update_parent_gallery_sales(first["parent"].id, sales_input(),
        first["admin_request"], client_db)
    assert result["payment_required"] is True
    assert result["payment_methods"] == {
        "available": True, "pix_available": method == "pix", "card_available": method == "card",
        "default_method": method,
    }
    assert first["parent"].fixed_unit_price_cents == 900


def test_no_charge_sales_does_not_require_payment_configuration(client_db, configured):
    first = configured[0]
    result = main.update_parent_gallery_sales(first["parent"].id, sales_input(False),
        first["admin_request"], client_db)
    assert result["payment_required"] is False
    assert result["payment_methods"]["available"] is False
    assert client_db.scalar(select(GlobalPixSettings)) is None
    assert client_db.scalar(select(InfinitePaySettings)) is None


def test_draft_creation_does_not_require_receiving(client_db, configured, monkeypatch):
    from app.auth import ParentGallery

    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    first = configured[0]
    created = main.create_parent_gallery(main.ParentGalleryInput(name="Rascunho sintético"),
        first["admin_request"], client_db)
    from uuid import UUID

    assert client_db.get(ParentGallery, UUID(created["id"])).payment_required is True
    assert not payment_methods(client_db, tenant_id=first["tenant"].id)["available"]


def test_zero_price_still_rejected_when_receiving_is_valid(client_db, configured):
    first = configured[0]
    pix(client_db, first)
    with pytest.raises(HTTPException) as exc:
        main.update_parent_gallery_sales(first["parent"].id,
            sales_input().model_copy(update={"fixed_unit_price_cents": 0}),
            first["admin_request"], client_db)
    assert exc.value.status_code == 422 and "maior que zero" in exc.value.detail
    client_db.rollback()
    assert first["parent"].fixed_unit_price_cents is None


@pytest.mark.parametrize("route", ["publish", "release", "publish_ready"])
def test_paid_publication_requires_own_payment_method(client_db, configured, route):
    first = configured[0]
    first["folder"].status = "preparing"
    first["photo"].available = False
    client_db.add(MediaDerivative(tenant_id=first["tenant"].id,
        photo_asset_id=first["photo"].id, variant="client_preview", status="ready"))
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        if route == "publish_ready":
            main.publish_parent_gallery_ready_photos(first["parent"].id,
                first["admin_request"], client_db)
        else:
            operation, payload = (main.publish_photo_folder, main.PhotoFolderPublishInput()) if route == "publish" else (
                main.release_photo_folder, main.PhotoFolderReleaseInput())
            operation(first["folder"].id, payload, first["admin_request"], client_db)
    assert exc.value.status_code == 409
    client_db.rollback()
    assert first["photo"].available is False
    assert first["folder"].status == "preparing"


@pytest.mark.parametrize("method", ["pix", "card", "no_charge"])
def test_publication_accepts_valid_journey(client_db, configured, method):
    first = configured[0]
    if method == "no_charge":
        first["parent"].payment_required = False
    else:
        {"pix": pix, "card": card}[method](client_db, first)
    first["folder"].status = "preparing"
    first["photo"].available = False
    client_db.add(MediaDerivative(tenant_id=first["tenant"].id,
        photo_asset_id=first["photo"].id, variant="client_preview", status="ready"))
    client_db.commit()
    result = main.publish_photo_folder(first["folder"].id, main.PhotoFolderPublishInput(),
        first["admin_request"], client_db)
    assert result["published_count"] == 1
    assert first["photo"].available and first["folder"].status == "released"


@pytest.mark.parametrize("payable", [False, True])
def test_media_completes_derivatives_but_only_publishes_payable_journey(
    client_db, configured, tmp_path, monkeypatch, payable,
):
    from PIL import Image

    from app.auth import FacialJob, MediaJob
    from app.facial import indexing
    from app.media import generate_derivatives
    from tests.test_facial_indexing import _settings

    first = configured[0]
    first["folder"].status = "preparing"
    first["photo"].available = True  # O default legado não pode contornar a guarda da publicação.
    first["photo"].storage_key = f"tenants/{first['tenant'].id}/source/synthetic.jpg"
    if payable:
        pix(client_db, first)
    client_db.commit()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setattr(indexing, "facial_settings_from_environment", lambda **_: _settings(tmp_path))
    source = tmp_path / "source" / first["photo"].storage_key
    source.parent.mkdir(parents=True)
    Image.new("RGB", (64, 32), "blue").save(source)
    derivatives = generate_derivatives(client_db, first["photo"])
    assert all(item.status == "ready" for item in derivatives)
    assert client_db.scalar(select(MediaJob.status).where(
        MediaJob.photo_asset_id == first["photo"].id)) == "completed"
    assert first["photo"].available == payable
    assert first["folder"].status == ("released" if payable else "preparing")
    if not payable:
        assert client_db.scalar(select(FacialJob.id).where(
            FacialJob.photo_asset_id == first["photo"].id)) is None
        pix(client_db, first)
        main.publish_photo_folder(first["folder"].id, main.PhotoFolderPublishInput(),
            first["admin_request"], client_db)
    jobs = list(client_db.scalars(select(FacialJob).where(
        FacialJob.photo_asset_id == first["photo"].id, FacialJob.kind == "index",
    )))
    assert len(jobs) == 1 and jobs[0].status == "queued"
    main.publish_photo_folder(first["folder"].id, main.PhotoFolderPublishInput(),
        first["admin_request"], client_db)
    assert len(list(client_db.scalars(select(FacialJob).where(
        FacialJob.photo_asset_id == first["photo"].id, FacialJob.kind == "index",
    )))) == 1


@pytest.mark.parametrize("action", ["disable", "remove", "change_tag"])
def test_infinitepay_cannot_remove_last_method_of_published_paid_gallery(
    client_db, configured, monkeypatch, action,
):
    from app import admin_account
    from tests.test_tenant_infinitepay_configuration import confirm, issue

    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")
    first, second = configured
    settings = card(client_db, first)
    other = card(client_db, second)
    first["folder"].status = "released"
    client_db.commit()
    challenge = issue(client_db, first, handle=None if action == "remove" else
        "changed_tag" if action == "change_tag" else settings.handle,
        version=1, checkout_ready=action == "disable", card_enabled=False)
    with pytest.raises(HTTPException) as exc:
        confirm(client_db, first, challenge)
    assert exc.value.status_code == 409
    client_db.refresh(settings)
    assert (settings.status, settings.card_enabled, settings.handle, settings.version) == (
        "active", True, "synthetic_receiver", 1,
    )
    assert other.card_enabled and other.version == 1
    assert challenge.used_at is None


@pytest.mark.parametrize("coverage", ["pix", "no_charge", "draft"])
def test_infinitepay_can_disable_card_when_paid_journey_stays_covered(
    client_db, configured, monkeypatch, coverage,
):
    from app import admin_account
    from tests.test_tenant_infinitepay_configuration import confirm, issue

    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")
    first = configured[0]
    card(client_db, first)
    first["folder"].status = "preparing" if coverage == "draft" else "released"
    if coverage == "no_charge":
        first["parent"].payment_required = False
    if coverage == "pix":
        pix(client_db, first)
    client_db.commit()
    challenge = issue(client_db, first, handle="synthetic_receiver", version=1,
        checkout_ready=True, card_enabled=False)
    result = confirm(client_db, first, challenge)
    assert result["card_enabled"] is False and result["version"] == 2
    assert result["handle"] == "synthetic_receiver"


@pytest.mark.parametrize("method", [None, "pix", "card", "no_charge"])
def test_reactivating_released_gallery_requires_covered_paid_journey(client_db, configured, method):
    first = configured[0]
    first["parent"].active = False
    first["folder"].status = "released"
    if method == "no_charge":
        first["parent"].payment_required = False
    elif method:
        {"pix": pix, "card": card}[method](client_db, first)
    client_db.commit()
    args = (first["parent"].id, main.ParentGallerySettingsInput(active=True),
        first["admin_request"], client_db)
    if method is None:
        with pytest.raises(HTTPException) as exc:
            main.update_parent_gallery_settings(*args)
        assert exc.value.status_code == 409
        assert first["parent"].active is False
    else:
        main.update_parent_gallery_settings(*args)
        assert first["parent"].active is True


@pytest.mark.parametrize("first_action", ["publish", "disable"])
def test_concurrent_publication_and_last_method_change_keep_paid_gallery_covered(
    client_db, configured, first_action,
):
    from app.auth import PhotoAsset, PhotoFolder
    from app.infinitepay_settings import (
        ConfigurationConflict,
        ReceiverInput,
        apply_proposal,
        canonical_proposal,
    )

    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("A serialização de recebimento exige PostgreSQL descartável.")
    first = configured[0]
    settings = card(client_db, first)
    first["folder"].status = "preparing"
    first["photo"].available = False
    client_db.add(MediaDerivative(tenant_id=first["tenant"].id,
        photo_asset_id=first["photo"].id, variant="client_preview", status="ready"))
    client_db.commit()
    tenant_id, admin_id = first["tenant"].id, first["admin"].id
    folder_id, photo_id = first["folder"].id, first["photo"].id
    target = canonical_proposal(ReceiverInput(handle=settings.handle), 1, True, False)
    connected = Event()
    contender_pid = []

    def publish(db):
        return main._publish_photo_folder(db, db.get(PhotoFolder, folder_id), commit=False)

    def disable(db):
        return apply_proposal(db, tenant_id=tenant_id, admin_id=admin_id, target=target)

    def contender():
        with Session(client_db.bind) as db:
            contender_pid.append(db.scalar(text("SELECT pg_backend_pid()")))
            connected.set()
            try:
                (disable if first_action == "publish" else publish)(db)
                db.commit()
                return "accepted"
            except (ConfigurationConflict, HTTPException):
                db.rollback()
                return "rejected"

    with Session(client_db.bind) as leader, ThreadPoolExecutor(max_workers=1) as pool:
        (publish if first_action == "publish" else disable)(leader)
        future = pool.submit(contender)
        try:
            assert connected.wait(5)
            deadline = monotonic() + 5
            blocked = False
            while monotonic() < deadline:
                with client_db.bind.connect() as observer:
                    blocked = observer.scalar(text(
                        "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"
                    ), {"pid": contender_pid[0]})
                if blocked:
                    break
                sleep(0.05)
            assert blocked and not future.done(), "A operação concorrente deve aguardar a transação anterior."
        finally:
            leader.commit()
        assert future.result(timeout=10) == "rejected"
    client_db.expire_all()
    assert client_db.get(PhotoAsset, photo_id).available == (first_action == "publish")
    assert client_db.get(PhotoFolder, folder_id).status == (
        "released" if first_action == "publish" else "preparing"
    )
    assert client_db.get(InfinitePaySettings, settings.id).card_enabled == (first_action == "publish")
