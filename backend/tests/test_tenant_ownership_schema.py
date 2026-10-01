"""Constraints de domínio em inserts diretos, sem API, workers ou dados reais."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import ForeignKeyConstraint, delete, text
from sqlalchemy.exc import IntegrityError

from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    AssetFileCleanup,
    AuthChallenge,
    AuthSession,
    Base,
    Client,
    ClientDeletionReceipt,
    DerivedGallery,
    FacialJob,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryClientState,
    GalleryLifecycleOperation,
    GalleryMembershipNotificationOutbox,
    GlobalPixSettings,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    PaymentGroup,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    ProgressivePricingPreset,
    PushSubscription,
    SaleOrder,
    SaleOrderItem,
    Tenant,
    TenantAdmin,
    now,
)
from app.ownership_schema import CONTEXTUAL_TABLES, SHARED_TABLES
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


@pytest.fixture
def graph(client_db):
    records = []
    for label in ("A", "B"):
        tenant = Tenant()
        client_db.add(tenant)
        client_db.flush()
        admin = AdminUser(email=f"{label}@example.test", password_hash="synthetic", totp_secret="fake")
        client = Client(tenant_id=tenant.id, full_name=f"Sintética {label}", phone_e164="+5511999990001")
        parent = ParentGallery(tenant_id=tenant.id, name=f"Sintética {label}")
        client_db.add_all([admin, client, parent])
        client_db.flush()
        client_db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id))
        state = GalleryClientState(tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id)
        folder = PhotoFolder(tenant_id=tenant.id, parent_gallery_id=parent.id, name="Sintética")
        gallery = DerivedGallery(tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id,
                                 name="Legada sintética")
        client_db.add_all([state, folder, gallery])
        client_db.flush()
        photo = PhotoAsset(tenant_id=tenant.id, parent_gallery_id=parent.id, folder_id=folder.id,
                           filename="synthetic.jpg", storage_key=f"{tenant.id}/{uuid4()}.jpg")
        order = SaleOrder(tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id,
                          derived_gallery_name_snapshot="Sintética", parent_gallery_id_snapshot=parent.id,
                          parent_gallery_name_snapshot="Sintética", total_cents=0)
        setting = NotificationSetting(tenant_id=tenant.id, event_type="payment_confirmed",
                                      whatsapp_body="Sintética", push_title="Sintética", push_body="Sintética")
        client_db.add_all([photo, order, setting])
        client_db.flush()
        event = NotificationEvent(tenant_id=tenant.id, event_key="same-key",
                                  event_type=setting.event_type, parent_gallery_id=parent.id,
                                  client_id=client.id, template_version=1, push_title="Sintética",
                                  push_body="Sintética", whatsapp_body="Sintética", target_path="/library",
                                  expires_at=now() + timedelta(hours=1))
        client_db.add(event)
        client_db.flush()
        records.append({"tenant": tenant, "admin": admin, "client": client, "parent": parent, "folder": folder,
                            "gallery": gallery, "photo": photo, "order": order, "event": event})
    return records


def test_catalogo_postgresql_conserva_owner_e_constraints(client_db):
    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Conferência do catálogo PostgreSQL")
    schema = client_db.bind.get_execution_options()["schema_translate_map"][None]
    attributes = dict(client_db.execute(text(
        "SELECT c.relname, a.attnotnull FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "WHERE c.relnamespace = to_regnamespace(:schema) AND c.relkind IN ('r', 'p') "
        "AND a.attname = 'tenant_id'"
    ), {"schema": schema}).all())
    owned = set(Base.metadata.tables) - SHARED_TABLES
    assert set(attributes) == owned
    assert all(attributes[name] for name in owned - CONTEXTUAL_TABLES)
    actual = set(client_db.scalars(text(
        "SELECT conname FROM pg_constraint WHERE connamespace = to_regnamespace(:schema)"
    ), {"schema": schema}))
    expected = {
        constraint.name for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint) and constraint.name
        and constraint.name.startswith("fk_owner_")
    }
    assert len(expected) > 100 and expected <= actual


@pytest.mark.parametrize("kind", [
    "state", "folder", "private", "access", "group", "item", "receipt", "push",
    "session", "selection", "facial_job",
])
def test_insert_cruzado_recusado_pelo_banco(client_db, graph, kind):
    first, second = graph
    owner = first["tenant"].id
    if kind == "state":
        table = GalleryClientState.__table__
        values = {"parent_gallery_id": first["parent"].id, "client_id": second["client"].id}
    elif kind == "folder":
        table = PhotoFolder.__table__
        values = {"parent_gallery_id": second["parent"].id, "name": "Inválida"}
    elif kind == "private":
        table = DerivedGallery.__table__
        values = {"parent_gallery_id": first["parent"].id, "client_id": second["client"].id, "name": "Inválida"}
    elif kind == "access":
        table = GalleryAccess.__table__
        values = {"gallery_id": second["parent"].id, "parent_gallery_id": second["parent"].id,
                      "client_id": first["client"].id}
    elif kind == "group":
        table = PaymentGroup.__table__
        values = {"client_id": second["client"].id, "revision": "synthetic", "total_cents": 0,
                      "pix_copy_paste_snapshot": "synthetic-only", "pix_configuration_snapshot": {}}
    elif kind == "item":
        table = SaleOrderItem.__table__
        values = {"sale_order_id": first["order"].id, "photo_asset_id": second["photo"].id,
                      "photo_asset_id_snapshot": second["photo"].id,
                      "filename_snapshot": "synthetic.jpg", "unit_price_cents": 0}
    elif kind == "receipt":
        table = ClientDeletionReceipt.__table__
        values = {"actor_admin_id": second["admin"].id, "target_client_id": uuid4(),
                      "idempotency_key": "a" * 64, "inventory_fingerprint": "b" * 64}
    elif kind == "push":
        table = PushSubscription.__table__
        values = {"role": "client", "subject_id": second["client"].id,
                      "client_subject_id": second["client"].id, "endpoint_fingerprint": "synthetic",
                      "encrypted_subscription": "synthetic-envelope"}
    elif kind == "session":
        table = AuthSession.__table__
        values = {"role": "client", "subject_id": second["client"].id,
                  "client_subject_id": second["client"].id, "token_hash": "synthetic-hash",
                  "expires_at": now() + timedelta(hours=1)}
    elif kind == "selection":
        table = PhotoSelection.__table__
        values = {"parent_gallery_id": first["parent"].id, "client_id": first["client"].id,
                  "photo_asset_id": second["photo"].id}
    else:
        table = FacialJob.__table__
        values = {"parent_gallery_id": first["parent"].id, "photo_asset_id": second["photo"].id,
                  "kind": "index", "idempotency_key": "synthetic-job"}
    with pytest.raises(IntegrityError) as failure:
        client_db.execute(table.insert().values(tenant_id=owner, **values))
    if client_db.bind.dialect.name == "postgresql":
        assert failure.value.orig.diag.constraint_name.startswith("fk_owner_")


def test_configuracao_natural_e_singleton_por_conta(client_db, graph):
    for record in graph:
        owner = record["tenant"].id
        client_db.add(GlobalPixSettings(tenant_id=owner, admin_user_id=record["admin"].id))
        client_db.add(ProgressivePricingPreset(tenant_id=owner, code="same-code", name="Sintético"))
    client_db.flush()
    client_db.add(GlobalPixSettings(tenant_id=graph[0]["tenant"].id, admin_user_id=graph[0]["admin"].id))
    with pytest.raises(IntegrityError):
        client_db.flush()


def test_evento_nao_pode_usar_template_de_outro_dono(client_db, graph):
    first, second = graph
    client_db.add(NotificationSetting(tenant_id=second["tenant"].id, event_type="only-b",
                                      whatsapp_body="Sintético", push_title="Sintético", push_body="Sintético"))
    client_db.flush()
    with pytest.raises(IntegrityError):
        client_db.execute(NotificationEvent.__table__.insert().values(
            tenant_id=first["tenant"].id, event_type="only-b", event_key="invalid-template",
            template_version=1, push_title="Sintético", push_body="Sintético", whatsapp_body="Sintético",
            target_path="/library", expires_at=now() + timedelta(hours=1),
        ))


def test_destinatario_tipado_nao_pode_ser_de_outro_dono(client_db, graph):
    first, second = graph
    with pytest.raises(IntegrityError):
        client_db.execute(NotificationDelivery.__table__.insert().values(
            tenant_id=first["tenant"].id, event_id=first["event"].id, channel="whatsapp",
            recipient_role="client", recipient_id=second["client"].id,
            client_recipient_id=second["client"].id,
        ))


def test_outbox_preserva_dono_apos_excluir_origem(client_db):
    owner = Tenant()
    client_db.add(owner)
    client_db.flush()
    parent = ParentGallery(tenant_id=owner.id, name="Origem descartável")
    client_db.add(parent)
    client_db.flush()
    notice = GalleryMembershipNotificationOutbox(
        tenant_id=owner.id, parent_gallery_id=parent.id, event_key="same-key",
        event_type="private_created", parent_name_snapshot="Sintética", derived_name_snapshot="Sintética",
    )
    cleanup = AssetFileCleanup(tenant_id=owner.id, paths=[f"{owner.id}/synthetic.jpg"])
    client_db.add_all([notice, cleanup])
    client_db.flush()
    client_db.execute(delete(ParentGallery).where(ParentGallery.id == parent.id))
    client_db.expire_all()
    assert client_db.get(GalleryMembershipNotificationOutbox, notice.id).parent_gallery_id is None
    assert client_db.get(GalleryMembershipNotificationOutbox, notice.id).tenant_id == owner.id
    assert client_db.get(AssetFileCleanup, cleanup.id).tenant_id == owner.id


@pytest.mark.parametrize("kind", ["challenge", "session"])
def test_identidade_cliente_sem_contexto_recusada(client_db, kind):
    if kind == "challenge":
        table = AuthChallenge.__table__
        values = {"kind": "client_otp", "secret_hash": "synthetic-hash", "expires_at": now() + timedelta(minutes=1)}
    else:
        table = AuthSession.__table__
        values = {"role": "client", "token_hash": "synthetic-hash", "subject_id": uuid4(),
                      "expires_at": now() + timedelta(minutes=1)}
    with pytest.raises(IntegrityError):
        client_db.execute(table.insert().values(**values))


@pytest.mark.parametrize("kind", ["lifecycle", "capability", "pix_session"])
def test_ator_e_sessao_sensivel_exigem_mesmo_dono(client_db, graph, kind):
    first, second = graph
    if kind == "lifecycle":
        table = GalleryLifecycleOperation.__table__
        values = {"operation_type": "delete_parent_gallery", "target_parent_gallery_id": first["parent"].id,
                  "actor_admin_id": second["admin"].id, "idempotency_key": "synthetic-lifecycle"}
    elif kind == "capability":
        table = GalleryAccessCapability.__table__
        values = {"parent_gallery_id": first["parent"].id, "actor_admin_id": second["admin"].id,
                  "scope": "public_gallery", "token_hash": "a" * 64}
    else:
        session = AuthSession(tenant_id=second["tenant"].id, role="admin", subject_id=second["admin"].id,
                              admin_subject_id=second["admin"].id, token_hash="synthetic-session",
                              expires_at=now() + timedelta(minutes=1))
        client_db.add(session)
        client_db.flush()
        table = AdminSecurityChallenge.__table__
        values = {"purpose": "change_pix_otp", "admin_id": first["admin"].id, "session_id": session.id,
                  "subject_fingerprint": "synthetic", "secret_hash": "synthetic-hash",
                  "expires_at": now() + timedelta(minutes=1)}
    with pytest.raises(IntegrityError) as failure:
        client_db.execute(table.insert().values(tenant_id=first["tenant"].id, **values))
    if client_db.bind.dialect.name == "postgresql":
        assert failure.value.orig.diag.constraint_name.startswith("fk_owner_")
