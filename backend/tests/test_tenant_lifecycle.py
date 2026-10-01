"""Estatísticas, exports e exclusões apenas em schemas e arquivos sintéticos A/B."""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import admin_account, homolog_cleanup, main
from app.auth import (
    AuthChallenge,
    Client,
    ClientDeletionReceipt,
    GalleryLifecycleOperation,
    WhatsAppDelivery,
)
from app.tenancy import TenantContextError
from tests.test_tenant_client_auth import challenge
from tests.test_tenant_commerce import client_db as _client_db
from tests.test_tenant_commerce import commerce as _commerce
from tests.test_tenant_commerce import graph as _graph
from tests.test_tenant_commerce import links as _links
from tests.test_tenant_commerce import reported

client_db = _client_db
graph = _graph
links = _links
commerce = _commerce


def stats(db, row, **filters):
    return main.admin_statistics(row["admin_request"], starts_at=None, ends_at=None,
        client_id=filters.get("client_id"), parent_gallery_id=filters.get("parent_gallery_id"),
        derived_gallery_id=filters.get("derived_gallery_id"), event_name=None,
        offset=None, purchased_offset=0, selected_offset=0, limit=100, db=db)


def test_estatisticas_filtros_e_TXT_somente_owner(client_db, commerce):
    for label, row in zip(("A", "B"), commerce, strict=True):
        row["photo"].filename = f"somente-{label}.jpg"
        reported(client_db, row)
        main.decide_payment_communication(row["communication"].id,
            main.PaymentDecisionInput(decision="confirmed", payment_group_id=row["group"].id),
            row["admin_request"], client_db)
    for index, row in enumerate(commerce):
        result = stats(client_db, row)
        assert result["revenue_cents"] == 700 + index*100 and result["purchased_count"] == 1
        other = commerce[1-index]
        assert str(other["photo"].id) not in str(result)
        assert str(other["client"].id) not in str(main.admin_statistics_filters(row["admin_request"], client_db))
        for name, candidate in (("client_id", other["client"].id), ("parent_gallery_id", other["parent"].id),
                                ("derived_gallery_id", other["gallery"].id)):
            assert stats(client_db, row, **{name: candidate})["revenue_cents"] == 0
        response = main.export_purchased_txt(row["admin_request"], None, None, None, None, None, None, client_db)
        assert row["photo"].filename.encode() in response.body and other["photo"].filename.encode() not in response.body


def test_resumo_mede_so_arquivos_proprios_sem_cache_global(client_db, commerce, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "history"))
    for index, row in enumerate(commerce):
        row["photo"].storage_key = f"tenants/{row['tenant'].id}/source/synthetic.jpg"
        path = tmp_path / "source" / row["photo"].storage_key
        path.parent.mkdir(parents=True)
        path.write_bytes(b"x" * (3 + index*1000))
    client_db.commit()
    for index, row in enumerate(commerce):
        result = main.admin_validation_summary(row["admin_request"], client_db)
        assert result["storage"] == {"photo_count": 1, "bytes": 3 + index*1000, "available": True}
        assert result["counts"]["clients"] == 1
        assert result["recent_galleries"][0]["id"] == str(row["parent"].id)


def test_export_de_selecao_e_pedido_recusa_alheio_antes_de_arquivo(client_db, commerce, monkeypatch):
    first, second = commerce
    for row in commerce:
        row["photo"].filename = f"{row['tenant'].id}.jpg"
        reported(client_db, row)
        main.decide_payment_communication(row["communication"].id,
            main.PaymentDecisionInput(decision="confirmed", payment_group_id=row["group"].id),
            row["admin_request"], client_db)
    monkeypatch.setattr(main, "safe_derivative_path", lambda *_: pytest.fail("Não deve ler arquivo alheio"))
    for operation, key, foreign in ((main.export_selection, "gallery_id", second["gallery"].id),
                                    (main.export_finalized_order, "order_id", second["purchase"].id)):
        errors = []
        for candidate in (foreign, uuid4()):
            args = {key: candidate, "format": "txt", "request": first["admin_request"], "db": client_db}
            if operation is main.export_selection:
                args["client_id"] = None
            with pytest.raises(HTTPException) as exc:
                operation(**args)
            errors.append((exc.value.status_code, exc.value.detail))
        assert errors[0] == errors[1]
    response = main.export_finalized_order(first["purchase"].id, "txt", first["admin_request"], client_db)
    assert first["photo"].filename.encode() in response.body and second["photo"].filename.encode() not in response.body


def test_exclusao_mesmo_telefone_preserva_OTP_cadastro_B_e_replay_contextual(client_db, commerce, links, monkeypatch):
    records = []
    for row, (token, _) in zip(commerce, links, strict=True):
        created = main.create_client(main.ClientInput(full_name="Exclusão sintética", phone_e164="+5511999990002"),
            row["admin_request"], client_db)
        client = client_db.get(Client, UUID(created["id"]))
        otp = challenge(client_db, token, phone=client.phone_e164)
        records.append((client, otp))
        row["admin_request"].scope["headers"].append((b"idempotency-key", b"same-deletion-key"))
    first, second = commerce
    a, b = records
    a_client_id, a_otp_id = a[0].id, a[1].id
    # A client's phone can also be the administrator's recipient: retain technical OTP.
    monkeypatch.setenv("WHATSAPP_BINDING_A_PHOTOGRAPHER_PHONE_E164", a[0].phone_e164)
    technical, code, _ = admin_account.create_security_challenge(client_db, purpose="password_recovery_otp",
        subject_fingerprint="synthetic-admin", admin=first["admin"])
    admin_delivery = admin_account._queue_admin_otp(client_db, technical, code, a[0].phone_e164)
    client_db.commit()
    admin_delivery_id = admin_delivery.id
    b_before = (b[0].full_name, b[0].phone_e164, b[1].secret_hash, b[1].used_at)
    assert main.get_client_deletion_inventory(a[0].id, first["admin_request"], client_db)["can_delete"]
    result = main.delete_client(a_client_id, first["admin_request"], client_db)
    assert result["status"] == "completed"
    assert client_db.get(Client, a_client_id) is None and client_db.get(AuthChallenge, a_otp_id) is None
    assert client_db.get(WhatsAppDelivery, admin_delivery_id) is not None
    client_db.refresh(b[0]); client_db.refresh(b[1])
    assert (b[0].full_name, b[0].phone_e164, b[1].secret_hash, b[1].used_at) == b_before
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery).where(
        WhatsAppDelivery.tenant_id == second["tenant"].id)) == 1
    assert main.delete_client(a_client_id, first["admin_request"], client_db)["receipt_id"] == result["receipt_id"]
    assert main._client_deletion_transaction_state(client_db, "same-deletion-key",
        tenant_id=second["tenant"].id) == ("rolled_back", None)
    # Same key in B is an independent operation, not replay of A's receipt.
    other = main.delete_client(b[0].id, second["admin_request"], client_db)
    assert other["receipt_id"] != result["receipt_id"]
    assert client_db.scalar(select(func.count()).select_from(ClientDeletionReceipt)) == 2


def test_exclusao_alheia_neutra_e_historico_protegido(client_db, commerce):
    first, second = commerce
    first["admin_request"].scope["headers"].append((b"idempotency-key", b"negative-deletion-key"))
    for operation in (main.get_client_deletion_inventory, main.delete_client):
        errors = []
        for candidate in (second["client"].id, uuid4()):
            with pytest.raises(HTTPException) as exc:
                operation(candidate, first["admin_request"], client_db)
            errors.append((exc.value.status_code, exc.value.detail))
        assert errors[0] == errors[1] and errors[0][0] == 404
    with pytest.raises(HTTPException) as exc:
        main.delete_client(first["client"].id, first["admin_request"], client_db)
    assert exc.value.status_code == 409
    assert client_db.get(Client, first["client"].id) and client_db.get(Client, second["client"].id)


def test_lifecycle_operacao_status_cancel_e_retry_contextuais(client_db, commerce):
    for row in commerce:
        row["admin_request"].scope["headers"].append((b"idempotency-key", b"same-lifecycle-key"))
    first, second = commerce
    foreign = main.delete_parent_gallery(second["parent"].id, second["admin_request"], client_db)
    for operation in (main.gallery_lifecycle_operation_status, main.retry_gallery_lifecycle_operation,
                      main.cancel_gallery_lifecycle_operation):
        errors = []
        for candidate in (UUID(foreign["operation_id"]), uuid4()):
            with pytest.raises(HTTPException) as exc:
                operation(candidate, first["admin_request"], client_db)
            errors.append((exc.value.status_code, exc.value.detail))
        assert errors[0] == errors[1]
    own = main.delete_parent_gallery(first["parent"].id, first["admin_request"], client_db)
    cancelled = main.cancel_gallery_lifecycle_operation(UUID(own["operation_id"]), first["admin_request"], client_db)
    assert cancelled["status"] == "cancelled" and first["parent"].lifecycle_status == "active"
    assert client_db.get(GalleryLifecycleOperation, UUID(foreign["operation_id"])).status == "queued"
    assert second["parent"].lifecycle_status == "deleting"


def test_cleanup_integral_recusa_multitenant_antes_de_arquivos(client_db, commerce, monkeypatch):
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setattr(homolog_cleanup, "_clear_media_root", lambda *_: pytest.fail("Não limpar mídia"))
    with pytest.raises(TenantContextError):
        homolog_cleanup.execute(client_db, homolog_cleanup.CONFIRMATION)
    assert client_db.scalar(select(func.count()).select_from(Client)) == 2
