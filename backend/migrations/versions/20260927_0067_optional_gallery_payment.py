"""Seleção com cobrança externa, preservando cobrança e pedidos existentes."""

import sqlalchemy as sa
from alembic import op

revision = "20260927_0067"
down_revision = "20260927_0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parent_gallery", sa.Column(
        "payment_required", sa.Boolean(), nullable=False, server_default=sa.true(),
    ))
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        table = sa.Table("sale_order", sa.MetaData(), autoload_with=bind)
        has_payment_constraint = False
        for constraint in list(table.constraints):
            if isinstance(constraint, sa.CheckConstraint) and "payment_status IN" in str(constraint.sqltext):
                constraint.name = "ck_sale_order_payment_status"
                has_payment_constraint = True
        with op.batch_alter_table("sale_order", copy_from=table, recreate="always") as batch:
            batch.add_column(sa.Column(
                "payment_required_snapshot", sa.Boolean(), nullable=False, server_default=sa.true(),
            ))
            if has_payment_constraint:
                batch.drop_constraint("ck_sale_order_payment_status", type_="check")
            batch.create_check_constraint("ck_sale_order_payment_status",
                "payment_status IN ('pending', 'confirmed', 'cancelled', 'not_required')")
    else:
        constraints = sa.inspect(bind).get_check_constraints("sale_order")
        existing = next(item["name"] for item in constraints if "payment_status" in item["sqltext"])
        op.add_column("sale_order", sa.Column(
            "payment_required_snapshot", sa.Boolean(), nullable=False, server_default=sa.true(),
        ))
        op.drop_constraint(existing, "sale_order", type_="check")
        op.create_check_constraint("ck_sale_order_payment_status", "sale_order",
            "payment_status IN ('pending', 'confirmed', 'cancelled', 'not_required')")


def downgrade() -> None:
    bind = op.get_bind()
    external_gallery = bind.execute(sa.text(
        "SELECT id FROM parent_gallery WHERE payment_required = false LIMIT 1"
    )).first()
    external_order = bind.execute(sa.text(
        "SELECT id FROM sale_order WHERE payment_required_snapshot = false "
        "OR payment_status = 'not_required' LIMIT 1"
    )).first()
    if external_gallery or external_order:
        raise RuntimeError("Rollback exige inventário de seleções sem cobrança; downgrade com dados externos recusado.")
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_constraint("ck_sale_order_payment_status", type_="check")
        batch.create_check_constraint("ck_sale_order_payment_status",
            "payment_status IN ('pending', 'confirmed', 'cancelled')")
        batch.drop_column("payment_required_snapshot")
    with op.batch_alter_table("parent_gallery") as batch:
        batch.drop_column("payment_required")
