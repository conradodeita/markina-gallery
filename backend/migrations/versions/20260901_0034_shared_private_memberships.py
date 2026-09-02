"""Adiciona membros às galerias privadas compartilhadas.

Revision ID: 20260901_0034
Revises: 20260831_0033
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260901_0034"
down_revision = "20260831_0033"
branch_labels = None
depends_on = None


def _assert_no_owner_conflicts(bind) -> None:
    conflicts = bind.execute(
        sa.text(
            """
            SELECT parent_gallery_id, client_id, COUNT(*) AS total
            FROM derived_gallery
            GROUP BY parent_gallery_id, client_id
            HAVING COUNT(*) > 1
            ORDER BY parent_gallery_id, client_id
            """
        )
    ).all()
    if conflicts:
        preview = ", ".join(
            f"parent={row.parent_gallery_id} client={row.client_id} total={row.total}"
            for row in conflicts[:10]
        )
        raise RuntimeError(
            "Conflito de galerias privadas por origem/cliente; "
            f"o upgrade foi interrompido sem mesclar dados: {preview}"
        )


def _uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _timestamp(value, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if value:
        return datetime.fromisoformat(str(value))
    return fallback


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_owner_conflicts(bind)

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("derived_gallery", recreate="always") as batch_op:
            batch_op.create_unique_constraint(
                "uq_derived_gallery_id_parent",
                ["id", "parent_gallery_id"],
            )
    else:
        op.create_unique_constraint(
            "uq_derived_gallery_id_parent",
            "derived_gallery",
            ["id", "parent_gallery_id"],
        )

    op.create_table(
        "derived_gallery_membership",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("derived_gallery_id", sa.Uuid(), nullable=False),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlinked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "actor_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["derived_gallery_id", "parent_gallery_id"],
            ["derived_gallery.id", "derived_gallery.parent_gallery_id"],
            name="fk_membership_gallery_parent",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "parent_gallery_id",
            "client_id",
            name="uq_membership_parent_client",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'blocked', 'unlinked')",
            name="ck_derived_gallery_membership_status",
        ),
    )
    for column in (
        "derived_gallery_id",
        "parent_gallery_id",
        "client_id",
        "status",
        "actor_admin_id",
    ):
        op.create_index(
            f"ix_derived_gallery_membership_{column}",
            "derived_gallery_membership",
            [column],
        )
    op.create_index(
        "ix_membership_gallery_status",
        "derived_gallery_membership",
        ["derived_gallery_id", "status"],
    )
    op.create_index(
        "ix_membership_client_status",
        "derived_gallery_membership",
        ["client_id", "status"],
    )

    membership = sa.table(
        "derived_gallery_membership",
        sa.column("id", sa.Uuid()),
        sa.column("derived_gallery_id", sa.Uuid()),
        sa.column("parent_gallery_id", sa.Uuid()),
        sa.column("client_id", sa.Uuid()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    instant = datetime.now(UTC)
    galleries = bind.execute(
        sa.text(
            "SELECT id, parent_gallery_id, client_id, created_at FROM derived_gallery"
        )
    ).mappings()
    rows = [
        {
            "id": uuid4(),
            "derived_gallery_id": _uuid(row["id"]),
            "parent_gallery_id": _uuid(row["parent_gallery_id"]),
            "client_id": _uuid(row["client_id"]),
            "status": "active",
            "created_at": _timestamp(row["created_at"], instant),
            "updated_at": instant,
        }
        for row in galleries
    ]
    if rows:
        op.bulk_insert(membership, rows)


def downgrade() -> None:
    op.drop_table("derived_gallery_membership")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("derived_gallery", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_derived_gallery_id_parent", type_="unique")
    else:
        op.drop_constraint(
            "uq_derived_gallery_id_parent",
            "derived_gallery",
            type_="unique",
        )
