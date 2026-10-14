"""Adiciona prova minimizada de representação legal para busca facial infantil.

Revision ID: 20260908_0049
Revises: 20260908_0048
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0049"
down_revision = "20260908_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facial_legal_representation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "client_id",
            sa.Uuid(),
            sa.ForeignKey("client.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_scope_reference", sa.String(length=200), nullable=False),
        sa.Column("authority_kind", sa.String(length=24), nullable=False),
        sa.Column("verification_method", sa.String(length=32), nullable=False),
        sa.Column("terms_version", sa.String(length=80), nullable=False),
        sa.Column("evidence_reference", sa.String(length=200), nullable=False),
        sa.Column(
            "verified_by_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_facial_legal_representation_status",
        ),
        sa.CheckConstraint(
            "authority_kind IN ('parent', 'legal_guardian', 'court_order')",
            name="ck_facial_legal_representation_authority",
        ),
        sa.CheckConstraint(
            "verification_method IN ('admin_attestation', 'trusted_provider')",
            name="ck_facial_legal_representation_verification",
        ),
        sa.CheckConstraint(
            "expires_at > valid_from",
            name="ck_facial_legal_representation_validity",
        ),
    )
    op.create_index(
        "ix_facial_legal_representation_client_id",
        "facial_legal_representation",
        ["client_id"],
    )
    op.create_index(
        "ix_facial_legal_representation_parent_gallery_id",
        "facial_legal_representation",
        ["parent_gallery_id"],
    )
    op.create_index(
        "ix_facial_legal_representation_verified_by_admin_id",
        "facial_legal_representation",
        ["verified_by_admin_id"],
    )
    op.create_index(
        "ix_facial_legal_representation_status",
        "facial_legal_representation",
        ["status"],
    )
    op.create_index(
        "ix_facial_legal_representation_expires_at",
        "facial_legal_representation",
        ["expires_at"],
    )
    op.create_index(
        "ix_facial_representation_scope_validity",
        "facial_legal_representation",
        ["client_id", "parent_gallery_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_table("facial_legal_representation")
