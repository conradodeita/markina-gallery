"""Recuperação delimitada com provedor sintético e sem dinheiro real."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.auth import (
    AuditEvent,
    Client,
    DerivedGallery,
    GlobalPixSettings,
    InfinitePaySettings,
    PaymentGroup,
    PhotoAsset,
    PhotoSelection,
    ProviderPayment,
    ProviderPaymentAttempt,
    ProviderPaymentReceipt,
    SaleOrder,
    SaleOrderItem,
    engine,
    now,
)
from app.payment_provider import InfinitePayHttpProvider, SyntheticPaymentProvider
from app.provider_checkout import issue_provider_payment
from app.provider_confirmation import apply_payment_check
from app.tenancy import TenantContextError
from app.unified_checkout import _fingerprint, _materials, cart_payload
from operations import recover_three_infinitepay_purchases as recovery
from tests.test_provider_checkout import SessionLocal, prepare, setup
from tests.test_provider_checkout import isolated_cart_database as _isolated
from tests.test_provider_checkout import synthetic_infinitepay_binding as _binding
from tests.test_provider_confirmation import verified_result

isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


def new_selection(db, owner_id, gallery_id):
    gallery = db.get(DerivedGallery, gallery_id)
    example = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == gallery_id))
    photo = PhotoAsset(tenant_id=gallery.tenant_id, parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery_id, folder_id=example.folder_id,
        filename="recovery-synthetic.jpg", storage_key=f"synthetic/{uuid4()}.jpg")
    db.add(photo)
    db.flush()
    db.add(PhotoSelection(tenant_id=gallery.tenant_id, client_id=owner_id,
                         derived_gallery_id=gallery_id, photo_asset_id=photo.id))
    db.commit()
    return photo.id


@pytest.fixture
def case(monkeypatch):
    def no_real_checkout(*_args, **_kwargs):
        raise AssertionError("Operação não pode criar checkout externo")
    monkeypatch.setattr(InfinitePayHttpProvider, "create_checkout", no_real_checkout)
    owner_id, _, gallery_ids, revision = setup()
    with SessionLocal() as db:
        client = db.get(Client, owner_id)
        targets = {}
        for index, outcome in enumerate(("accepted", "unknown", "unknown")):
            if index:
                new_selection(db, owner_id, gallery_ids[0])
                revision = _fingerprint([row for row in _materials(db, client) if row[1].payment_required])
            payment = prepare(db, owner_id, revision)
            db.commit()
            issue_provider_payment(db, payment.id, SyntheticPaymentProvider(outcome))
            targets[payment.id] = (payment.total_cents, payment.state, 3 if index == 0 else 1, client.id)
        new_selection(db, owner_id, gallery_ids[0])
        revision = _fingerprint([row for row in _materials(db, client) if row[1].payment_required])
        paid = prepare(db, owner_id, revision)
        db.commit()
        issue_provider_payment(db, paid.id, SyntheticPaymentProvider("accepted"))
        result = verified_result(db, paid)
        apply_payment_check(db, paid.id, requested_slug=result.slug, result=result)
        db.commit()
        extra_photo = new_selection(db, owner_id, gallery_ids[0])
        actor_id = db.scalar(select(InfinitePaySettings.admin_user_id))
        monkeypatch.setattr(recovery, "TENANT_ID", client.tenant_id)
        monkeypatch.setattr(recovery, "TARGETS", targets)
        return {"client": owner_id, "actor": actor_id, "targets": targets,
                "paid": paid.id, "extra": extra_photo, "gallery": gallery_ids[0]}


def state():
    with SessionLocal() as db:
        return {
            model.__tablename__: sorted(
                [tuple((column.name, getattr(row, column.name)) for column in model.__table__.columns)
                 for row in db.scalars(select(model))], key=str)
            for model in (ProviderPayment, ProviderPaymentAttempt, SaleOrder, SaleOrderItem,
                          PhotoSelection, PaymentGroup, AuditEvent)
        }


def simulate(case, **kwargs):
    with SessionLocal() as db:
        return recovery.execute(db, case["actor"], **kwargs)


def apply(case, plan):
    return simulate(case, apply=True, expected_fingerprint=plan["fingerprint"])


def test_simulacao_reverte_tudo_e_nao_expoe_urls(case, tmp_path):
    before = state()
    path = tmp_path / "before.json"
    report = simulate(case, before_path=path)
    assert state() == before
    assert report["mode"] == "dry-run" and not report["already_applied"]
    assert report["remote_checkout_state"] == "unknown"
    assert len(report["fingerprint"]) == 64
    assert report["carts"][0]["restored_quantity"] == 5
    assert report["carts"][0]["quantity"] == 6
    assert report["carts"][0]["total_cents"] == 4200
    assert report["carts"][0]["pix_available"] and report["carts"][0]["card_available"]
    assert "https://" not in str(report) and "checkout_url" not in path.read_text()


def test_aplicacao_preserva_snapshots_e_compra_confirmada(case):
    before = state()
    report = apply(case, simulate(case))
    assert report["mode"] == "apply" and not report["already_applied"]
    with SessionLocal() as db:
        for payment_id in case["targets"]:
            payment = db.get(ProviderPayment, payment_id)
            assert payment.state == "exception" and payment.confirmed_at is None
            orders = list(db.scalars(select(SaleOrder).where(SaleOrder.provider_payment_id == payment_id)))
            assert orders and all(row.payment_status == "cancelled" and row.frozen_at for row in orders)
        paid = db.get(ProviderPayment, case["paid"])
        assert paid.state == "confirmed" and paid.provider_transaction_nsu
        assert db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.event == recovery.EVENT)) == 3
        cart = cart_payload(db, db.get(Client, case["client"]))
        assert cart["quantity"] == 6 and cart["total_cents"] == 4200
        assert cart["card_payment"] is None and cart["pix_available"] and cart["can_prepare"]
    after = state()
    assert before["sale_order_item"] == [row for row in after["sale_order_item"]
        if dict(row)["sale_order_id"] in {dict(o)["id"] for o in before["sale_order"]}]
    assert before["provider_payment_attempt"] == after["provider_payment_attempt"]
    old_payments = {dict(row)["id"]: dict(row) for row in before["provider_payment"]}
    for row in after["provider_payment"]:
        current = dict(row)
        old = old_payments[current["id"]]
        if current["id"] in case["targets"]:
            assert current.pop("state") == "exception"
            assert current.pop("revision_number") == old.pop("revision_number") + 1
            old.pop("state")
            old.pop("updated_at")
            current.pop("updated_at")
        assert current == old
    old_orders = {dict(row)["id"]: dict(row) for row in before["sale_order"]}
    for row in after["sale_order"]:
        current = dict(row)
        if current["id"] in old_orders:
            old = old_orders[current["id"]]
            old.pop("payment_status")
            current.pop("payment_status")
            assert current == old


@pytest.mark.parametrize("failure", ["actor", "scope", "client", "confirmed", "stale", "pix", "eligibility", "snapshot"])
def test_recusa_preserva_todo_lote(case, monkeypatch, failure):
    plan = simulate(case)
    actor = case["actor"]
    with SessionLocal() as db:
        if failure == "actor":
            actor = uuid4()
        elif failure == "scope":
            targets = dict(case["targets"])
            targets[uuid4()] = targets.pop(next(iter(targets)))
            monkeypatch.setattr(recovery, "TARGETS", targets)
        elif failure == "client":
            targets = dict(case["targets"])
            key = next(iter(targets))
            targets[key] = (*targets[key][:3], uuid4())
            monkeypatch.setattr(recovery, "TARGETS", targets)
        elif failure == "confirmed":
            payment = db.get(ProviderPayment, next(iter(case["targets"])))
            result = verified_result(db, payment)
            apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
            db.commit()
        elif failure == "stale":
            new_selection(db, case["client"], case["gallery"])
        elif failure == "pix":
            db.scalar(select(GlobalPixSettings)).copy_paste = ""
            db.commit()
        elif failure == "eligibility":
            db.get(DerivedGallery, case["gallery"]).selection_expires_at = now() - timedelta(days=1)
            db.commit()
        elif failure == "snapshot":
            db.scalar(select(SaleOrderItem).join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id).where(
                SaleOrder.provider_payment_id.in_(case["targets"]))).unit_price_cents += 1
            db.commit()
    before = state()
    with SessionLocal() as db, pytest.raises((recovery.RecoveryError, TenantContextError)):
        recovery.execute(db, actor, apply=failure not in {"pix", "eligibility"},
                         expected_fingerprint=plan["fingerprint"])
    assert state() == before


def test_reexecucao_nao_reabre_fotos_consumidas_por_outro_checkout(case):
    plan = simulate(case)
    apply(case, plan)
    with SessionLocal() as db:
        client = db.get(Client, case["client"])
        payment = prepare(db, client.id, cart_payload(db, client)["cart_revision"])
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("unknown"))
    before = state()
    repeated = apply(case, plan)
    assert repeated["already_applied"] and not repeated["mutated"]
    assert state() == before


@pytest.mark.parametrize("present", [False, True])
def test_aplicacao_exige_preimagem_compativel(case, tmp_path, present):
    plan = simulate(case)
    path = tmp_path / "before.json"
    if present:
        path.write_text("{}")
    before = state()
    with pytest.raises(recovery.RecoveryError):
        simulate(case, apply=True, expected_fingerprint=plan["fingerprint"], before_path=path)
    assert state() == before


def test_retorno_tardio_retido_sem_alterar_pix_novo(case):
    report = apply(case, simulate(case))
    with SessionLocal() as db:
        group = db.get(PaymentGroup, UUID(report["carts"][0]["pix_group_id"]))
        group_before = (group.state, group.total_cents, group.revision)
        payment = db.get(ProviderPayment, next(iter(case["targets"])))
        result = verified_result(db, payment)
        outcome = apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
        assert not outcome.confirmed and outcome.state == "exception"
        db.refresh(group)
        assert (group.state, group.total_cents, group.revision) == group_before
        assert db.scalar(select(ProviderPaymentReceipt.state).where(
            ProviderPaymentReceipt.payment_id == payment.id)) == "ignored"
        assert db.scalar(select(func.count(AuditEvent.id)).where(
            AuditEvent.event == "provider_payment.invalid_state")) == 1


def test_aplicacao_concorrente_grava_uma_unica_recuperacao(case):
    if engine.dialect.name != "postgresql":
        pytest.skip("Locks concorrentes exigem PostgreSQL sintético")
    plan = simulate(case)
    barrier = Barrier(2)

    def recover():
        barrier.wait(timeout=10)
        return apply(case, plan)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: recover(), range(2)))
    assert sorted(row["already_applied"] for row in results) == [False, True]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.event == recovery.EVENT)) == 3


@pytest.mark.parametrize("_run", range(3))
def test_confirmacao_concorrente_nao_e_convertida_em_pix(case, _run):
    if engine.dialect.name != "postgresql":
        pytest.skip("Locks concorrentes exigem PostgreSQL sintético")
    plan = simulate(case)
    barrier = Barrier(2)
    target_id = next(iter(case["targets"]))

    def confirm():
        with SessionLocal() as db:
            result = verified_result(db, db.get(ProviderPayment, target_id))
            barrier.wait(timeout=10)
            outcome = apply_payment_check(db, target_id, requested_slug=result.slug, result=result)
            db.commit()
            return outcome.confirmed

    def recover():
        barrier.wait(timeout=10)
        try:
            return not apply(case, plan)["already_applied"]
        except recovery.RecoveryError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        confirmed = pool.submit(confirm)
        recovered = pool.submit(recover)
        assert confirmed.result() != recovered.result()


@pytest.mark.parametrize("gate", ["fingerprint", "acknowledgement", "runtime"])
def test_cli_recusa_sem_precondicoes_antes_de_abrir_banco(monkeypatch, tmp_path, gate):
    def no_database():
        raise AssertionError("CLI deveria recusar antes de acessar o banco")
    monkeypatch.setattr(recovery, "SessionLocal", no_database)
    monkeypatch.setenv("APP_VERSION", "wrong-runtime" if gate == "runtime" else recovery.BASE_SHA)
    args = ["recovery", "--mode", "apply", "--actor-admin-id", str(uuid4()),
            "--before-file", str(tmp_path / "before.json")]
    if gate != "fingerprint":
        args.extend(["--expected-fingerprint", "0" * 64])
    if gate != "acknowledgement":
        args.append("--acknowledge-remote-link-may-remain-payable")
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit) as exc:
        recovery.main()
    assert exc.value.code == 2
