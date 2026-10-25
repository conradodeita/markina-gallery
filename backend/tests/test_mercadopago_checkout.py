"""Contratos públicos Orders e fronteiras de rede simuladas; sem movimentação real."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import (
    Client,
    MercadoPagoAccount,
    MercadoPagoPayment,
    ParentGallery,
    PaymentPreferences,
    PhotoSelection,
    PriceRule,
    Role,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    Tenant,
    create_session,
    engine,
    now,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher
from app.main import app
from app.mercadopago_api import SubmitInput
from app.mercadopago_checkout import (
    apply_order,
    cancel_payment,
    own_payment,
    payment_payload,
    prepare_payment,
    reconcile,
    submit_payment,
)
from app.mercadopago_provider import MercadoPagoError
from app.unified_checkout import cart_payload
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_unified_checkout import isolated_cart_database, setup_cart  # noqa: F401


class Network:
    def __init__(self):
        self.creates = []
        self.cancels = []
        self.resource = None
        self.fail = False
        self.state = "confirmed"
        self.create_status = 201
        self.live_mode = False
        self.minimum_allowed_amount = 0.5

    def request(self, _transport, method, url, **kwargs):
        if method == "GET" and url.endswith("/v1/payment_methods"):
            return {"status": 200, "response": [
                {"id": "visa", "payment_type_id": "credit_card", "status": "active",
                 "min_allowed_amount": self.minimum_allowed_amount},
                {"id": "pix", "payment_type_id": "bank_transfer", "status": "active",
                 "min_allowed_amount": 0.5},
            ]}
        if url.endswith("/v1/orders") and method == "POST":
            data = json.loads(kwargs["data"])
            self.creates.append((deepcopy(data), kwargs["headers"]))
            if self.fail:
                raise MercadoPagoError("timeout")
            state, detail = {
                "confirmed": ("processed", "accredited"), "pending": ("action_required", "waiting_payment"),
                "rejected": ("failed", "rejected_by_issuer"), "processing": ("processing", "processing"),
            }[self.state]
            self.resource = {
                "id": f"ORDSYNTHETIC{len(self.creates)}", "type": "online", "status": state, "status_detail": detail,
                "external_reference": data["external_reference"], "total_amount": data["total_amount"],
                "total_paid_amount": data["total_amount"] if self.state == "confirmed" else "0.00",
                "last_updated_date": now().isoformat(), "live_mode": self.live_mode,
                "transactions": {"payments": [{
                    "id": f"PAYSYNTHETIC{len(self.creates)}", "status": state, "status_detail": detail,
                    "amount": data["total_amount"],
                    "payment_method": {
                        "id": data["transactions"]["payments"][0]["payment_method"]["id"],
                        "type": data["transactions"]["payments"][0]["payment_method"]["type"],
                        "qr_code": "synthetic-pix",
                    },
                }]},
            }
            return {"status": self.create_status, "response": deepcopy(self.resource)}
        if self.fail:
            raise MercadoPagoError("timeout")
        if method == "POST" and url.endswith("/cancel"):
            self.cancels.append(url)
            self.resource["status"], self.resource["status_detail"] = "canceled", "canceled"
            self.resource["transactions"]["payments"][0].update(status="canceled", status_detail="canceled")
            self.resource["last_updated_date"] = now().isoformat()
            return {"status": 200, "response": deepcopy(self.resource)}
        if method == "GET" and url.endswith("/v1/orders"):
            return {"status": 200, "response": {"data": [deepcopy(self.resource)] if self.resource else []}}
        if method == "GET" and self.resource:
            return {"status": 200, "response": deepcopy(self.resource)}
        raise AssertionError(f"Unexpected route: {method} {url}")


@pytest.fixture
def commerce(monkeypatch):
    monkeypatch.setenv("INTEGRATION_SECRET_ENV", "development")
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "test")
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps(
        {"test": base64.b64encode(b"x" * 32).decode()}))
    client_id, other_id, galleries = setup_cart()
    with SessionLocal() as db:
        account_id = uuid4()
        cipher = IntegrationCipher()
        db.add(MercadoPagoAccount(
            id=account_id, tenant_id=FIXTURE_TENANT_ID, seller_id="123456",
            public_key="APP_USR-synthetic-public", test_account=True,
            access_token_envelope=cipher.encrypt(
                "APP_USR-synthetic-token", tenant_id=FIXTURE_TENANT_ID,
                credential_id=account_id).payload(),
            webhook_secret_envelope=cipher.encrypt(
                "synthetic-webhook-secret", tenant_id=FIXTURE_TENANT_ID,
                credential_id=account_id).payload()))
        db.flush()
        db.add(PaymentPreferences(
            tenant_id=FIXTURE_TENANT_ID, account_id=account_id, mercadopago_enabled=True))
        db.commit()
    network = Network()
    monkeypatch.setattr("app.mercadopago_provider.BoundedTransport.request",
                        lambda transport, method, url, **kwargs: network.request(
                            transport, method, url, **kwargs))
    return client_id, other_id, galleries, network


def input_data():
    return SubmitInput(token="single-use-synthetic-token", payment_method_id="visa",
                       email="buyer@testuser.test", identification_number="12345678909")


def prepared(db, client_id, method="credit_card"):
    client = db.get(Client, client_id)
    revision = cart_payload(db, client)["cart_revision"]
    payment = prepare_payment(db, client, revision=revision, key=uuid4(), method=method)
    db.commit()
    return client, payment


def test_cria_snapshot_valor_do_servidor_e_envia_orders_uma_vez(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "confirmed"
        assert len(network.creates) == 1
        body, headers = network.creates[0]
        assert body["total_amount"] == "21.00"
        assert body["type"] == "online" and body["processing_mode"] == "automatic"
        assert body["external_reference"] == str(payment.id)
        assert headers["x-idempotency-key"] == str(payment.id)
        assert "issuer_id" not in body["transactions"]["payments"][0]["payment_method"]
        assert db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.mercadopago_payment_id == payment.id)) == 2
        assert sum(db.scalars(select(SaleOrder.total_cents).where(
            SaleOrder.mercadopago_payment_id == payment.id))) == 2100
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0
        assert db.scalar(select(func.count(SaleOrderItem.id))) == 3
        assert submit_payment(db, client, payment.id, input_data()).id == payment.id
        assert len(network.creates) == 1
        assert "single-use" not in str(payment.__dict__)


def test_prepara_recusa_total_abaixo_de_um_real_sem_alterar_selecao(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        db.query(ParentGallery).filter_by(tenant_id=FIXTURE_TENANT_ID).update(
            {ParentGallery.fixed_unit_price_cents: 33})
        db.query(PriceRule).filter_by(tenant_id=FIXTURE_TENANT_ID).update(
            {PriceRule.unit_price_cents: 33})
        db.commit()
        client = db.get(Client, client_id)
        payload = cart_payload(db, client)
        assert payload["total_cents"] == 99
        with pytest.raises(CheckoutError, match=r"pelo menos R\$ 1,00"):
            prepare_payment(db, client, revision=payload["cart_revision"], key=uuid4(), method="credit_card")
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert db.scalar(select(func.count(SaleOrder.id))) == 0
    assert network.creates == []


def test_total_exatamente_um_real_e_aceito(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        selections = list(db.scalars(select(PhotoSelection).where(
            PhotoSelection.client_id == client_id).order_by(PhotoSelection.id)))
        for selection in selections[1:]:
            db.delete(selection)
        db.query(ParentGallery).filter_by(tenant_id=FIXTURE_TENANT_ID).update(
            {ParentGallery.fixed_unit_price_cents: 100})
        db.query(PriceRule).filter_by(tenant_id=FIXTURE_TENANT_ID).update(
            {PriceRule.unit_price_cents: 100})
        db.commit()
        client, payment = prepared(db, client_id)
        assert payment.total_cents == 100
        result = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert result.state == "confirmed"
        assert network.creates[0][0]["total_amount"] == "1.00"


def test_limite_dinamico_superior_nao_congela_fotos_nem_envia_ordem(commerce):
    client_id, _, _, network = commerce
    network.minimum_allowed_amount = 21.01
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        with pytest.raises(CheckoutError, match=r"R\$ 21,01"):
            submit_payment(db, client, payment.id, input_data())
        db.rollback()
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert db.scalar(select(func.count(SaleOrder.id))) == 0
    assert network.creates == []


def test_piloto_disponibilidade_e_envio_nao_aceitam_outro_cliente(commerce, monkeypatch):
    from app.payment_availability import payment_methods

    client_id, other_id, _, network = commerce
    policy = [{"tenant_id": str(FIXTURE_TENANT_ID), "client_id": str(client_id)}]
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", json.dumps(policy))
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        assert cart_payload(db, client)["mercadopago_available"]
        assert not cart_payload(db, db.get(Client, other_id))["mercadopago_available"]
        assert not payment_methods(db, tenant_id=FIXTURE_TENANT_ID)["card_available"]
        assert payment_methods(db, tenant_id=FIXTURE_TENANT_ID)["pix_available"]
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", "[]")
    with TestClient(app) as browser:
        browser.cookies.set("markina_session", "cart-test")
        assert not browser.get("/library/cart").json()["mercadopago_available"]
        response = browser.post(f"/library/mercadopago/{payment.id}/submit", json={
            "token": "single-use-synthetic-token", "payment_method_id": "visa",
            "email": "buyer@testuser.test", "identification_number": "12345678909"})
        assert response.status_code == 409
        assert browser.post("/library/mercadopago/prepare", json={
            "cart_revision": payment.cart_revision, "idempotency_key": str(uuid4()),
            "method": "credit_card"}).status_code == 409
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "prepared"
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert not list(db.scalars(select(SaleOrder)))
    assert not network.creates
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", json.dumps(policy))
    with SessionLocal() as db:
        assert submit_payment(db, db.get(Client, client_id), payment.id, input_data()).state == "confirmed"
        db.commit()
    assert len(network.creates) == 1


def test_piloto_revogado_nao_bloqueia_conciliacao_ou_cancelamento(commerce, monkeypatch):
    client_id, _, _, network = commerce
    network.state = "pending"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id, method="pix")
        submit_payment(db, client, payment.id, input_data())
        db.commit()
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", "[]")
    with SessionLocal() as db:
        client = db.get(Client, client_id)
        assert not cart_payload(db, client)["mercadopago_available"]
        assert reconcile(db, client, payment.id).state == "pending"
        assert cancel_payment(db, client, payment.id).state == "canceled"
        db.commit()
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
    assert len(network.creates) == 1


def test_recusa_restaura_selecao_e_nova_tentativa(commerce):
    client_id, _, _, network = commerce
    network.state = "rejected"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "rejected" and not payment.active
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert set(db.scalars(select(SaleOrder.payment_status))) == {"cancelled"}
        _, next_payment = prepared(db, client_id)
        assert next_payment.id != payment.id
        assert next_payment.total_cents == payment.total_cents


def test_timeout_bloqueia_reemissao_e_busca_vazia_nao_prova_ausencia(commerce):
    client_id, _, _, network = commerce
    network.fail = True
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "verification_required" and payment.active
        assert prepare_payment(db, client, revision="a" * 64, key=uuid4(),
                               method="pix").id == payment.id
        network.fail = False
        assert reconcile(db, client, payment.id).state == "verification_required"
        assert len(network.creates) == 1


def test_http_402_recupera_order_recusada_por_busca_sem_reenviar(commerce):
    client_id, _, _, network = commerce
    network.state, network.create_status = "rejected", 402
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "verification_required" and payment.provider_order_id is None
        payment = reconcile(db, client, payment.id)
        db.commit()
        assert payment.state == "rejected" and payment.provider_order_id == "ORDSYNTHETIC1"
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert len(network.creates) == 1


def test_pix_cancelamento_confirmado_e_inalterabilidade(commerce):
    client_id, _, _, network = commerce
    network.state = "pending"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id, method="pix")
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "pending" and payment.method == "pix"
        assert payment.pix_copy_paste == "synthetic-pix"
        assert network.creates[0][0]["transactions"]["payments"][0]["payment_method"] == {
            "id": "pix", "type": "bank_transfer"}
        payment = cancel_payment(db, client, payment.id)
        db.commit()
        assert payment.state == "canceled" and not payment.active
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert payment.total_cents == 2100


def test_orders_em_processamento_permanece_bloqueada_sem_tentar_cancelar(commerce):
    client_id, _, _, network = commerce
    network.state = "processing"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        assert payment.state == "processing" and payment.active
        assert payment_payload(db, payment)["can_cancel"] is False

        # A requisição pode chegar depois de a tela ter sido renderizada;
        # o servidor reconcilia primeiro e respeita o estado novo do provedor.
        payment = cancel_payment(db, client, payment.id)
        db.commit()
        assert payment.state == "processing" and payment.active
        assert payment.total_cents == 2100
        assert network.cancels == []


def test_revisao_alterada_recusa_sem_rede_e_abandono_preserva_fotos(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        db.delete(db.scalar(select(PhotoSelection)))
        db.commit()
        with pytest.raises(CheckoutError, match="seleção mudou"):
            submit_payment(db, client, payment.id, input_data())
        db.rollback()
        assert not network.creates
        assert cancel_payment(db, client, payment.id).state == "abandoned"
        db.commit()
        assert db.scalar(select(func.count(PhotoSelection.id))) == 2


def test_atualizacao_atrasada_valor_divergente_e_reembolso(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        pending = deepcopy(network.resource)
        pending.update(status="processing", last_updated_date=(now() + timedelta(seconds=1)).isoformat())
        pending["transactions"]["payments"][0]["status"] = "processing"
        assert not apply_order(db, payment, pending)
        assert payment.state == "confirmed"
        invalid = deepcopy(network.resource)
        invalid["total_amount"] = "0.01"
        assert not apply_order(db, payment, invalid)
        assert payment.state == "confirmed"
        refund = deepcopy(network.resource)
        refund.update(status="refunded", status_detail="refunded",
                      last_updated_date=(now() + timedelta(seconds=2)).isoformat())
        refund["transactions"]["payments"][0].update(status="refunded", status_detail="refunded")
        assert apply_order(db, payment, refund)
        db.commit()
        assert payment.state == "refunded"
        assert payment.confirmed_at
        assert set(db.scalars(select(SaleOrder.payment_status))) == {"cancelled"}
        assert not apply_order(db, payment, network.resource)


def test_http_nao_aceita_preco_tenant_ou_sucesso_do_navegador(commerce):
    client_id, other_id, _, _ = commerce
    with SessionLocal() as db:
        _, payment = prepared(db, client_id)
        with pytest.raises(CheckoutError):
            own_payment(db, payment.id, db.get(Client, other_id))
    with TestClient(app) as browser:
        browser.cookies.set("markina_session", "cart-test")
        response = browser.post(f"/library/mercadopago/{payment.id}/submit", json={
            "email": "buyer@testuser.test", "identification_number": "12345678909",
            "token": "do-not-echo", "total_amount": "0.01", "status": "processed",
            "tenant_id": str(uuid4())})
        assert response.status_code == 422
        assert "do-not-echo" not in response.text
        assert browser.post(f"/library/mercadopago/{payment.id}/cancel",
                            headers={"origin": "https://foreign.test"}).status_code == 403


def test_cliente_de_outro_tenant_nao_consulta_ou_modifica_tentativa(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        _, payment = prepared(db, client_id)
        tenant = Tenant()
        db.add(tenant)
        db.flush()
        foreign = Client(tenant_id=tenant.id, full_name="Outro fotógrafo",
                         phone_e164="+5511999988000")
        db.add(foreign)
        db.flush()
        with pytest.raises(CheckoutError):
            own_payment(db, payment.id, foreign)
        cookie = create_session(db, Response(), Role.CLIENT, foreign.id, tenant_id=tenant.id)
        db.commit()
    with TestClient(app) as browser:
        browser.cookies.set("markina_session", cookie)
        assert browser.get(f"/library/mercadopago/{payment.id}").status_code == 403
        assert browser.post(f"/library/mercadopago/{payment.id}/submit",
                            json=input_data().model_dump(mode="json")).status_code == 403
        assert browser.post(f"/library/mercadopago/{payment.id}/cancel").status_code == 403
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "prepared"
    assert not network.creates


def test_concorrencia_postgresql_prepara_e_envia_uma_unica_cobranca(commerce):
    if engine.dialect.name != "postgresql":
        pytest.skip("Locks de concorrência financeira exigem PostgreSQL.")
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        revision = cart_payload(db, db.get(Client, client_id))["cart_revision"]
    barrier = Barrier(2)
    def prepare_one(_index):
        with SessionLocal() as db:
            client = db.get(Client, client_id)
            barrier.wait(timeout=15)
            payment = prepare_payment(db, client, revision=revision, key=uuid4(), method="credit_card")
            db.commit()
            return payment.id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(prepare_one, range(2)))
    assert ids[0] == ids[1]
    barrier = Barrier(2)
    def submit_one(_index):
        with SessionLocal() as db:
            client = db.get(Client, client_id)
            barrier.wait(timeout=15)
            payment = submit_payment(db, client, ids[0], input_data())
            db.commit()
            return payment.id
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(submit_one, range(2))) == ids
    assert len(network.creates) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count(SaleOrder.id))) == 2
        assert db.get(MercadoPagoPayment, ids[0]).state == "confirmed"
