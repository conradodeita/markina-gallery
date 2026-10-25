"""Compra, dashboard, CSV e relatório comercial usam a mesma prova financeira."""
# ruff: noqa: F811

import csv
from copy import deepcopy
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.auth import MercadoPagoAccount, MercadoPagoPayment, SaleOrder, SessionLocal, engine
from app.client_lifecycle import deletion_inventory
from app.main import _payment_dashboard_data, app
from app.mercadopago_checkout import apply_order, submit_payment
from app.payment_export import FINANCIAL_HEADERS, HEADERS, payment_orders_csv
from app.statistics_report import commercial_report
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_derived_galleries import authenticate_admin
from tests.test_mercadopago_checkout import commerce, input_data, prepared  # noqa: F401
from tests.test_unified_checkout import isolated_cart_database  # noqa: F401


def dashboard(db, **filters):
    return _payment_dashboard_data(db, tenant_id=FIXTURE_TENANT_ID, **filters)


def test_dashboard_filtros_csv_e_indicadores_do_mesmo_pagamento(commerce):
    client_id, _, _, _ = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        data = dashboard(db, payment_provider="mercadopago", financial_status="confirmed_undelivered")
        assert len(data["groups"]) == 1
        orders = data["groups"][0]["orders"]
        assert len(orders) == 2
        assert {order["payment_provider"] for order in orders} == {"mercadopago"}
        assert {order["mercadopago"]["id"] for order in orders} == {str(payment.id)}
        assert all(order["mercadopago"]["test_account"] for order in orders)
        assert {order["payment_status"] for order in orders} == {"confirmed"}
        assert sum(order["total_cents"] for order in orders) == 2100
        assert not dashboard(db, payment_provider="pix")["groups"]
        assert not dashboard(db, financial_status="refunded")["groups"]
        legacy = list(csv.reader(StringIO(payment_orders_csv(data["groups"]).decode("utf-8-sig")), delimiter=";"))
        assert legacy == [HEADERS]
        detailed = list(csv.reader(StringIO(payment_orders_csv(
            data["groups"], include_financial_details=True).decode("utf-8-sig")), delimiter=";"))
        assert detailed[0] == [*HEADERS, *FINANCIAL_HEADERS]
        assert all(row[6] == "mercadopago" for row in detailed[1:])
        assert all(row[1].startswith("TESTE — ") for row in detailed[1:])
        report = commercial_report(db, tenant_id=FIXTURE_TENANT_ID)
        assert report["revenue_cents"] == 0
        assert report["confirmed_order_count"] == report["sold_photo_count"] == 0
        assert data["summary"]["confirmed_cents"] == data["summary"]["confirmed_orders"] == 0
        assert data["groups"][0]["totals"]["confirmed_cents"] == 0


def test_historico_e_refund_preservam_identidades_e_retiram_entrega(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        original_ids = list(db.scalars(select(SaleOrder.id)))
    with TestClient(app) as browser:
        browser.cookies.set("markina_session", "cart-test")
        response = browser.get("/library/purchases")
        assert response.status_code == 200, response.text
        group = response.json()["mercadopago_payment_groups"][0]
        assert group["test_account"] is True
        assert group["id"] == str(payment.id) and len(group["orders"]) == 2
        assert not response.json()["orders"]
        with SessionLocal() as db:
            order = db.scalar(select(SaleOrder))
            order.delivery_album_url = "https://photos.app.goo.gl/fixture"
            refund = deepcopy(network.resource)
            refund.update(status="refunded", status_detail="refunded")
            refund["transactions"]["payments"][0].update(status="refunded", status_detail="refunded")
            assert apply_order(db, db.get(type(payment), payment.id), refund)
            db.commit()
            assert list(db.scalars(select(SaleOrder.id))) == original_ids
            data = dashboard(db, financial_status="refunded")
            assert len(data["groups"][0]["orders"]) == 2
            assert commercial_report(db, tenant_id=FIXTURE_TENANT_ID)["revenue_cents"] == 0
        group = browser.get("/library/purchases").json()["mercadopago_payment_groups"][0]
        assert group["state"] == "refunded"
        assert all(not order["delivery_album_url"] for order in group["orders"])
        authenticate_admin(browser)
        response = browser.get("/admin/payment-communications", params={
            "payment_provider": "mercadopago", "financial_status": "refunded"})
        assert response.status_code == 200, response.text
        assert len(response.json()["groups"][0]["orders"]) == 2


def test_conta_real_simulada_preserva_receita_e_csv_padrao(commerce, monkeypatch):
    """Rede sintética; não usa conta real ou credenciais externas."""
    client_id, _, _, network = commerce
    monkeypatch.setenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS", "true")
    network.live_mode = True
    with SessionLocal() as db:
        db.scalar(select(MercadoPagoAccount)).test_account = False
        db.commit()
        client, payment = prepared(db, client_id)
        assert submit_payment(db, client, payment.id, input_data()).state == "confirmed"
        db.commit()
        data = dashboard(db, payment_provider="mercadopago")
        assert data["summary"]["confirmed_cents"] == 2100
        assert data["summary"]["confirmed_orders"] == 2
        assert not any(order["mercadopago"]["test_account"] for order in data["groups"][0]["orders"])
        assert commercial_report(db, tenant_id=FIXTURE_TENANT_ID)["revenue_cents"] == 2100
        rows = list(csv.reader(StringIO(payment_orders_csv(data["groups"]).decode("utf-8-sig")), delimiter=";"))
        assert len(rows) == 3 and all(len(row) == 4 for row in rows)
        assert all("TESTE" not in row[1] for row in rows[1:])


def test_inventario_da_cliente_protege_tentativa_preparada_sem_pedido(commerce):
    client_id, _, _, _ = commerce
    with SessionLocal() as db:
        client, _payment = prepared(db, client_id)
        inventory = deletion_inventory(db, client, tenant_id=FIXTURE_TENANT_ID)
        assert inventory["commercial_protected"]["mercadopago_payments"] == 1
        assert inventory["commercial_protected"]["orders"] == 0
        assert not inventory["can_delete"]


def test_reset_homolog_recusa_evidencia_financeira_antes_de_apagar(commerce, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Guarda transacional de reset exige PostgreSQL isolado.")
    from app import homolog_cleanup
    from app.homolog_cleanup import CONFIRMATION, execute

    client_id, _, _, _ = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        monkeypatch.setenv("APP_ENV", "homolog")
        connection = db.connection()
        schema = connection.get_execution_options()["schema_translate_map"][None]
        quoted = connection.dialect.identifier_preparer.quote_schema(schema)
        db.execute(text(f"SET LOCAL search_path TO {quoted}"))
        # A inspeção operacional recebe a conexão do schema privado, não outro checkout do pool.
        monkeypatch.setattr(homolog_cleanup, "inspect", lambda _bind: inspect(connection))
        with pytest.raises(RuntimeError, match="evidências financeiras Mercado Pago"):
            execute(db, CONFIRMATION)
        db.rollback()
        assert db.get(MercadoPagoPayment, payment.id).state == "confirmed"
        assert len(list(db.scalars(select(SaleOrder)))) == 2
