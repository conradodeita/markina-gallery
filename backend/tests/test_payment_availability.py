"""Disponibilidade de pagamento restrita ao PIX configurado da própria conta."""

import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import auth, main
from app.auth import Base, GlobalPixSettings, Role
from app.global_pix import normalize_configuration
from app.payment_availability import payment_methods
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie
from tests.test_tenant_configuration import graph as _graph
from tests.test_tenant_configuration import links as _links

graph = _graph
links = _links


@pytest.fixture
def configured(client_db, graph, links):
    for row in graph:
        row["admin"].email_verified = True
        row["admin"].password_hash = auth.password_hasher.hash("Isolated-Configuration-2026!")
        row["parent"].payment_required = True
    client_db.commit()
    for row in graph:
        row["admin_request"] = request(cookie(client_db, row, Role.ADMIN))
    return graph


@pytest.fixture
def client_db(tmp_path):
    url = os.getenv("PAYMENT_TEST_DATABASE_URL", f"sqlite:///{(tmp_path / 'payment.sqlite').as_posix()}")
    engine = create_engine(url, poolclass=NullPool)
    schema = None
    if engine.dialect.name == "postgresql":
        assert (engine.url.host, engine.url.port, engine.url.database) == ("127.0.0.1", 15471, "pyp_payment_test")
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


def sales_input(required=True):
    return main.ParentGallerySalesInput(payment_required=required, pricing_mode="fixed",
        fixed_unit_price_cents=900, sales_message="Proposta nova")


def test_payment_methods_report_only_owned_pix(client_db, configured):
    first, second = configured
    pix(client_db, second)
    assert payment_methods(client_db, tenant_id=first["tenant"].id) == {
        "pix_available": False, "card_available": False, "available": False, "default_method": None,
    }
    pix(client_db, first)
    assert payment_methods(client_db, tenant_id=first["tenant"].id) == {
        "pix_available": True, "card_available": False, "available": True, "default_method": "pix",
    }


def test_paid_sales_without_pix_are_rejected(client_db, configured):
    first = configured[0]
    with pytest.raises(HTTPException) as exc:
        main.update_parent_gallery_sales(first["parent"].id, sales_input(), first["admin_request"], client_db)
    assert exc.value.status_code == 422


def test_paid_sales_accept_pix_and_no_charge_remains_available(client_db, configured):
    first = configured[0]
    pix(client_db, first)
    result = main.update_parent_gallery_sales(first["parent"].id, sales_input(), first["admin_request"], client_db)
    assert result["payment_methods"] == {
        "available": True, "pix_available": True, "card_available": False, "default_method": "pix",
    }
    free = main.update_parent_gallery_sales(first["parent"].id, sales_input(False), first["admin_request"], client_db)
    assert free["payment_required"] is False
