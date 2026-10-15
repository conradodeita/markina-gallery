"""Propriedade explícita do legado único, sem alterar acervo ou credenciais."""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260929_0069"
down_revision = "20260928_0068"
branch_labels = None
depends_on = None


def _preflight(bind):
    checks = (
        "SELECT count(*) FROM derived_gallery g LEFT JOIN parent_gallery p "
        "ON p.id=g.parent_gallery_id WHERE p.id IS NULL",
        "SELECT count(*) FROM photo_asset a LEFT JOIN parent_gallery p "
        "ON p.id=a.parent_gallery_id WHERE p.id IS NULL",
        "SELECT count(*) FROM photo_asset a LEFT JOIN derived_gallery g "
        "ON g.id=a.derived_gallery_id WHERE a.derived_gallery_id IS NOT NULL "
        "AND (g.id IS NULL OR g.parent_gallery_id<>a.parent_gallery_id)",
    )
    if any(bind.scalar(sa.text(query)) for query in checks):
        raise RuntimeError("Acervo inconsistente; migração de propriedade interrompida.")


def upgrade():
    bind = op.get_bind()
    _preflight(bind)  # Antes de qualquer DDL, também para o fallback SQLite.
    tenant = op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_tenant_status"),
    )
    membership = op.create_table(
        "tenant_admin",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "admin_user_id", name="uq_tenant_admin"),
    )
    op.create_index("ix_tenant_admin_tenant_id", "tenant_admin", ["tenant_id"])
    op.create_index("ix_tenant_admin_admin_user_id", "tenant_admin", ["admin_user_id"])
    tenant_id, instant = uuid4(), datetime.now(UTC)
    bind.execute(tenant.insert().values(id=tenant_id, status="active", created_at=instant))
    admins = sa.table("admin_user", sa.column("id", sa.Uuid()))
    for admin_id in bind.scalars(sa.select(admins.c.id)):
        bind.execute(membership.insert().values(
            id=uuid4(), tenant_id=tenant_id, admin_user_id=admin_id,
            active=True, created_at=instant,
        ))
    for name in ("parent_gallery", "derived_gallery", "photo_asset"):
        op.add_column(name, sa.Column("tenant_id", sa.Uuid(), nullable=True))
        table = sa.table(name, sa.column("tenant_id", sa.Uuid()))
        bind.execute(table.update().values(tenant_id=tenant_id))
        if bind.scalar(sa.select(sa.func.count()).select_from(table).where(
            table.c.tenant_id.is_(None)
        )):
            raise RuntimeError("Atribuição de propriedade incompleta.")
    with op.batch_alter_table("parent_gallery") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_parent_gallery_tenant", "tenant", ["tenant_id"], ["id"])
        batch.create_unique_constraint("uq_parent_gallery_id_tenant", ["id", "tenant_id"])
        batch.create_index("ix_parent_gallery_tenant_id", ["tenant_id"])
    with op.batch_alter_table("derived_gallery") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_derived_gallery_tenant", "tenant", ["tenant_id"], ["id"])
        batch.create_foreign_key("fk_derived_gallery_parent_tenant", "parent_gallery",
                                 ["parent_gallery_id", "tenant_id"], ["id", "tenant_id"])
        batch.create_unique_constraint("uq_derived_gallery_tenant",
                                       ["id", "parent_gallery_id", "tenant_id"])
        batch.create_index("ix_derived_gallery_tenant_id", ["tenant_id"])
    with op.batch_alter_table("photo_asset") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_photo_asset_tenant", "tenant", ["tenant_id"], ["id"])
        batch.create_foreign_key("fk_photo_asset_parent_tenant", "parent_gallery",
                                 ["parent_gallery_id", "tenant_id"], ["id", "tenant_id"])
        batch.create_foreign_key("fk_photo_asset_private_tenant", "derived_gallery",
                                 ["derived_gallery_id", "parent_gallery_id", "tenant_id"],
                                 ["id", "parent_gallery_id", "tenant_id"])
        batch.create_index("ix_photo_asset_tenant_id", ["tenant_id"])


def downgrade():
    bind = op.get_bind()
    if any(bind.scalar(sa.text(f"SELECT count(*) FROM {name}")) for name in (
        "tenant_admin", "parent_gallery", "derived_gallery", "photo_asset",
    )):
        raise RuntimeError("Há propriedade atribuída. Preserve o schema ao reverter a aplicação.")
    for name, constraints in (
        ("photo_asset", ("fk_photo_asset_private_tenant", "fk_photo_asset_parent_tenant",
                         "fk_photo_asset_tenant")),
        ("derived_gallery", ("fk_derived_gallery_parent_tenant", "fk_derived_gallery_tenant")),
        ("parent_gallery", ("fk_parent_gallery_tenant",)),
    ):
        with op.batch_alter_table(name) as batch:
            for constraint in constraints:
                batch.drop_constraint(constraint, type_="foreignkey")
            if name == "derived_gallery":
                batch.drop_constraint("uq_derived_gallery_tenant", type_="unique")
            if name == "parent_gallery":
                batch.drop_constraint("uq_parent_gallery_id_tenant", type_="unique")
            batch.drop_index(f"ix_{name}_tenant_id")
            batch.drop_column("tenant_id")
    op.drop_table("tenant_admin")
    op.drop_table("tenant")
