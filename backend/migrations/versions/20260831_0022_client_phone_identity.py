"""Reconcilia telefone canônico com identidades ativas verificadas.

Revision ID: 20260831_0022
Revises: 20260831_0021
"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260831_0022"
down_revision = "20260831_0021"
branch_labels = None
depends_on = None

SQLITE_NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"}


def _reconcile_legacy_phones(bind) -> None:
    mismatch = bind.execute(
        sa.text(
            """
            SELECT cp.id
            FROM client_phone cp
            JOIN client c ON c.id = cp.client_id
            WHERE cp.active = :active AND cp.phone_e164 <> c.phone_e164
            LIMIT 1
            """
        ),
        {"active": True},
    ).first()
    if mismatch:
        raise RuntimeError(
            "Telefone ativo legado diverge do canônico; reconcilie o cadastro antes da migration."
        )

    clients = bind.execute(
        sa.text("SELECT id, phone_e164 FROM client ORDER BY id")
    ).all()
    for client_id, phone_e164 in clients:
        active = bind.execute(
            sa.text(
                """
                SELECT id, verified_at
                FROM client_phone
                WHERE client_id = :client_id AND phone_e164 = :phone AND active = :active
                """
            ),
            {"client_id": client_id, "phone": phone_e164, "active": True},
        ).first()
        if active:
            if active.verified_at is None:
                bind.execute(
                    sa.text(
                        "UPDATE client_phone SET verified_at = CURRENT_TIMESTAMP WHERE id = :id"
                    ),
                    {"id": active.id},
                )
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO client_phone
                    (id, client_id, phone_e164, active, verified_at, created_at, retired_at)
                VALUES
                    (:id, :client_id, :phone, :active, CURRENT_TIMESTAMP,
                     CURRENT_TIMESTAMP, NULL)
                """
            ),
            {
                "id": str(uuid4()),
                "client_id": client_id,
                "phone": phone_e164,
                "active": True,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    _reconcile_legacy_phones(bind)

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "client_phone",
            recreate="always",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint("uq_client_phone_active", type_="unique")
    else:
        op.drop_constraint("uq_client_phone_active", "client_phone", type_="unique")

    op.create_index(
        "uq_client_phone_active_verified",
        "client_phone",
        ["phone_e164"],
        unique=True,
        sqlite_where=sa.text("active = 1 AND verified_at IS NOT NULL"),
        postgresql_where=sa.text("active AND verified_at IS NOT NULL"),
    )
    op.create_index(
        "uq_client_phone_one_active_per_client",
        "client_phone",
        ["client_id"],
        unique=True,
        sqlite_where=sa.text("active = 1"),
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    duplicate_history = bind.execute(
        sa.text(
            """
            SELECT phone_e164, active, COUNT(*) AS quantity
            FROM client_phone
            GROUP BY phone_e164, active
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_history:
        raise RuntimeError(
            "O downgrade não representa múltiplos históricos inativos do mesmo telefone."
        )

    op.drop_index(
        "uq_client_phone_one_active_per_client", table_name="client_phone"
    )
    op.drop_index("uq_client_phone_active_verified", table_name="client_phone")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "client_phone",
            recreate="always",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.create_unique_constraint(
                "uq_client_phone_active", ["phone_e164", "active"]
            )
    else:
        op.create_unique_constraint(
            "uq_client_phone_active",
            "client_phone",
            ["phone_e164", "active"],
        )
