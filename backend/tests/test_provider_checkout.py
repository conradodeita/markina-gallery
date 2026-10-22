"""Reserva de carrinho por conta, usando apenas PostgreSQL e provedor sintético."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from starlette.requests import Request

from app import auth, main
from app.auth import (
    AdminUser,
    Client,
    DerivedGallery,
    GlobalPixSettings,
    InfinitePaySettings,
    ParentGallery,
    PaymentCommunication,
    PaymentGroup,
    PhotoAsset,
    PhotoSelection,
    PriceRule,
    ProviderPayment,
    ProviderPaymentAttempt,
    SaleOrder,
    SaleOrderItem,
    TenantAdmin,
    now,
)
from app.checkout import CheckoutError
from app.payment_provider import CheckoutResult, ProviderCapabilities, SyntheticPaymentProvider
from app.provider_checkout import (
    checkout_request_for,
    issue_provider_payment,
    prepare_provider_payment,
)
from app.unified_checkout import (
    _fingerprint,
    _materials,
    cart_payload,
    finalize_selection,
    prepare_group,
    report_group,
)
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_unified_checkout import SessionLocal as _SessionLocal
from tests.test_unified_checkout import isolated_cart_database as _isolated_cart_database
from tests.test_unified_checkout import setup_cart

SessionLocal = _SessionLocal
isolated_cart_database = _isolated_cart_database


@pytest.fixture(autouse=True)
def synthetic_infinitepay_binding(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INFINITEPAY_TENANT_BINDINGS", json.dumps({str(FIXTURE_TENANT_ID): "CHECKOUT_TEST"}))
    monkeypatch.setenv("INFINITEPAY_BINDING_CHECKOUT_TEST_CREDENTIAL_ENV", "development")
    monkeypatch.setenv("INFINITEPAY_BINDING_CHECKOUT_TEST_API_KEY", "synthetic-checkout-key")


def configure(db, tenant_id):
    admin = AdminUser(email=f"synthetic-{uuid4()}@example.test", password_hash="synthetic", totp_secret="synthetic")
    db.add(admin)
    db.flush()
    db.add(TenantAdmin(tenant_id=tenant_id, admin_user_id=admin.id))
    db.flush()
    settings = InfinitePaySettings(tenant_id=tenant_id, admin_user_id=admin.id, handle="synthetic_handle",
        version=4, status="active", card_enabled=True,
        verification_profile="infinitepay-public-v1", verified_at=now())
    db.add(settings)
    return settings


def setup():
    with SessionLocal() as db:
        if db.get(auth.Tenant, FIXTURE_TENANT_ID) is None:
            db.add(auth.Tenant(id=FIXTURE_TENANT_ID))
            db.commit()
    owner_id, other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        configure(db, owner.tenant_id)
        db.commit()
        revision = _fingerprint([item for item in _materials(db, owner) if item[1].payment_required])
    return owner_id, other_id, gallery_ids, revision


def prepare(db, owner_id, revision, key=None):
    return prepare_provider_payment(db, db.get(Client, owner_id), cart_revision=revision,
                                    checkout_key=key or str(uuid4()))


def set_small_cart_total(db, owner_id, gallery_ids, total):
    """As duas fotos da primeira galeria valem 1 centavo cada."""
    for gallery_id, price in zip(gallery_ids, (1, total - 2), strict=True):
        parent = db.get(ParentGallery, db.get(DerivedGallery, gallery_id).parent_gallery_id)
        parent.fixed_unit_price_cents = price
        for rule in db.scalars(select(PriceRule).where(PriceRule.parent_gallery_id == parent.id)):
            rule.unit_price_cents = price
    db.commit()
    return cart_payload(db, db.get(Client, owner_id))["cart_revision"]


@pytest.mark.parametrize("total", [5, 99])
def test_rota_recusa_cartao_abaixo_de_um_real_sem_reserva_ou_efeito_no_pix(monkeypatch, total):
    owner_id, _, gallery_ids, _ = setup()
    provider_factory = []
    def provider_for(**kwargs):
        provider_factory.append(kwargs)
        return SyntheticPaymentProvider("accepted")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    monkeypatch.setattr(main, "operational_provider", provider_for)
    with SessionLocal() as db:
        revision = set_small_cart_total(db, owner_id, gallery_ids, total)
        owner = db.get(Client, owner_id)
        pix = prepare_group(db, owner)
        db.commit()
        pix_before = (pix.id, pix.state, pix.total_cents)
        selections = set(db.execute(select(PhotoSelection.derived_gallery_id, PhotoSelection.photo_asset_id)))
        orders_before = db.scalar(select(func.count(SaleOrder.id)))
        response = Response()
        auth.create_session(db, response, auth.Role.CLIENT, owner.id, tenant_id=owner.tenant_id)
        cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        request = Request({"type": "http", "method": "POST", "path": "/library/cart/prepare-card",
                           "headers": [(b"cookie", f"markina_session={cookie}".encode())],
                           "client": ("127.0.0.1", 12345)})
        payload = main.ProviderCheckoutInput(cart_revision=revision, idempotency_key=uuid4())
        with pytest.raises(HTTPException) as error:
            main.prepare_unified_card(request, payload, db)
        assert error.value.status_code == 409
        assert "R$ 1,00" in error.value.detail
        assert provider_factory == []
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 0
        assert db.scalar(select(func.count(SaleOrder.id))) == orders_before
        assert set(db.execute(select(PhotoSelection.derived_gallery_id, PhotoSelection.photo_asset_id))) == selections
        db.refresh(pix)
        assert (pix.id, pix.state, pix.total_cents) == pix_before
        assert prepare_group(db, owner).id == pix.id
        assert cart_payload(db, owner)["total_cents"] == total


@pytest.mark.parametrize("total", [100, 101])
def test_total_minimo_aceita_fotos_de_um_centavo(total):
    owner_id, _, gallery_ids, _ = setup()
    with SessionLocal() as db:
        revision = set_small_cart_total(db, owner_id, gallery_ids, total)
        payment = prepare(db, owner_id, revision)
        db.commit()
        request = checkout_request_for(db, payment)
        assert request.total_cents == total
        assert sum(item.price * item.quantity for item in request.items) == total
        assert min(item.price for item in request.items) == 1
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_repeticao_de_tentativa_historica_abaixo_do_minimo_nao_reemite():
    owner_id, _, _, revision = setup()
    key = str(uuid4())
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision, key)
        # Caracteriza registro histórico pré-existente, sem emitir no provedor.
        payment.total_cents = 5
        payment.state = "verification_required"
        db.commit()
        before = (payment.id, payment.state, payment.total_cents)
        assert (prepare(db, owner_id, revision, key).id, payment.state, payment.total_cents) == before
        assert db.scalar(select(func.count(ProviderPayment.id))) == 1
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 1
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_snapshot_neutro_uuid_multi_galeria_e_idempotente():
    owner_id, _, _, revision = setup()
    key = str(uuid4())
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision, key)
        db.commit()
        request = checkout_request_for(db, payment)
        assert request.payment_id == payment.id and request.tenant_id == payment.tenant_id
        assert request.total_cents == payment.total_cents == 2100
        assert sum(item.quantity for item in request.items) == 3
        assert len(request.items) == 1 and request.items[0].price == 700
        assert payment.state == "creating" and payment.configuration_version == 4
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 1
        assert db.scalar(select(func.count(SaleOrder.id)).where(SaleOrder.provider_payment_id == payment.id)) == 2
        assert db.scalar(select(func.count(SaleOrderItem.id)).where(
            SaleOrderItem.sale_order_id.in_(select(SaleOrder.id).where(SaleOrder.provider_payment_id == payment.id)))) == 3
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0
        assert prepare(db, owner_id, revision, key).id == payment.id
        with pytest.raises(CheckoutError):
            prepare(db, owner_id, "stale", key)


def test_config_pendente_ou_revisao_stale_nao_muda_selecao():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        settings = db.scalar(select(InfinitePaySettings))
        settings.status = "pending"
        db.commit()
        before = db.scalar(select(func.count(PhotoSelection.id)))
        with pytest.raises(CheckoutError):
            prepare(db, owner_id, revision)
        db.rollback()
        settings = db.scalar(select(InfinitePaySettings))
        settings.status = "active"
        db.commit()
        with pytest.raises(CheckoutError, match="carrinho mudou"):
            prepare(db, owner_id, "f"*64)
        db.rollback()
        assert db.scalar(select(func.count(PhotoSelection.id))) == before == 3
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0


def test_binding_ausente_recusa_cartao_antes_de_reservar_selecao(monkeypatch):
    owner_id, _, _, revision = setup()
    monkeypatch.delenv("INFINITEPAY_BINDING_CHECKOUT_TEST_API_KEY")
    with SessionLocal() as db:
        before = db.scalar(select(func.count(PhotoSelection.id)))
        with pytest.raises(CheckoutError, match="Cartão indisponível"):
            prepare(db, owner_id, revision)
        db.rollback()
        assert db.scalar(select(func.count(PhotoSelection.id))) == before == 3
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0


def test_pix_sem_configuracao_nao_impede_cartao():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        db.query(GlobalPixSettings).delete()
        db.commit()
        payment = prepare(db, owner_id, revision)
        db.commit()
        assert payment.total_cents == 2100
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 1


def test_carrinho_misto_reserva_apenas_galeria_com_cobranca():
    owner_id, _, gallery_ids, _ = setup()
    with SessionLocal() as db:
        free_gallery = db.get(DerivedGallery, gallery_ids[0])
        db.get(ParentGallery, free_gallery.parent_gallery_id).payment_required = False
        db.commit()
        owner = db.get(Client, owner_id)
        revision = _fingerprint([item for item in _materials(db, owner) if item[1].payment_required])
        payment = prepare(db, owner_id, revision)
        db.commit()
        assert payment.total_cents == 700
        assert db.scalar(select(func.count(PhotoSelection.id)).where(
            PhotoSelection.derived_gallery_id == free_gallery.id)) == 2
        assert db.scalar(select(func.count(PhotoSelection.id))) == 2


def test_prazo_expirado_impede_reserva_sem_efeitos():
    owner_id, _, gallery_ids, revision = setup()
    with SessionLocal() as db:
        db.get(DerivedGallery, gallery_ids[0]).selection_expires_at = now() - timedelta(minutes=1)
        db.commit()
        with pytest.raises(CheckoutError, match="prazo desta galeria expirou"):
            prepare(db, owner_id, revision)
        db.rollback()
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0


def test_rollback_local_remove_snapshot_e_tentativa_em_conjunto():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        prepare(db, owner_id, revision)
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0
        db.rollback()
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 0


def test_pix_comunicado_permanece_fechado_e_nao_e_convertido_para_cartao():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        client = db.get(Client, owner_id)
        group = prepare_group(db, client)
        db.commit()
        communication = report_group(db, client, group.id, group.revision, str(uuid4()))
        db.commit()
        with pytest.raises(CheckoutError):
            prepare(db, owner_id, revision)
        db.rollback()
        assert db.get(PaymentGroup, group.id).state == "reported"
        assert db.get(PaymentCommunication, communication.id) is not None
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_clique_concorrente_com_mesma_chave_produz_uma_reserva():
    if auth.engine.dialect.name != "postgresql":
        pytest.skip("Concorrência do checkout depende dos locks de linha do PostgreSQL")
    owner_id, _, _, revision = setup()
    key = str(uuid4())
    barrier = Barrier(2)

    def prepare_in_session():
        with SessionLocal() as db:
            barrier.wait(timeout=10)
            payment = prepare(db, owner_id, revision, key)
            payment_id = payment.id
            db.commit()
            return payment_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = [future.result(timeout=30) for future in
                         (pool.submit(prepare_in_session), pool.submit(prepare_in_session))]
    assert first == second
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ProviderPayment.id))) == 1
        assert db.scalar(select(func.count(ProviderPaymentAttempt.id))) == 1
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_pix_e_finalizacao_sem_cobranca_nao_emitem_cartao(monkeypatch):
    from app.payment_provider import SyntheticPaymentProvider

    monkeypatch.setattr(SyntheticPaymentProvider, "create_checkout",
                        lambda *_args: pytest.fail("Fluxo PIX/sem cobrança chamou o provedor"))
    owner_id, _, gallery_ids, _ = setup()
    with SessionLocal() as db:
        pix = prepare_group(db, db.get(Client, owner_id))
        db.commit()
        gallery = db.get(DerivedGallery, gallery_ids[0])
        db.get(ParentGallery, gallery.parent_gallery_id).payment_required = False
        db.commit()
        materials = _materials(db, db.get(Client, owner_id))
        entry = next(row for row in materials if row[0].id == gallery.id)
        order = finalize_selection(db, db.get(Client, owner_id), gallery.id,
                                   _fingerprint([entry]), str(uuid4()))
        db.commit()
        assert pix.state == "draft"
        assert order.payment_status == "not_required"
        assert db.scalar(select(func.count(ProviderPayment.id))) == 0


def test_rascunho_pix_local_e_fechado_preservando_snapshot_historico():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        group = prepare_group(db, db.get(Client, owner_id))
        snapshot = group.pix_copy_paste_snapshot
        db.commit()
        payment = prepare(db, owner_id, revision)
        db.commit()
        group = db.get(PaymentGroup, group.id)
        orders = list(db.scalars(select(SaleOrder)))
        assert group.state == "unavailable" and group.pix_copy_paste_snapshot == snapshot
        assert all(order.payment_group_id is None for order in orders)
        assert all(order.provider_payment_id == payment.id for order in orders)
        assert all(order.pix_copy_paste_snapshot is None for order in orders)


@pytest.mark.parametrize("outcome", ["accepted", "refused", "unknown", "transport"])
def test_emissao_somente_uma_vez_e_recuperacao_conservadora(outcome):
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        provider = SyntheticPaymentProvider("unknown" if outcome == "transport" else outcome,
                                            transport_error=outcome == "transport")
        updated = issue_provider_payment(db, payment.id, provider)
        db.refresh(updated)
        state = {"accepted":"awaiting_payment", "refused":"failed_before_issue",
                 "unknown":"verification_required", "transport":"verification_required"}[outcome]
        assert updated.state == state and len(provider.create_calls) == 1
        # Reservas são mantidas em todos os resultados incertos/aceitos; apenas
        # recusa comprovada antes de criar checkout libera a seleção local.
        count = 3 if outcome == "refused" else 0
        assert db.scalar(select(func.count(PhotoSelection.id))) == count
        if outcome == "accepted":
            assert updated.checkout_url.startswith("https://checkout.example.invalid/")
        elif outcome in {"unknown", "transport"}:
            assert updated.checkout_url is None
        if outcome in {"accepted", "unknown", "transport"}:
            with pytest.raises(CheckoutError):
                prepare_group(db, db.get(Client, owner_id))
            db.rollback()
        with pytest.raises(CheckoutError):
            issue_provider_payment(db, updated.id, provider)
        assert len(provider.create_calls) == 1


def test_link_emitido_nao_confirma_pagamento():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("accepted"))
        assert payment.state == "awaiting_payment"
        assert payment.provider_transaction_nsu is None and payment.confirmed_at is None
        assert payment.total_cents == 2100


def test_categoria_http_da_emissao_e_persistida_sem_liberar_reserva(monkeypatch):
    owner_id, _, _, revision = setup()
    provider = SyntheticPaymentProvider("unknown")
    monkeypatch.setattr(provider, "create_checkout", lambda _request: CheckoutResult(
        outcome="unknown", error_category="http_422"))
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        updated = issue_provider_payment(db, payment.id, provider)
        attempt = db.scalar(select(ProviderPaymentAttempt).where(
            ProviderPaymentAttempt.payment_id == payment.id))
        assert updated.state == "verification_required"
        assert attempt.state == "unknown"
        assert attempt.error_category == "http_422"
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


@pytest.mark.parametrize("outcome", ["unknown", "accepted"])
def test_compra_anterior_nao_bloqueia_total_e_meios_de_fotos_novas(outcome):
    owner_id, other_id, gallery_ids, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider(outcome))
        previous = (payment.state, payment.total_cents, payment.revision_number, payment.checkout_url)
        previous_items = set(db.execute(select(SaleOrderItem.sale_order_id, SaleOrderItem.photo_asset_id_snapshot)))
        client = db.get(Client, owner_id)
        assert cart_payload(db, client)["card_payment"]["id"] == str(payment.id)

        gallery = db.get(DerivedGallery, gallery_ids[0])
        example = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == gallery.id))
        new_photo = PhotoAsset(tenant_id=client.tenant_id, parent_gallery_id=gallery.parent_gallery_id,
            derived_gallery_id=gallery.id, folder_id=example.folder_id,
            filename="new-selection.jpg", storage_key=f"synthetic/{uuid4()}.jpg")
        db.add(new_photo)
        db.flush()
        db.add(PhotoSelection(tenant_id=client.tenant_id, client_id=owner_id,
                             derived_gallery_id=gallery.id, photo_asset_id=new_photo.id))
        db.commit()
        cart = cart_payload(db, client)
        assert cart["total_cents"] == 700 and cart["quantity"] == 1
        assert cart["card_available"] and cart["pix_available"] and cart["can_prepare"]
        assert cart["card_payment"] is None
        assert [row["id"] for row in cart["pending_card_payments"]] == [str(payment.id)]
        other = cart_payload(db, db.get(Client, other_id))
        assert other["card_payment"] is None and other["pending_card_payments"] == []

        pix = prepare_group(db, client)
        db.commit()
        assert pix.total_cents == 700
        pix_photos = set(db.scalars(select(SaleOrderItem.photo_asset_id_snapshot).join(
            SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id).where(SaleOrder.payment_group_id == pix.id)))
        assert pix_photos == {new_photo.id}
        next_card = prepare(db, owner_id, cart["cart_revision"])
        db.commit()
        assert next_card.total_cents == 700
        db.refresh(payment)
        assert (payment.state, payment.total_cents, payment.revision_number, payment.checkout_url) == previous
        old_order_ids = select(SaleOrder.id).where(SaleOrder.provider_payment_id == payment.id)
        assert set(db.execute(select(SaleOrderItem.sale_order_id, SaleOrderItem.photo_asset_id_snapshot)
            .where(SaleOrderItem.sale_order_id.in_(old_order_ids)))) == previous_items
        issue_provider_payment(db, next_card.id, SyntheticPaymentProvider("unknown"))
        empty_cart = cart_payload(db, client)
        assert empty_cart["quantity"] == 0
        assert empty_cart["card_payment"]["id"] == str(next_card.id)
        assert [row["id"] for row in empty_cart["pending_card_payments"]] == [str(payment.id)]


def test_foto_reservada_continua_bloqueada_nos_dois_meios():
    owner_id, _, gallery_ids, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("unknown"))
        gallery = db.get(DerivedGallery, gallery_ids[0])
        reserved = db.scalar(select(SaleOrderItem.photo_asset_id_snapshot).join(
            SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id).where(
                SaleOrder.provider_payment_id == payment.id, SaleOrder.derived_gallery_id == gallery.id))
        # Mesmo um cliente que burle a seleção na UI não pode recobrar a foto.
        db.add(PhotoSelection(tenant_id=payment.tenant_id, client_id=owner_id,
                             derived_gallery_id=gallery.id, photo_asset_id=reserved))
        db.commit()
        client = db.get(Client, owner_id)
        cart = cart_payload(db, client)
        assert not cart["can_prepare"]
        assert cart["card_payment"]["id"] == str(payment.id)
        with pytest.raises(CheckoutError, match="congelado"):
            prepare_group(db, client)
        with pytest.raises(CheckoutError, match="congelado"):
            prepare(db, owner_id, revision)
        assert payment.state == "verification_required"


def test_perfil_de_retorno_e_payment_check_nao_exige_webhook_assinado_ou_recovery():
    owner_id, _, _, revision = setup()

    class ReturnOnlyProvider:
        capabilities = ProviderCapabilities(
            profile="infinitepay-public-v1", operational=True, payment_methods=("credit_card", "pix"),
            payment_binding_verified=True, signed_webhook=False, recovery_verified=False,
        )

        def create_checkout(self, _request):
            return CheckoutResult(outcome="accepted", url="https://checkout.infinitepay.io/tag/link")

    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        updated = issue_provider_payment(db, payment.id, ReturnOnlyProvider())
        assert updated.state == "awaiting_payment"
        assert updated.checkout_url == "https://checkout.infinitepay.io/tag/link"


def test_retorno_chama_payment_check_e_confirma_somente_compra_correspondente(monkeypatch):
    class PublicProfileChecker(SyntheticPaymentProvider):
        def check_payment(self, request):
            # O snapshot usa o perfil público autorizado; a fronteira HTTP
            # sintética devolve evidência desse mesmo perfil documentado.
            return super().check_payment(request).model_copy(update={"verification_profile": "infinitepay-public-v1"})

    owner_id, _, _, revision = setup()
    checker = PublicProfileChecker(check_outcome="verified")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    monkeypatch.setattr(main, "operational_provider", lambda **_kwargs: checker)
    request = Request({"type": "http", "method": "GET", "path": "/infinitepay/return",
                       "headers": [], "client": ("127.0.0.1", 12345), "query_string": b""})
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("accepted"))
        response = main.infinitepay_return(
            request, order_nsu=str(payment.id), transaction_nsu="synthetic-transaction",
            slug="synthetic-invoice", db=db,
        )
        db.refresh(payment)
        assert response.status_code == 303
        assert response.headers["location"] == f"/library/purchases#payment-{payment.id}"
        assert len(checker.check_calls) == 1
        assert checker.check_calls[0].payment_id == payment.id
        assert payment.state == "confirmed"
        assert payment.provider_transaction_nsu == "synthetic-transaction"


def test_retorno_sem_order_nsu_canonico_nao_consulta_nem_confirma(monkeypatch):
    owner_id, _, _, revision = setup()
    checker = SyntheticPaymentProvider(check_outcome="verified")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    monkeypatch.setattr(main, "operational_provider", lambda **_kwargs: checker)
    request = Request({"type": "http", "method": "GET", "path": "/infinitepay/return",
                       "headers": [], "client": ("127.0.0.1", 12345), "query_string": b""})
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("accepted"))
        response = main.infinitepay_return(
            request, order_nsu="not-a-uuid", transaction_nsu="synthetic-transaction",
            slug="synthetic-invoice", db=db,
        )
        db.refresh(payment)
        assert response.status_code == 303 and len(checker.check_calls) == 0
        assert payment.state == "awaiting_payment" and payment.provider_transaction_nsu is None


@pytest.mark.parametrize("pix_configured", [True, False])
def test_rota_cliente_prepara_cartao_por_sessao_e_reutiliza_mesma_tentativa(monkeypatch, pix_configured):
    owner_id, _, _, revision = setup()
    provider = SyntheticPaymentProvider("accepted")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    monkeypatch.setattr(main, "operational_provider", lambda **_kwargs: provider)
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        settings = db.scalar(select(InfinitePaySettings))
        settings.verification_profile = "infinitepay-public-v1"
        if not pix_configured:
            db.delete(db.scalar(select(GlobalPixSettings)))
            db.flush()
        response = Response()
        auth.create_session(db, response, auth.Role.CLIENT, owner.id, tenant_id=owner.tenant_id)
        cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        request = Request({"type": "http", "method": "POST", "path": "/library/cart/prepare-card",
                           "headers": [(b"cookie", f"markina_session={cookie}".encode())],
                           "client": ("127.0.0.1", 12345)})
        payload = main.ProviderCheckoutInput(cart_revision=revision, idempotency_key=uuid4())
        result = main.prepare_unified_card(request, payload, db)
        replay = main.prepare_unified_card(request, payload, db)
        assert result["status"] == replay["status"] == "awaiting_payment"
        assert result["id"] == replay["id"]
        assert result["checkout_url"] == replay["checkout_url"]
        assert len(provider.create_calls) == 1
        visible = cart_payload(db, owner)
        assert visible["card_available"] is True
        assert visible["pix_available"] == pix_configured
        assert visible["card_payment"]["id"] == result["id"]
        assert visible["card_payment"]["checkout_url"] == result["checkout_url"]
        settings.card_enabled = False
        db.flush()
        disabled = cart_payload(db, owner)
        assert disabled["card_available"] is False
        assert disabled["card_payment"]["id"] == result["id"]
        assert disabled["card_payment"]["checkout_url"] == result["checkout_url"]
        # A replay of the original key still returns the issued checkout even
        # after the photographer disables new card purchases.
        replay_after_disable = main.prepare_unified_card(request, payload, db)
        assert replay_after_disable["id"] == result["id"]
        assert replay_after_disable["checkout_url"] == result["checkout_url"]
        assert len(provider.create_calls) == 1


def test_perfil_de_cartao_nao_utilizavel_recusa_nova_preparacao():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        db.scalar(select(InfinitePaySettings)).verification_profile = "unverified"
        db.commit()
        with pytest.raises(CheckoutError, match="Cartão indisponível"):
            prepare(db, owner_id, revision)
        assert db.scalar(select(func.count()).select_from(ProviderPayment)) == 0
