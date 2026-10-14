"""Centraliza configuração herdada na Galeria pública.

Revision ID: 20260831_0030
Revises: 20260831_0029
"""

from collections import defaultdict
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260831_0030"
down_revision = "20260831_0029"
branch_labels = None
depends_on = None


def _legacy_state(bind):
    derived = sa.Table("derived_gallery", sa.MetaData(), autoload_with=bind)
    prices = sa.Table("price_rule", sa.MetaData(), autoload_with=bind)
    pix = sa.Table("pix_checkout_settings", sa.MetaData(), autoload_with=bind)

    derived_rows = list(
        bind.execute(
            sa.select(
                derived.c.id,
                derived.c.parent_gallery_id,
                derived.c.custom_message,
                derived.c.favorites_enabled,
                derived.c.comments_enabled,
            )
        ).mappings()
    )
    parent_by_derived = {
        row["id"]: row["parent_gallery_id"] for row in derived_rows
    }
    private_by_parent = defaultdict(list)
    for row in derived_rows:
        private_by_parent[row["parent_gallery_id"]].append(row)

    price_by_private = defaultdict(list)
    for row in bind.execute(sa.select(prices)).mappings():
        price_by_private[row["derived_gallery_id"]].append(row)
    pix_by_private = {
        row["derived_gallery_id"]: row
        for row in bind.execute(sa.select(pix)).mappings()
    }

    presentation = {}
    parent_prices = {}
    parent_pix = {}
    for parent_id, rows in private_by_parent.items():
        presentation_signatures = {
            (
                row["custom_message"],
                bool(row["favorites_enabled"]),
                bool(row["comments_enabled"]),
            )
            for row in rows
        }
        if len(presentation_signatures) > 1:
            raise RuntimeError(
                "Migration recusada: galerias privadas da mesma Galeria pública "
                "possuem mensagens ou interações divergentes."
            )
        if presentation_signatures:
            presentation[parent_id] = next(iter(presentation_signatures))

        configured_price_sets = []
        for row in rows:
            rules = price_by_private.get(row["id"], [])
            if rules:
                signature = tuple(
                    sorted(
                        (
                            rule["minimum_quantity"],
                            rule["maximum_quantity"],
                            rule["unit_price_cents"],
                        )
                        for rule in rules
                    )
                )
                configured_price_sets.append((signature, rules))
        if len({item[0] for item in configured_price_sets}) > 1:
            raise RuntimeError(
                "Migration recusada: galerias privadas da mesma Galeria pública "
                "possuem faixas de preço divergentes."
            )
        if configured_price_sets:
            parent_prices[parent_id] = configured_price_sets[0][1]

        configured_pix = [
            pix_by_private[row["id"]]
            for row in rows
            if row["id"] in pix_by_private
        ]
        pix_signatures = {
            (
                item["copy_paste"],
                item["qr_code_payload"],
                item["instructions"],
            )
            for item in configured_pix
        }
        if len(pix_signatures) > 1:
            raise RuntimeError(
                "Migration recusada: galerias privadas da mesma Galeria pública "
                "possuem configurações PIX divergentes."
            )
        if configured_pix:
            parent_pix[parent_id] = configured_pix[0]

    return presentation, parent_prices, parent_pix, parent_by_derived


def _create_parent_commercial_tables() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "price_rule_parent_new",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "parent_gallery_id",
            uuid,
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("maximum_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id", "minimum_quantity"),
        sa.CheckConstraint("minimum_quantity >= 1"),
        sa.CheckConstraint(
            "maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity"
        ),
        sa.CheckConstraint("unit_price_cents >= 0"),
    )
    op.create_index(
        "ix_price_rule_parent_gallery_id",
        "price_rule_parent_new",
        ["parent_gallery_id"],
    )
    op.create_table(
        "pix_checkout_settings_parent_new",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "parent_gallery_id",
            uuid,
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("copy_paste", sa.Text(), nullable=True),
        sa.Column("qr_code_payload", sa.Text(), nullable=True),
        sa.Column("instructions", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id"),
    )
    op.create_index(
        "ix_pix_checkout_settings_parent_gallery_id",
        "pix_checkout_settings_parent_new",
        ["parent_gallery_id"],
    )


def upgrade() -> None:
    bind = op.get_bind()
    presentation, parent_prices, parent_pix, _ = _legacy_state(bind)

    op.add_column("parent_gallery", sa.Column("sales_message", sa.Text(), nullable=True))
    op.add_column(
        "parent_gallery",
        sa.Column("selection_duration_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "parent_gallery",
        sa.Column(
            "favorites_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "parent_gallery",
        sa.Column(
            "comments_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.create_check_constraint(
            "ck_parent_gallery_selection_duration_days",
            "selection_duration_days IS NULL OR "
            "selection_duration_days BETWEEN 1 AND 3650",
        )

    parent = sa.Table("parent_gallery", sa.MetaData(), autoload_with=bind)
    for parent_id, values in presentation.items():
        bind.execute(
            parent.update()
            .where(parent.c.id == parent_id)
            .values(
                sales_message=values[0],
                favorites_enabled=values[1],
                comments_enabled=values[2],
            )
        )

    _create_parent_commercial_tables()
    price_new = sa.Table(
        "price_rule_parent_new", sa.MetaData(), autoload_with=bind
    )
    pix_new = sa.Table(
        "pix_checkout_settings_parent_new", sa.MetaData(), autoload_with=bind
    )
    for parent_id, rules in parent_prices.items():
        for rule in rules:
            bind.execute(
                price_new.insert().values(
                    id=uuid4(),
                    parent_gallery_id=parent_id,
                    minimum_quantity=rule["minimum_quantity"],
                    maximum_quantity=rule["maximum_quantity"],
                    unit_price_cents=rule["unit_price_cents"],
                    created_at=rule["created_at"],
                    updated_at=rule["updated_at"],
                )
            )
    for parent_id, settings in parent_pix.items():
        bind.execute(
            pix_new.insert().values(
                id=uuid4(),
                parent_gallery_id=parent_id,
                copy_paste=settings["copy_paste"],
                qr_code_payload=settings["qr_code_payload"],
                instructions=settings["instructions"],
                updated_at=settings["updated_at"],
            )
        )

    op.drop_table("pix_checkout_settings")
    op.drop_table("price_rule")
    op.rename_table("price_rule_parent_new", "price_rule")
    op.rename_table("pix_checkout_settings_parent_new", "pix_checkout_settings")


def _create_derived_commercial_tables() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "price_rule_derived_new",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "derived_gallery_id",
            uuid,
            sa.ForeignKey("derived_gallery.id"),
            nullable=False,
        ),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("maximum_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id", "minimum_quantity"),
        sa.CheckConstraint("minimum_quantity >= 1"),
        sa.CheckConstraint(
            "maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity"
        ),
        sa.CheckConstraint("unit_price_cents >= 0"),
    )
    op.create_index(
        "ix_price_rule_derived_gallery_id",
        "price_rule_derived_new",
        ["derived_gallery_id"],
    )
    op.create_table(
        "pix_checkout_settings_derived_new",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "derived_gallery_id",
            uuid,
            sa.ForeignKey("derived_gallery.id"),
            nullable=False,
        ),
        sa.Column("copy_paste", sa.Text(), nullable=True),
        sa.Column("qr_code_payload", sa.Text(), nullable=True),
        sa.Column("instructions", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id"),
    )
    op.create_index(
        "ix_pix_checkout_settings_derived_gallery_id",
        "pix_checkout_settings_derived_new",
        ["derived_gallery_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    parent = sa.Table("parent_gallery", sa.MetaData(), autoload_with=bind)
    derived = sa.Table("derived_gallery", sa.MetaData(), autoload_with=bind)
    prices = sa.Table("price_rule", sa.MetaData(), autoload_with=bind)
    pix = sa.Table("pix_checkout_settings", sa.MetaData(), autoload_with=bind)
    parent_rows = {
        row["id"]: row for row in bind.execute(sa.select(parent)).mappings()
    }
    derived_rows = list(
        bind.execute(sa.select(derived.c.id, derived.c.parent_gallery_id)).mappings()
    )
    prices_by_parent = defaultdict(list)
    for row in bind.execute(sa.select(prices)).mappings():
        prices_by_parent[row["parent_gallery_id"]].append(row)
    pix_by_parent = {
        row["parent_gallery_id"]: row
        for row in bind.execute(sa.select(pix)).mappings()
    }

    for row in derived_rows:
        source = parent_rows[row["parent_gallery_id"]]
        bind.execute(
            derived.update()
            .where(derived.c.id == row["id"])
            .values(
                custom_message=source["sales_message"],
                favorites_enabled=source["favorites_enabled"],
                comments_enabled=source["comments_enabled"],
            )
        )

    _create_derived_commercial_tables()
    price_new = sa.Table(
        "price_rule_derived_new", sa.MetaData(), autoload_with=bind
    )
    pix_new = sa.Table(
        "pix_checkout_settings_derived_new", sa.MetaData(), autoload_with=bind
    )
    for row in derived_rows:
        for rule in prices_by_parent.get(row["parent_gallery_id"], []):
            bind.execute(
                price_new.insert().values(
                    id=uuid4(),
                    derived_gallery_id=row["id"],
                    minimum_quantity=rule["minimum_quantity"],
                    maximum_quantity=rule["maximum_quantity"],
                    unit_price_cents=rule["unit_price_cents"],
                    created_at=rule["created_at"],
                    updated_at=rule["updated_at"],
                )
            )
        settings = pix_by_parent.get(row["parent_gallery_id"])
        if settings:
            bind.execute(
                pix_new.insert().values(
                    id=uuid4(),
                    derived_gallery_id=row["id"],
                    copy_paste=settings["copy_paste"],
                    qr_code_payload=settings["qr_code_payload"],
                    instructions=settings["instructions"],
                    updated_at=settings["updated_at"],
                )
            )

    op.drop_table("pix_checkout_settings")
    op.drop_table("price_rule")
    op.rename_table("price_rule_derived_new", "price_rule")
    op.rename_table("pix_checkout_settings_derived_new", "pix_checkout_settings")

    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.drop_constraint(
            "ck_parent_gallery_selection_duration_days", type_="check"
        )
        batch_op.drop_column("comments_enabled")
        batch_op.drop_column("favorites_enabled")
        batch_op.drop_column("selection_duration_days")
        batch_op.drop_column("sales_message")
