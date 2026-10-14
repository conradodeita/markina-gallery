"""PIX agrupado aditivo; nenhum pedido legado é recombinado."""

import sqlalchemy as sa
from alembic import op

revision = "20260920_0058"
down_revision = "20260919_0057"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_group",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("pix_copy_paste_snapshot", sa.Text(), nullable=False),
        sa.Column("pix_instructions_snapshot", sa.Text()),
        sa.Column("pix_configuration_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("id", "client_id", name="uq_payment_group_owner"),
        sa.CheckConstraint(
            "state IN ('draft', 'reported', 'confirmed', 'refused')", name="ck_payment_group_state"
        ),
        sa.CheckConstraint("total_cents >= 0", name="ck_payment_group_total"),
    )
    op.create_index("ix_payment_group_client_id", "payment_group", ["client_id"])
    op.create_index(
        "uq_payment_group_draft",
        "payment_group",
        ["client_id"],
        unique=True,
        sqlite_where=sa.text("state = 'draft'"),
        postgresql_where=sa.text("state = 'draft'"),
    )
    for table, constraint in (
        ("sale_order", "fk_sale_order_payment_group_owner"),
        ("payment_communication", "fk_payment_communication_group_owner"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("payment_group_id", sa.Uuid()))
            batch.create_foreign_key(
                constraint, "payment_group", ["payment_group_id", "client_id"], ["id", "client_id"]
            )
            if table == "sale_order":
                batch.create_index("ix_sale_order_payment_group_id", ["payment_group_id"])
            else:
                batch.create_unique_constraint(
                    "uq_payment_communication_group", ["payment_group_id"]
                )


def downgrade():
    # Nunca apagar agrupamentos financeiros existentes para retornar a código antigo.
    if op.get_bind().execute(sa.text("SELECT count(*) FROM payment_group")).scalar():
        raise RuntimeError("Há pagamentos agrupados; use uma versão de aplicação compatível.")
    for table, constraint in (
        ("payment_communication", "fk_payment_communication_group_owner"),
        ("sale_order", "fk_sale_order_payment_group_owner"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(constraint, type_="foreignkey")
            if table == "sale_order":
                batch.drop_index("ix_sale_order_payment_group_id")
            else:
                batch.drop_constraint("uq_payment_communication_group", type_="unique")
            batch.drop_column("payment_group_id")
    op.drop_table("payment_group")
