"""Constraints reais de proprietário; sem atribuição automática ou filtros de consulta.

Chamado após declarar os modelos, antes de usar o metadata. As mesmas regras
servem ao DDL dos testes e ao inventário de constraints da migration.
"""

from hashlib import sha256

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, MetaData, UniqueConstraint

# Infraestrutura técnica não contém configuração comercial de um fotógrafo.
SHARED_TABLES = frozenset({
    "tenant", "admin_user", "admin_action_token", "email_delivery", "email_delivery_attempt",
    "installation_operator",
})
CONTEXTUAL_TABLES = frozenset({
    "admin_security_challenge", "auth_challenge", "auth_session", "audit_event",
})
SINGLETON_TABLES = frozenset({"branding_settings", "global_pix_settings"})
# Um caminho físico ou capacidade opaca não pode representar dois proprietários.
GLOBALLY_UNIQUE_FIELDS = frozenset({
    "storage_key", "relative_path", "preview_storage_key", "delivery_storage_key", "token_hash",
})


def constraint_name(prefix: str, *parts: str) -> str:
    raw = "_".join((prefix, *parts))
    if len(raw) <= 63:
        return raw
    return raw[:54] + "_" + sha256(raw.encode()).hexdigest()[:8]


def ensure_unique(table, columns) -> None:
    names = tuple(columns)
    existing = [tuple(column.name for column in table.primary_key.columns)]
    existing += [tuple(column.name for column in constraint.columns)
                 for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
    if names not in existing:
        table.append_constraint(UniqueConstraint(
            *names, name=constraint_name("uq_owner", table.name, *names),
        ))


def add_owner_fk(table, columns, target, target_columns) -> None:
    local = tuple(columns)
    remote = tuple(target_columns)
    signature = (local, tuple(f"{target.name}.{name}" for name in remote))
    for existing in table.foreign_key_constraints:
        found = (
            tuple(item.parent.name for item in existing.elements),
            tuple(item.target_fullname for item in existing.elements),
        )
        if found == signature:
            return
    ensure_unique(target, remote)
    # NO ACTION verifica ao fim da instrução; a FK original mantém seu CASCADE/
    # SET NULL apenas no vínculo, conservando tenant_id em registros históricos.
    table.append_constraint(ForeignKeyConstraint(
        local, [f"{target.name}.{name}" for name in remote],
        name=constraint_name("fk_owner", table.name, *local, target.name),
    ))


def apply_ownership_constraints(metadata: MetaData) -> None:
    if metadata.info.get("ownership_constraints_applied"):
        return
    tables = list(metadata.tables.values())
    referenced_keys = {
        (foreign_key.referred_table.name, tuple(item.column.name for item in foreign_key.elements))
        for table in tables for foreign_key in table.foreign_key_constraints
    }
    for table in tables:
        if table.name in SHARED_TABLES:
            continue
        if "tenant_id" not in table.c:
            raise ValueError(f"Tabela sem classificação de proprietário: {table.name}")
        # Escopar unicidade natural; UUIDs PK e caminhos/capacidades seguem únicos.
        for constraint in list(table.constraints):
            if not isinstance(constraint, UniqueConstraint):
                continue
            names = tuple(column.name for column in constraint.columns)
            if "tenant_id" in names or GLOBALLY_UNIQUE_FIELDS.intersection(names):
                continue
            # Candidate keys referenciadas permanecem disponíveis às FKs
            # antigas. A nova FK recebe chave adicional com owner; chaves
            # naturais não referenciadas passam ao escopo da conta.
            if (table.name, names) in referenced_keys:
                continue
            table.constraints.remove(constraint)
            table.append_constraint(UniqueConstraint(
                "tenant_id", *names,
                name=constraint.name or constraint_name("uq_scope", table.name, *names),
                deferrable=constraint.deferrable, initially=constraint.initially,
            ))
        for index in list(table.indexes):
            names = tuple(column.name for column in index.columns)
            if not index.unique or "tenant_id" in names or GLOBALLY_UNIQUE_FIELDS.intersection(names):
                continue
            if (table.name, names) in referenced_keys:
                continue
            table.indexes.remove(index)
            Index(index.name, table.c.tenant_id, *index.expressions, unique=True,
                  **dict(index.dialect_kwargs))
        if "id" in table.c:
            ensure_unique(table, ("id", "tenant_id"))
        if table.name in SINGLETON_TABLES:
            ensure_unique(table, ("tenant_id",))

    for table in tables:
        if table.name in SHARED_TABLES or table.name == "tenant_admin":
            continue
        for foreign_key in list(table.foreign_key_constraints):
            target = foreign_key.referred_table
            local = tuple(item.parent.name for item in foreign_key.elements)
            remote = tuple(item.column.name for item in foreign_key.elements)
            # FKs históricas continuam referindo a chave original; escopar sua
            # unicidade natural não pode retirar a candidate key necessária.
            ensure_unique(target, remote)
            if "tenant_id" in local:
                continue
            if target.name == "admin_user" and remote == ("id",):
                add_owner_fk(table, (*local, "tenant_id"), metadata.tables["tenant_admin"],
                             ("admin_user_id", "tenant_id"))
            elif target.name not in SHARED_TABLES and "tenant_id" in target.c:
                add_owner_fk(table, (*local, "tenant_id"), target, (*remote, "tenant_id"))
    add_owner_fk(metadata.tables["notification_event"], ("event_type", "tenant_id"),
                 metadata.tables["notification_setting"], ("event_type", "tenant_id"))
    for table_name in ("gallery_lifecycle_operation", "gallery_access_capability"):
        add_owner_fk(metadata.tables[table_name], ("actor_admin_id", "tenant_id"),
                     metadata.tables["tenant_admin"], ("admin_user_id", "tenant_id"))
    add_owner_fk(metadata.tables["admin_security_challenge"], ("session_id", "tenant_id"),
                 metadata.tables["auth_session"], ("id", "tenant_id"))
    metadata.tables["admin_security_challenge"].append_constraint(CheckConstraint(
        "purpose != 'change_pix_otp' OR tenant_id IS NOT NULL",
        name="ck_admin_challenge_pix_context",
    ))
    metadata.info["ownership_constraints_applied"] = True
