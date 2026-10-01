"""Propriedade explícita nos dados sintéticos das suítes anteriores à fundação."""

from uuid import UUID

import sqlalchemy as sa

from app.auth import AdminUser, TenantAdmin

FIXTURE_TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
# Ciclos antigos não atravessam a barreira de propriedade 0069 com dados.
# A cadeia completa e sua recusa de downgrade são ensaiadas em test_tenant_migration.
LEGACY_SCHEMA_HEAD = "20260928_0068"


def fixture_admin(admin: AdminUser) -> AdminUser:
    admin.tenant_memberships.append(TenantAdmin(tenant_id=FIXTURE_TENANT_ID))
    return admin


def insert_legacy_model(connection, entity, **values):
    """Insere somente colunas existentes no schema histórico do ensaio."""
    table = sa.Table(entity.__tablename__, sa.MetaData(), autoload_with=connection)
    data = {}
    for column in table.columns:
        if column.name in values:
            data[column.name] = values[column.name]
        elif not column.nullable and column.default is None and column.server_default is None:
            default = entity.__table__.c[column.name].default
            if default is not None:
                data[column.name] = default.arg(None) if default.is_callable else default.arg
    identifier = data.get("id")
    if connection.dialect.name == "sqlite":
        data = {key: value.hex if isinstance(value, UUID) else value for key, value in data.items()}
    connection.execute(table.insert().values(**data))
    return identifier


def fixture_session(*, role, subject_id, tenant_id=FIXTURE_TENANT_ID, **values):
    """Sessão de teste explícita, com um único UUID de sujeito tipado."""
    from app.auth import AuthSession

    return AuthSession(role=role, subject_id=subject_id, tenant_id=tenant_id,
        client_subject_id=subject_id if role == "client" else None,
        admin_subject_id=subject_id if role == "admin" else None, **values)


def fixture_access(*, client_id, gallery_id, gallery_type="private", tenant_id=FIXTURE_TENANT_ID, **values):
    from app.auth import GalleryAccess

    return GalleryAccess(client_id=client_id, gallery_id=gallery_id,
        tenant_id=tenant_id, parent_gallery_id=gallery_id if gallery_type == "public" else None,
        derived_gallery_id=gallery_id if gallery_type == "private" else None, **values)


def fixture_client_cookie(browser, phone, *, session_factory=None):
    from fastapi import Response

    from app.auth import Client, Role, SessionLocal, create_session, normalize_e164

    with (session_factory or SessionLocal)() as db:
        person = db.scalar(sa.select(Client).where(Client.tenant_id == FIXTURE_TENANT_ID,
                                                  Client.phone_e164 == normalize_e164(phone)))
        assert person is not None
        cookie = create_session(db, Response(), Role.CLIENT, person.id, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    browser.cookies.set("markina_session", cookie)
