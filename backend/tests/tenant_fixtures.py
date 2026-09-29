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
