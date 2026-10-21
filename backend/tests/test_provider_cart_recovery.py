"""Contrato: as mesmas fotos voltam ao carrinho, sem recebimento fictício."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth import (
    AdminUser,
    AuditEvent,
    Client,
    DerivedGallery,
    GlobalPixSettings,
    InfinitePaySettings,
    ParentGallery,
    PhotoAsset,
    PhotoSelection,
    PriceRule,
    ProviderPayment,
    ProviderPaymentAttempt,
    ProviderPaymentReceipt,
    SaleOrder,
    SaleOrderItem,
    Tenant,
    TenantAdmin,
    now,
)
from app.payment_provider import SyntheticPaymentProvider
from app.provider_cart_recovery import (
    RECOVERY_EVENT,
    CartRecoveryError,
    preview_cart_recovery,
    reopen_payment_cart,
)
from app.provider_checkout import issue_provider_payment
from app.provider_confirmation import apply_payment_check
from app.tenancy import TenantContextError
from app.unified_checkout import cart_payload
from tests.test_provider_checkout import SessionLocal as _SessionLocal
from tests.test_provider_checkout import isolated_cart_database as _isolated
from tests.test_provider_checkout import prepare, setup
from tests.test_provider_checkout import synthetic_infinitepay_binding as _binding
from tests.test_provider_confirmation import verified_result

SessionLocal = _SessionLocal
isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


@pytest.fixture
def case():
    owner, other, galleries, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner, revision)
        payment_id = payment.id
        db.commit()
        issue_provider_payment(db, payment_id, SyntheticPaymentProvider("accepted"))
        actor = db.scalar(select(InfinitePaySettings.admin_user_id))
        wanted = set(db.execute(select(SaleOrder.derived_gallery_id, SaleOrderItem.photo_asset_id_snapshot)
            .join(SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id)
            .where(SaleOrder.provider_payment_id == payment_id)))
        return {"owner": owner, "other": other, "galleries": galleries, "payment": payment_id,
                "actor": actor, "wanted": wanted, "revision": payment.revision_number}


def preview(case):
    with SessionLocal() as db:
        return preview_cart_recovery(db, case["actor"], case["payment"], expected_revision=case["revision"])


def decision(case, plan, *, key=None, commit=True, **overrides):
    args = {"expected_revision": plan["revision"], "expected_fingerprint": plan["fingerprint"],
            "decision_id": key or uuid4(), "reason": "Sem retorno; recuperar fotos da compra",
            "acknowledge_remote_checkout": True, **overrides}
    with SessionLocal() as db:
        result = reopen_payment_cart(db, case["actor"], case["payment"], **args)
        if commit:
            db.commit()
        else:
            db.rollback()
        return result


def state(case):
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        return (payment.state, payment.revision_number,
                list(db.execute(select(PhotoSelection.id, PhotoSelection.photo_asset_id).order_by(PhotoSelection.id))),
                list(db.execute(select(SaleOrder.id, SaleOrder.payment_status).order_by(SaleOrder.id))),
                db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.event == RECOVERY_EVENT)))


@pytest.mark.parametrize("unknown", [False, True])
def test_mesmas_fotos_retornam_sem_cliente_selecionar_novamente(case, unknown):
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        if unknown:
            payment.state = "verification_required"
            payment.checkout_url = None
            attempt = db.scalar(select(ProviderPaymentAttempt))
            attempt.state, attempt.error_category = "unknown", "response_missing_url"
            db.commit()
        old_url = payment.checkout_url
        original = [(order.id, order.total_cents, order.frozen_at, order.provider_payment_id)
                    for order in db.scalars(select(SaleOrder).order_by(SaleOrder.id))]
    before = state(case)
    plan = preview(case)
    assert state(case) == before
    assert plan["restored_quantity"] == plan["quantity"] == 3
    assert plan["total_cents"] == 2100 and plan["pix_available"] and plan["card_available"]
    result = decision(case, plan)
    assert not result["already_reopened"] and result["resume_path"] == "/library/cart"
    with SessionLocal() as db:
        selected = set(db.execute(select(PhotoSelection.derived_gallery_id, PhotoSelection.photo_asset_id)
                                 .where(PhotoSelection.client_id == case["owner"])))
        assert selected == case["wanted"]
        cart = cart_payload(db, db.get(Client, case["owner"]))
        assert cart["quantity"] == 3 and cart["can_prepare"] and cart["card_payment"] is None
        assert {item["id"] for group in cart["groups"] for item in group["items"]} == {str(p) for _, p in case["wanted"]}
        payment = db.get(ProviderPayment, case["payment"])
        assert payment.state == "exception" and payment.confirmed_at is None and payment.checkout_url == old_url
        assert [(order.id, order.total_cents, order.frozen_at, order.provider_payment_id)
                for order in db.scalars(select(SaleOrder).order_by(SaleOrder.id))] == original
        assert all(order.payment_status == "cancelled" for order in db.scalars(select(SaleOrder)))
        assert db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.event == RECOVERY_EVENT)) == 1


def test_preserva_foto_nova_sem_duplicar_antigas(case):
    with SessionLocal() as db:
        old = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == case["galleries"][0]))
        extra = PhotoAsset(tenant_id=old.tenant_id, parent_gallery_id=old.parent_gallery_id,
            derived_gallery_id=old.derived_gallery_id, folder_id=old.folder_id,
            filename="nova-foto.jpg", storage_key=f"synthetic/{uuid4()}.jpg")
        db.add(extra)
        db.flush()
        selection = PhotoSelection(tenant_id=old.tenant_id, client_id=case["owner"],
            derived_gallery_id=old.derived_gallery_id, photo_asset_id=extra.id)
        db.add(selection)
        db.commit()
        new_selection_id = selection.id
    plan = preview(case)
    assert plan["quantity"] == 4 and plan["restored_quantity"] == 3 and plan["total_cents"] == 2800
    decision(case, plan)
    with SessionLocal() as db:
        assert db.get(PhotoSelection, new_selection_id) is not None
        assert db.scalar(select(func.count(PhotoSelection.id))) == 4


@pytest.mark.parametrize("method", ["card", "pix"])
def test_respeita_meios_habilitados_sem_exigir_pix_para_cartao(case, method):
    with SessionLocal() as db:
        if method == "card":
            db.scalar(select(GlobalPixSettings)).copy_paste = ""
        else:
            db.scalar(select(InfinitePaySettings)).card_enabled = False
        db.commit()
    plan = preview(case)
    assert plan["card_available"] == (method == "card")
    assert plan["pix_available"] == (method == "pix")
    decision(case, plan)


@pytest.mark.parametrize("failure", ["confirmed", "nsu", "clear_failure", "snapshot", "receipt", "expired", "no_method", "stale", "ack", "reason"])
def test_recusas_nao_liberam_fotos_nem_alteram_compra(case, failure):
    plan = preview(case)
    overrides = {}
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        if failure == "confirmed":
            evidence = verified_result(db, payment)
            apply_payment_check(db, payment.id, requested_slug=evidence.slug, result=evidence)
        elif failure == "nsu":
            payment.provider_transaction_nsu = "synthetic-known-transaction"
        elif failure == "clear_failure":
            payment.state = "failed_before_issue"
        elif failure == "snapshot":
            db.scalar(select(SaleOrderItem)).unit_price_cents += 1
        elif failure == "receipt":
            db.add(ProviderPaymentReceipt(tenant_id=payment.tenant_id, client_id=payment.client_id,
                payment_id=payment.id, digest=uuid4().hex * 2, transaction_nsu="candidate",
                slug="candidate", verification_profile=payment.verification_profile, state="processing"))
        elif failure == "expired":
            db.get(DerivedGallery, case["galleries"][0]).selection_expires_at = now() - timedelta(days=1)
        elif failure == "no_method":
            db.scalar(select(InfinitePaySettings)).card_enabled = False
            db.scalar(select(GlobalPixSettings)).copy_paste = ""
        elif failure == "stale":
            overrides["expected_fingerprint"] = "0" * 64
        elif failure == "ack":
            overrides["acknowledge_remote_checkout"] = False
        elif failure == "reason":
            overrides["reason"] = " "
        db.commit()
    before = state(case)
    with pytest.raises(CartRecoveryError):
        decision(case, plan, **overrides)
    assert state(case) == before


def test_sem_commit_e_repeticao_apos_nova_compra_preservam_selecao(case):
    plan = preview(case)
    before = state(case)
    decision(case, plan, commit=False)
    assert state(case) == before
    key = uuid4()
    decision(case, plan, key=key)
    with SessionLocal() as db:
        cart = cart_payload(db, db.get(Client, case["owner"]))
        payment = prepare(db, case["owner"], cart["cart_revision"])
        new_id = payment.id
        db.commit()
        issue_provider_payment(db, new_id, SyntheticPaymentProvider("accepted"))
    before = state(case)
    repeated = decision(case, plan, key=key)
    assert repeated["already_reopened"] and state(case) == before
    with SessionLocal() as db:
        assert db.get(ProviderPayment, new_id).state == "awaiting_payment"
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_actor_inexistente_ou_compra_ausente_nao_revela_dados(case):
    before = state(case)
    with SessionLocal() as db:
        with pytest.raises(TenantContextError):
            preview_cart_recovery(db, uuid4(), case["payment"], expected_revision=case["revision"])
        db.rollback()
        with pytest.raises(LookupError, match="Compra indisponível"):
            preview_cart_recovery(db, case["actor"], uuid4(), expected_revision=case["revision"])
    assert state(case) == before


def test_admin_ativo_de_outra_conta_nao_reabre_compra(case):
    before = state(case)
    with SessionLocal() as db:
        tenant = Tenant(id=uuid4())
        admin = AdminUser(email=f"other-{uuid4()}@example.test", password_hash="synthetic", totp_secret="synthetic")
        db.add_all([tenant, admin])
        db.flush()
        db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id))
        db.commit()
        with pytest.raises(LookupError, match="Compra indisponível"):
            preview_cart_recovery(db, admin.id, case["payment"], expected_revision=case["revision"])
    assert state(case) == before


def test_configuracao_alterada_exige_nova_previa(case):
    plan = preview(case)
    with SessionLocal() as db:
        db.scalar(select(GlobalPixSettings)).version += 1
        db.commit()
    before = state(case)
    with pytest.raises(CartRecoveryError, match="nova prévia"):
        decision(case, plan)
    assert state(case) == before


def test_preco_atual_recalculado_conserva_snapshot_da_compra(case):
    with SessionLocal() as db:
        for parent in db.scalars(select(ParentGallery)):
            parent.fixed_unit_price_cents = 800
        for rule in db.scalars(select(PriceRule)):
            rule.unit_price_cents = 800
        db.commit()
    plan = preview(case)
    assert plan["total_cents"] == 2400 and plan["previous_total_cents"] == 2100
    decision(case, plan)
    with SessionLocal() as db:
        assert db.get(ProviderPayment, case["payment"]).total_cents == 2100
        assert all(item.unit_price_cents == 700 for item in db.scalars(select(SaleOrderItem)))
