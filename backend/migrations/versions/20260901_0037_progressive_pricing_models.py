"""Adiciona presets e snapshots de preço progressivo.

Revision ID: 20260901_0037
Revises: 20260901_0036
"""

import sqlalchemy as sa
from alembic import op
from uuid import UUID

revision = "20260901_0037"
down_revision = "20260901_0036"
branch_labels = None
depends_on = None


def _as_uuid(value: object) -> object:
    if isinstance(value, str):
        return UUID(value)
    return value


def upgrade() -> None:
    op.create_table(
        "progressive_pricing_preset",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_progressive_pricing_preset_code"),
        sa.CheckConstraint("version >= 1", name="ck_progressive_pricing_preset_version"),
    )
    op.create_index(
        "ix_progressive_pricing_preset_code",
        "progressive_pricing_preset",
        ["code"],
    )
    op.create_index(
        "ix_progressive_pricing_preset_active",
        "progressive_pricing_preset",
        ["active"],
    )
    op.create_table(
        "progressive_pricing_tier",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "preset_id",
            sa.Uuid(),
            sa.ForeignKey("progressive_pricing_preset.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("maximum_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "preset_id",
            "minimum_quantity",
            name="uq_progressive_pricing_tier_minimum",
        ),
        sa.CheckConstraint("minimum_quantity >= 1", name="ck_progressive_tier_minimum"),
        sa.CheckConstraint(
            "maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity",
            name="ck_progressive_tier_maximum",
        ),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_progressive_tier_price"),
    )
    op.create_index(
        "ix_progressive_pricing_tier_preset_id",
        "progressive_pricing_tier",
        ["preset_id"],
    )

    bind = op.get_bind()
    columns = (
        sa.Column(
            "pricing_mode",
            sa.String(length=24),
            nullable=False,
            server_default="fixed",
        ),
        sa.Column("fixed_unit_price_cents", sa.Integer(), nullable=True),
        sa.Column(
            "progressive_pricing_preset_id",
            sa.Uuid(),
            sa.ForeignKey(
                "progressive_pricing_preset.id",
                name="fk_parent_gallery_progressive_pricing_preset",
            ),
            nullable=True,
        ),
        sa.Column("pricing_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "pricing_review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            for column in columns:
                batch_op.add_column(column)
            batch_op.create_check_constraint(
                "ck_parent_gallery_pricing_mode",
                "pricing_mode IN ('fixed', 'progressive', 'legacy_volume')",
            )
            batch_op.create_check_constraint(
                "ck_parent_gallery_fixed_unit_price",
                "fixed_unit_price_cents IS NULL OR fixed_unit_price_cents >= 0",
            )
    else:
        for column in columns:
            op.add_column("parent_gallery", column)
        op.create_check_constraint(
            "ck_parent_gallery_pricing_mode",
            "parent_gallery",
            "pricing_mode IN ('fixed', 'progressive', 'legacy_volume')",
        )
        op.create_check_constraint(
            "ck_parent_gallery_fixed_unit_price",
            "parent_gallery",
            "fixed_unit_price_cents IS NULL OR fixed_unit_price_cents >= 0",
        )
    op.create_index(
        "ix_parent_gallery_progressive_pricing_preset_id",
        "parent_gallery",
        ["progressive_pricing_preset_id"],
    )

    parent_table = sa.table(
        "parent_gallery",
        sa.column("id", sa.Uuid()),
        sa.column("pricing_mode", sa.String()),
        sa.column("fixed_unit_price_cents", sa.Integer()),
        sa.column("pricing_snapshot", sa.JSON()),
        sa.column("pricing_review_required", sa.Boolean()),
    )
    gallery_ids = bind.execute(sa.text("SELECT id FROM parent_gallery")).scalars()
    for raw_gallery_id in gallery_ids:
        tiers = bind.execute(
            sa.text(
                """
                SELECT minimum_quantity, maximum_quantity, unit_price_cents
                FROM price_rule
                WHERE parent_gallery_id = :gallery_id
                ORDER BY minimum_quantity
                """
            ),
            {"gallery_id": raw_gallery_id},
        ).mappings().all()
        normalized = [
            {
                "minimum_quantity": row["minimum_quantity"],
                "maximum_quantity": row["maximum_quantity"],
                "unit_price_cents": row["unit_price_cents"],
            }
            for row in tiers
        ]
        if len(tiers) == 1 and tiers[0]["minimum_quantity"] == 1:
            values = {
                "pricing_mode": "fixed",
                "fixed_unit_price_cents": tiers[0]["unit_price_cents"],
                "pricing_snapshot": {
                    "mode": "fixed",
                    "unit_price_cents": tiers[0]["unit_price_cents"],
                    "migrated_from": "legacy_single_tier",
                },
                "pricing_review_required": False,
            }
        elif len(tiers) > 1:
            values = {
                "pricing_mode": "legacy_volume",
                "fixed_unit_price_cents": None,
                "pricing_snapshot": {
                    "mode": "legacy_volume",
                    "tiers": normalized,
                },
                "pricing_review_required": True,
            }
        else:
            values = {
                "pricing_mode": "fixed",
                "fixed_unit_price_cents": None,
                "pricing_snapshot": None,
                "pricing_review_required": True,
            }
        bind.execute(
            sa.update(parent_table)
            .where(parent_table.c.id == _as_uuid(raw_gallery_id))
            .values(**values)
        )


def downgrade() -> None:
    op.drop_index(
        "ix_parent_gallery_progressive_pricing_preset_id",
        table_name="parent_gallery",
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_parent_gallery_fixed_unit_price", type_="check")
            batch_op.drop_constraint("ck_parent_gallery_pricing_mode", type_="check")
            batch_op.drop_column("pricing_review_required")
            batch_op.drop_column("pricing_snapshot")
            batch_op.drop_column("progressive_pricing_preset_id")
            batch_op.drop_column("fixed_unit_price_cents")
            batch_op.drop_column("pricing_mode")
    else:
        op.drop_constraint(
            "ck_parent_gallery_fixed_unit_price", "parent_gallery", type_="check"
        )
        op.drop_constraint(
            "ck_parent_gallery_pricing_mode", "parent_gallery", type_="check"
        )
        for column in (
            "pricing_review_required",
            "pricing_snapshot",
            "progressive_pricing_preset_id",
            "fixed_unit_price_cents",
            "pricing_mode",
        ):
            op.drop_column("parent_gallery", column)
    op.drop_table("progressive_pricing_tier")
    op.drop_table("progressive_pricing_preset")
