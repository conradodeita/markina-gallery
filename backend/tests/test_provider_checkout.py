"""Reserva de carrinho por conta, usando apenas PostgreSQL e provedor sintético."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import Response
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
    PhotoSelection,
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


def configure(db, tenant_id):
    admin = AdminUser(email=f"synthetic-{uuid4()}@example.test", password_hash="synthetic", totp_secret="synthetic")
    db.add(admin)
    db.flush()
    db.add(TenantAdmin(tenant_id=tenant_id, admin_user_id=admin.id))
    db.flush()
    settings = InfinitePaySettings(tenant_id=tenant_id, admin_user_id=admin.id, handle="synthetic_handle",
        version=4, status="active", verification_profile="synthetic-only", verified_at=now())
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


def test_perfil_de_retorno_e_payment_check_nao_exige_webhook_assinado_ou_recovery():
    owner_id, _, _, revision = setup()

    class ReturnOnlyProvider:
        capabilities = ProviderCapabilities(
            profile="infinitepay-public-v1", operational=True, credit_only=True,
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


def test_rota_cliente_prepara_cartao_por_sessao_e_reutiliza_mesma_tentativa(monkeypatch):
    owner_id, _, _, revision = setup()
    provider = SyntheticPaymentProvider("accepted")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")
    monkeypatch.setattr(main, "operational_provider", lambda **_kwargs: provider)
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        settings = db.scalar(select(InfinitePaySettings))
        settings.verification_profile = "infinitepay-public-v1"
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
        assert visible["card_payment"]["id"] == result["id"]
        assert visible["card_payment"]["checkout_url"] == result["checkout_url"]
