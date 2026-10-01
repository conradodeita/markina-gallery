"""Comércio A/B no PostgreSQL sintético, sem pagamento, transporte ou álbum real."""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import main, unified_checkout
from app.auth import (
    GlobalPixSettings,
    MediaDerivative,
    NotificationDelivery,
    NotificationEvent,
    PaymentCommunication,
    PaymentGroup,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PriceRule,
    Role,
    SaleOrder,
    SaleOrderItem,
)
from app.checkout import CheckoutError, _checkout_material, _synchronize_order
from app.global_pix import normalize_configuration
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = _client_db
graph = _graph
links = _links


@pytest.fixture
def commerce(client_db, graph, links):
    for index, row in enumerate(graph):
        row["admin"].email_verified = True
        row["parent"].favorites_enabled = True
        row["parent"].comments_enabled = True
        folder = PhotoFolder(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            derived_gallery_id=row["gallery"].id, name="Privada sintética", status="released")
        client_db.add(folder)
        client_db.flush()
        row["photo"].folder_id = folder.id
        row["photo"].derived_gallery_id = row["gallery"].id
        row["folder"] = folder
        config = normalize_configuration({"copy_paste": f"synthetic-{index}@example.test",
            "receiver_name": f"SINTETICO {index}", "receiver_city": "SAO PAULO"})
        pix = GlobalPixSettings(tenant_id=row["tenant"].id,
            admin_user_id=row["admin"].id, version=index+1, **config)
        client_db.add_all([pix, PriceRule(tenant_id=row["tenant"].id,
            parent_gallery_id=row["parent"].id, minimum_quantity=1,
            maximum_quantity=None, unit_price_cents=700 + index*100)])
        row["pix"] = pix
    client_db.commit()
    for row in graph:
        row["customer_request"] = request(cookie(client_db, row, Role.CLIENT))
        row["admin_request"] = request(cookie(client_db, row, Role.ADMIN))
    return graph


def selected(db, row):
    main.select_photo(row["gallery"].id, row["photo"].id, row["customer_request"], db)


def reported(db, row):
    selected(db, row)
    group = unified_checkout.prepare_group(db, row["client"])
    db.commit()
    communication = unified_checkout.report_group(db, row["client"], group.id,
                                                   group.revision, "same-key")
    db.commit()
    order = db.scalar(select(SaleOrder).where(SaleOrder.payment_group_id == group.id))
    row.update(group=group, communication=communication, purchase=order)
    return communication


def payments(db, row):
    return main.list_payment_communications(row["admin_request"], query=None,
        parent_gallery_id=None, financial_status=None, delivery_status=None,
        created_from=None, created_to=None, cursor=None, limit=20, db=db)


def test_mesmo_telefone_compras_pix_destinatarios_e_historico_independentes(client_db, commerce):
    first, second = commerce
    assert first["client"].phone_e164 == second["client"].phone_e164
    for row in commerce:
        reported(client_db, row)
        assert row["group"].pix_copy_paste_snapshot == row["pix"].copy_paste
        assert row["purchase"].pix_configuration_snapshot["configuration_id"] == str(row["pix"].id)
        assert row["purchase"].tenant_id == row["tenant"].id
        item = client_db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == row["purchase"].id))
        assert item.tenant_id == row["tenant"].id and item.photo_asset_id == row["photo"].id
        event = client_db.scalar(select(NotificationEvent).where(
            NotificationEvent.sale_order_id == row["purchase"].id,
            NotificationEvent.event_type == "payment_reported"))
        recipients = list(client_db.scalars(select(NotificationDelivery.recipient_id).where(
            NotificationDelivery.event_id == event.id)))
        assert recipients == [row["admin"].id]
        history = main.client_purchase_history(row["customer_request"], client_db)
        assert [order["id"] for group in history["payment_groups"] for order in group["orders"]] == [str(row["purchase"].id)]
        assert str(row["communication"].id) in str(payments(client_db, row))
    assert first["group"].total_cents == 700 and second["group"].total_cents == 800
    main.decide_payment_communication(first["communication"].id,
        main.PaymentDecisionInput(decision="confirmed", payment_group_id=first["group"].id),
        first["admin_request"], client_db)
    assert first["purchase"].payment_status == "confirmed"
    assert second["purchase"].payment_status == "pending"
    result = main.update_order_delivery(first["purchase"].id,
        main.OrderDeliveryInput(album_url="https://photos.app.goo.gl/syntheticA", version=0),
        first["admin_request"], client_db)
    assert result["delivery"]["album_url"].endswith("syntheticA")
    assert second["purchase"].delivery_album_url is None
    assert str(second["communication"].id) not in str(payments(client_db, first))


def test_interacoes_selecao_e_remocao_A_preservam_B(client_db, commerce):
    for row in commerce:
        selected(client_db, row)
        main.favorite_photo(row["gallery"].id, row["photo"].id, row["customer_request"], client_db)
        main.create_photo_comment(row["gallery"].id, row["photo"].id,
            main.PhotoCommentInput(body=row["client"].full_name), row["customer_request"], client_db)
    first, second = commerce
    main.unselect_photo(first["gallery"].id, first["photo"].id, first["customer_request"], client_db)
    main.unfavorite_photo(first["gallery"].id, first["photo"].id, first["customer_request"], client_db)
    for model in (PhotoSelection, PhotoFavorite):
        remaining = list(client_db.scalars(select(model)))
        assert len(remaining) == 1 and remaining[0].tenant_id == second["tenant"].id
    own = main.client_comments(first["gallery"].id, first["customer_request"], client_db)
    assert [item["body"] for item in own["comments"]] == [first["client"].full_name]
    foreign_comment = client_db.scalar(select(PhotoComment).where(PhotoComment.tenant_id == second["tenant"].id))
    with pytest.raises(HTTPException):
        main.remove_own_comment(first["gallery"].id, foreign_comment.id, first["customer_request"], client_db)
    assert foreign_comment.removed_at is None


@pytest.mark.parametrize("resource", ["gallery", "photo"])
def test_UUID_estrangeiro_interacoes_equivale_ausente(client_db, commerce, resource):
    first, second = commerce
    for function in (main.select_photo, main.unselect_photo, main.favorite_photo,
                     main.unfavorite_photo, main.create_photo_comment):
        errors = []
        for candidate in (second[resource].id, uuid4()):
            args = {"gallery_id": first["gallery"].id, "photo_id": first["photo"].id,
                    "request": first["customer_request"], "db": client_db}
            args[f"{resource}_id"] = candidate
            if function is main.create_photo_comment:
                args["payload"] = main.PhotoCommentInput(body="synthetic")
            try:
                result = function(**args)
                errors.append((result.status_code, result.body))
            except HTTPException as exc:
                errors.append((exc.status_code, exc.detail))
        assert errors[0] == errors[1], function.__name__
    assert client_db.scalar(select(func.count()).select_from(PhotoSelection)) == 0


def test_carrinho_misto_recusado_antes_de_criar_grupo_ou_pedido(client_db, commerce, monkeypatch):
    for row in commerce:
        selected(client_db, row)
    materials = [entry for row in commerce for entry in unified_checkout._materials(client_db, row["client"])]
    monkeypatch.setattr(unified_checkout, "_materials", lambda *_: materials)
    before = client_db.scalar(select(func.count()).select_from(SaleOrder))
    with pytest.raises(CheckoutError):
        unified_checkout.prepare_group(client_db, commerce[0]["client"])
    assert client_db.scalar(select(func.count()).select_from(PaymentGroup)) == 0
    assert client_db.scalar(select(func.count()).select_from(SaleOrder)) == before


def test_material_de_B_nao_modifica_pedido_de_A(client_db, commerce):
    first, second = commerce
    selected(client_db, second)
    material = _checkout_material(client_db, gallery=second["gallery"], client=second["client"])
    before = (first["order"].total_cents, first["order"].client_id)
    with pytest.raises(CheckoutError):
        _synchronize_order(client_db, order=first["order"], gallery=first["gallery"],
                           client=first["client"], material=material)
    assert (first["order"].total_cents, first["order"].client_id) == before


def test_pagamento_e_entrega_estrangeiros_nao_mudam_estado(client_db, commerce):
    first, second = commerce
    reported(client_db, second)
    for candidate in (second["communication"].id, uuid4()):
        with pytest.raises(HTTPException) as exc:
            main.decide_payment_communication(candidate,
                main.PaymentDecisionInput(decision="confirmed", payment_group_id=second["group"].id),
                first["admin_request"], client_db)
        assert exc.value.status_code == 409
    for candidate in (second["purchase"].id, uuid4()):
        with pytest.raises(HTTPException) as exc:
            main.update_order_delivery(candidate, main.OrderDeliveryInput(
                album_url="https://photos.app.goo.gl/synthetic", version=0), first["admin_request"], client_db)
        assert exc.value.status_code == 404
    for candidate in (second["group"].id, uuid4()):
        with pytest.raises(HTTPException) as exc:
            main.report_unified_payment(candidate, main.GroupPaymentInput(
                revision=second["group"].revision, idempotency_key="negative"), first["customer_request"], client_db)
        assert exc.value.status_code == 409
    assert second["purchase"].payment_status == "pending"
    assert second["purchase"].delivery_album_url is None
    assert second["communication"].status == "pending_review"


def test_conta_sem_pix_nao_recebe_configuracao_da_outra(client_db, commerce):
    first, second = commerce
    client_db.delete(second["pix"])
    client_db.commit()
    selected(client_db, second)
    with pytest.raises(CheckoutError):
        unified_checkout.prepare_group(client_db, second["client"])
    assert client_db.scalar(select(func.count()).select_from(PaymentGroup)) == 0
    assert first["pix"].status == "active"


def test_historico_estrangeiro_recusado_antes_de_arquivo(client_db, commerce, monkeypatch):
    first, second = commerce
    reported(client_db, second)
    second["purchase"].payment_status = "confirmed"
    client_db.commit()
    item = client_db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == second["purchase"].id))
    def forbidden(*_):
        pytest.fail("Arquivo estrangeiro alcançado")
    monkeypatch.setattr(main, "historical_media_path", forbidden)
    for function in (main.client_purchased_photo_preview, main.client_historical_preview,
                     main.client_historical_delivery):
        with pytest.raises(HTTPException) as exc:
            function(item.id, first["customer_request"], client_db)
        assert exc.value.status_code == 403


def test_selecao_canonica_interacoes_checkout_e_views_proprios(client_db, commerce):
    from app.parent_registration import link_client_to_parent

    photos = []
    for row in commerce:
        folder = PhotoFolder(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
                             name="Pública sintética", status="released", position=1, audience_scope="all")
        client_db.add(folder)
        client_db.flush()
        photo = PhotoAsset(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            folder_id=folder.id, filename="public-synthetic.jpg", storage_key=f"synthetic/{uuid4()}.jpg")
        client_db.add(photo)
        client_db.flush()
        client_db.add(MediaDerivative(tenant_id=photo.tenant_id, photo_asset_id=photo.id,
            variant="client_preview", status="ready", relative_path=f"synthetic/{photo.id}.jpg"))
        link_client_to_parent(client_db, parent_gallery_id=row["parent"].id, client_id=row["client"].id)
        client_db.commit()
        photos.append(photo)
        main.select_photo_from_public_gallery(row["parent"].id, photo.id, row["customer_request"], client_db)
        main.favorite_canonical_photo(row["parent"].id, photo.id, row["customer_request"], client_db)
        main.record_canonical_photo_view(row["parent"].id, photo.id, row["customer_request"], client_db)
        main.create_canonical_photo_comment(row["parent"].id, photo.id,
            main.PhotoCommentInput(body=row["client"].full_name), row["customer_request"], client_db)
        group = unified_checkout.prepare_group(client_db, row["client"])
        client_db.commit()
        assert group.pix_copy_paste_snapshot == row["pix"].copy_paste
        order = client_db.scalar(select(SaleOrder).where(SaleOrder.payment_group_id == group.id))
        assert order.parent_gallery_id == row["parent"].id and order.derived_gallery_id is None
        assert str(row["client"].id) in str(payments(client_db, row))
    first, second = commerce
    for function in (main.select_photo_from_public_gallery, main.favorite_canonical_photo,
                     main.record_canonical_photo_view):
        with pytest.raises(HTTPException):
            function(first["parent"].id, photos[1].id, first["customer_request"], client_db)
        with pytest.raises(HTTPException):
            function(second["parent"].id, photos[1].id, first["customer_request"], client_db)
    main.unselect_photo_from_public_gallery(first["parent"].id, photos[0].id,
                                           first["customer_request"], client_db)
    assert client_db.scalar(select(PhotoSelection).where(PhotoSelection.client_id == second["client"].id))


def test_finalizacao_sem_cobranca_e_projecao_sem_comunicacao(client_db, commerce):
    from app.client_commerce import client_photo_states
    from app.commercial_projection import build_commercial_projections

    first, second = commerce
    first["parent"].payment_required = False
    client_db.commit()
    selected(client_db, first)
    entry = unified_checkout.cart_payload(client_db, first["client"])["groups"][0]
    order = unified_checkout.finalize_selection(client_db, first["client"],
        first["gallery"].id, entry["revision"], "same-external-key")
    client_db.commit()
    assert order.payment_status == "not_required" and order.frozen_at
    assert client_db.scalar(select(func.count()).select_from(PaymentCommunication)) == 0
    states = client_photo_states(client_db, gallery_id=first["gallery"].id,
        client_id=first["client"].id, photo_ids={first["photo"].id})
    assert states[first["photo"].id] == "selection_finalized"
    projections = build_commercial_projections(client_db, tenant_id=first["tenant"].id,
        gallery_ids={first["gallery"].id}, client_ids={first["client"].id})
    assert projections[first["gallery"].id, first["client"].id].order_count == 1
    assert main.client_purchase_history(second["customer_request"], client_db)["orders"] == []


def test_checkout_legado_e_comunicacao_preservam_owner_e_pix(client_db, commerce):
    first, second = commerce
    selected(client_db, first)
    result = main.checkout_gallery(first["gallery"].id,
        main.CheckoutInput(idempotency_key="legacy-synthetic-key"), first["customer_request"], client_db)
    order = client_db.get(SaleOrder, UUID(result["id"]))
    assert order.pix_copy_paste_snapshot == first["pix"].copy_paste
    result = main.communicate_payment(first["gallery"].id, order.id,
        main.PaymentCommunicationInput(idempotency_key="legacy-payment-key"), first["customer_request"], client_db)
    communication = client_db.get(PaymentCommunication, UUID(result["id"]))
    assert communication.tenant_id == first["tenant"].id
    assert order.frozen_at and second["order"].frozen_at is None


@pytest.mark.parametrize("kind", ["client", "parent", "photo"])
def test_snapshot_ORM_cruzado_recusado_antes_de_copiar_dados(client_db, commerce, kind):
    first, second = commerce
    if kind == "photo":
        record = SaleOrderItem(tenant_id=first["tenant"].id, sale_order_id=first["order"].id,
                              photo_asset_id=second["photo"].id, unit_price_cents=1)
    else:
        record = SaleOrder(tenant_id=first["tenant"].id, total_cents=1,
            parent_gallery_id=second["parent"].id if kind == "parent" else first["parent"].id,
            client_id=second["client"].id if kind == "client" else first["client"].id)
    with pytest.raises(ValueError), client_db.begin_nested():
        client_db.add(record)
        client_db.flush()
    if kind == "photo":
        assert record.photo_asset_id_snapshot is None
    else:
        assert record.client_name_snapshot is None and record.parent_gallery_name_snapshot is None


def test_correcao_e_retry_estrangeiros_preservam_decisao_e_entrega_B(client_db, commerce):
    from app.auth import PaymentNotificationOutbox

    first, second = commerce
    reported(client_db, second)
    main.decide_payment_communication(second["communication"].id,
        main.PaymentDecisionInput(decision="confirmed", payment_group_id=second["group"].id),
        second["admin_request"], client_db)
    outbox = client_db.scalar(select(PaymentNotificationOutbox).where(
        PaymentNotificationOutbox.payment_communication_id == second["communication"].id))
    outbox.status = "failed"
    client_db.commit()
    with pytest.raises(HTTPException):
        main.correct_payment_confirmation(second["communication"].id,
            main.PaymentCorrectionInput(idempotency_key="synthetic-correction", payment_group_id=second["group"].id),
            first["admin_request"], client_db)
    with pytest.raises(HTTPException) as exc:
        main.retry_payment_notification(outbox.id, first["admin_request"], client_db)
    assert exc.value.status_code == 404
    assert outbox.status == "failed" and second["purchase"].payment_status == "confirmed"
    result = main.correct_payment_confirmation(second["communication"].id,
        main.PaymentCorrectionInput(idempotency_key="synthetic-correction", payment_group_id=second["group"].id),
        second["admin_request"], client_db)
    assert result["status"] == "pending_review" and second["purchase"].payment_status == "pending"
