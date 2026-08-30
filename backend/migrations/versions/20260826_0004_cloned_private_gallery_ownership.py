"""Adiciona registro de fonte, contatos históricos e visualizações privadas.

Revision ID: 20260826_0004
Revises: 20260826_0003
"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision = "20260826_0004"
down_revision = "20260826_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auth_challenge", sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
    op.create_table(
        "client_phone",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("phone_e164", sa.String(length=16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("phone_e164", "active", name="uq_client_phone_active"),
    )
    op.create_index("ix_client_phone_client_id", "client_phone", ["client_id"])
    op.create_index("ix_client_phone_phone_e164", "client_phone", ["phone_e164"])
    op.create_table(
        "parent_gallery_registration",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_gallery_id", sa.Uuid(), sa.ForeignKey("parent_gallery.id"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id", "client_id", name="uq_parent_gallery_registration"),
    )
    op.create_table(
        "photo_view",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("derived_gallery_id", sa.Uuid(), sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("photo_asset_id", sa.Uuid(), sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id", "client_id", "photo_asset_id", name="uq_photo_view_private"),
    )
    op.add_column("sale_order", sa.Column("client_name_snapshot", sa.String(length=200), nullable=True))
    op.add_column("sale_order", sa.Column("client_phone_snapshot", sa.String(length=16), nullable=True))
    bind = op.get_bind()
    metadata = sa.MetaData()
    client = sa.Table("client", metadata, autoload_with=bind)
    client_phone = sa.Table("client_phone", metadata, autoload_with=bind)
    sale_order = sa.Table("sale_order", metadata, autoload_with=bind)
    for row in bind.execute(sa.select(client.c.id, client.c.phone_e164)):
        bind.execute(client_phone.insert().values(
            id=str(uuid4()), client_id=row.id, phone_e164=row.phone_e164, active=True,
            verified_at=None, created_at=sa.func.current_timestamp(), retired_at=None,
        ))
    bind.execute(
        sale_order.update().values(
            client_name_snapshot=sa.select(client.c.full_name).where(client.c.id == sale_order.c.client_id).scalar_subquery(),
            client_phone_snapshot=sa.select(client.c.phone_e164).where(client.c.id == sale_order.c.client_id).scalar_subquery(),
        )
    )


def downgrade() -> None:
    op.drop_column("sale_order", "client_phone_snapshot")
    op.drop_column("sale_order", "client_name_snapshot")
    op.drop_table("photo_view")
    op.drop_table("parent_gallery_registration")
    op.drop_index("ix_client_phone_phone_e164", table_name="client_phone")
    op.drop_index("ix_client_phone_client_id", table_name="client_phone")
    op.drop_table("client_phone")
    op.drop_column("auth_challenge", "parent_gallery_id")
