"""Desafios limitados para comprovar identidade antes da reabertura tardia."""

import sqlalchemy as sa
from alembic import op

revision = "20261110_0121"
down_revision = "20261110_0120"
branch_labels = None
depends_on = None

_TABLE = "tenant_closure_identity_verification"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("closure_request_id", sa.Uuid(), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("current_name_envelope", sa.Text(), nullable=True),
        sa.Column("current_email_envelope", sa.Text(), nullable=True),
        sa.Column("email_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("code_digest", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_closure_identity_request"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["closure_request_id", "tenant_id"],
            ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
            name="fk_closure_identity_closure",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "admin_user_id"],
            ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_closure_identity_membership",
        ),
        sa.CheckConstraint(
            "state IN ('email_pending', 'verified', 'locked', 'expired', 'superseded')",
            name="ck_closure_identity_state",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 5", name="ck_closure_identity_attempts"),
        sa.CheckConstraint(
            "(state = 'verified' AND verified_at IS NOT NULL) OR "
            "(state != 'verified' AND verified_at IS NULL)",
            name="ck_closure_identity_verified_at",
        ),
        sa.CheckConstraint(
            "(state = 'email_pending' AND current_name_envelope IS NOT NULL "
            "AND current_email_envelope IS NOT NULL AND email_fingerprint IS NOT NULL "
            "AND code_digest IS NOT NULL) OR "
            "(state != 'email_pending' AND current_name_envelope IS NULL "
            "AND current_email_envelope IS NULL AND email_fingerprint IS NULL "
            "AND code_digest IS NULL)",
            name="ck_closure_identity_pending_material",
        ),
    )
    op.create_index("ix_tenant_closure_identity_verification_tenant_id", _TABLE, ["tenant_id"])
    op.create_index("ix_tenant_closure_identity_verification_expires_at", _TABLE, ["expires_at"])
    op.create_index(
        "uq_closure_identity_pending_tenant",
        _TABLE,
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("state = 'email_pending'"),
        sqlite_where=sa.text("state = 'email_pending'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Verificação de identidade requer PostgreSQL.")
    bind.exec_driver_sql(
        f"LOCK TABLE {_TABLE} IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(f"SELECT EXISTS(SELECT 1 FROM {_TABLE})")):
        raise RuntimeError("Preserve o histórico de verificação de identidade para reabertura.")
    op.drop_index("uq_closure_identity_pending_tenant", table_name=_TABLE)
    op.drop_index("ix_tenant_closure_identity_verification_expires_at", table_name=_TABLE)
    op.drop_index("ix_tenant_closure_identity_verification_tenant_id", table_name=_TABLE)
    op.drop_table(_TABLE)
