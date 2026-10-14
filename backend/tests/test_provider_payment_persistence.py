"""Contrato local de integridade de cartão, sem checkout nem confirmação externa."""

from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.auth import (
    Client,
    PaymentGroup,
    ProviderPayment,
    ProviderPaymentAttempt,
    ProviderPaymentReceipt,
    SaleOrder,
    now,
)
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph

client_db = _client_db
graph = _graph


def payment(db, row, **values):
    data = {"tenant_id": row["tenant"].id, "client_id": row["client"].id, "checkout_key": str(uuid4()),
                "cart_revision": "a" * 64, "total_cents": 1000, "handle_snapshot": "synthetic", "configuration_version": 1,
                "verification_profile": "synthetic-only"}
    result = ProviderPayment(**(data | values))
    db.add(result)
    db.flush()
    return result


@pytest.mark.parametrize("child", [ProviderPaymentAttempt, ProviderPaymentReceipt, SaleOrder])
@pytest.mark.parametrize("foreign", ["tenant", "client"])
def test_filhos_exigem_conta_e_cliente_da_compra(client_db, graph, child, foreign):
    first, second = graph
    parent = payment(client_db, first)
    other_client = second["client"]
    if foreign == "client":
        other_client = Client(tenant_id=first["tenant"].id, full_name="Outra sintética", phone_e164="+5511999990088")
        client_db.add(other_client)
        client_db.flush()
    values = {"tenant_id": second["tenant"].id if foreign == "tenant" else first["tenant"].id,
                  "client_id": other_client.id}
    if child is SaleOrder:
        values.update(provider_payment_id=parent.id, total_cents=1000,
            derived_gallery_id_snapshot=uuid4(), derived_gallery_name_snapshot="Sintética",
            parent_gallery_id_snapshot=uuid4(), parent_gallery_name_snapshot="Sintética")
    else:
        values["payment_id"] = parent.id
    if child is ProviderPaymentReceipt:
        values.update(digest="b"*64, transaction_nsu="synthetic", slug="synthetic", verification_profile="synthetic-only")
    client_db.add(child(**values))
    with pytest.raises(sa.exc.IntegrityError):
        client_db.flush()


def test_transacao_unica_global_e_rollback_atomico(client_db, graph):
    first, second = graph
    payment(client_db, first, provider_transaction_nsu="synthetic-tx", state="confirmed", confirmed_at=now())
    client_db.commit()
    with pytest.raises(sa.exc.IntegrityError):
        payment(client_db, second, provider_transaction_nsu="synthetic-tx", state="confirmed", confirmed_at=now())
    client_db.rollback()
    rows = list(client_db.scalars(sa.select(ProviderPayment)))
    assert len(rows) == 1 and rows[0].tenant_id == first["tenant"].id


def test_uma_tentativa_por_compra_e_recibo_deduplicado(client_db, graph):
    parent = payment(client_db, graph[0])
    owner = {"tenant_id": parent.tenant_id, "client_id": parent.client_id, "payment_id": parent.id}
    client_db.add(ProviderPaymentAttempt(**owner))
    client_db.add(ProviderPaymentReceipt(**owner, digest="c"*64, transaction_nsu="tx", slug="slug",
                                       verification_profile="synthetic-only"))
    client_db.commit()
    for row in (ProviderPaymentAttempt(**owner), ProviderPaymentReceipt(**owner, digest="c"*64,
                transaction_nsu="tx", slug="slug", verification_profile="synthetic-only")):
        with pytest.raises(sa.exc.IntegrityError):
            client_db.add(row)
            client_db.flush()
        client_db.rollback()


def test_snapshot_independente_da_configuracao_e_chave_por_cliente(client_db, graph):
    first, second = graph
    a = payment(client_db, first, checkout_key="same")
    b = payment(client_db, second, checkout_key="same", handle_snapshot="synthetic_b")
    client_db.commit()
    assert a.handle_snapshot == "synthetic" and b.handle_snapshot == "synthetic_b"
    assert a.configuration_version == b.configuration_version == 1
    with pytest.raises(sa.exc.IntegrityError):
        payment(client_db, first, checkout_key="same")


def test_pedido_nao_pode_ter_PIX_e_cartao_simultaneamente(client_db, graph):
    first = graph[0]
    parent = payment(client_db, first)
    pix = PaymentGroup(tenant_id=parent.tenant_id, client_id=parent.client_id, revision="synthetic",
                       total_cents=1000, pix_copy_paste_snapshot="synthetic", pix_configuration_snapshot={})
    client_db.add(pix)
    client_db.flush()
    client_db.add(SaleOrder(tenant_id=parent.tenant_id, client_id=parent.client_id,
        total_cents=1000, provider_payment_id=parent.id, payment_group_id=pix.id,
        derived_gallery_id_snapshot=uuid4(), derived_gallery_name_snapshot="Sintética",
        parent_gallery_id_snapshot=uuid4(), parent_gallery_name_snapshot="Sintética"))
    with pytest.raises(sa.exc.IntegrityError):
        client_db.flush()


@pytest.mark.parametrize("values", [{"total_cents":0}, {"state":"paid"}, {"state":"confirmed"}, {"configuration_version":0}])
def test_valores_e_estados_incoerentes_recusados(client_db, graph, values):
    with pytest.raises(sa.exc.IntegrityError):
        payment(client_db, graph[0], **values)
