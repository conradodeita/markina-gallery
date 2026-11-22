"""Perfil operacional e aceite progressivo do fotógrafo."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261104_0099"
down_revision = "20261103_0098"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Onboarding progressivo requer PostgreSQL.")
    op.add_column("admin_user", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        "photographer_business_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False, unique=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False, unique=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("cpf_envelope", sa.String(768), nullable=False),
        sa.Column("cpf_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(full_name) >= 2", name="ck_photographer_profile_name"),
    )
    op.create_index("ix_photographer_business_profile_tenant_id", "photographer_business_profile", ["tenant_id"])
    op.create_index("ix_photographer_business_profile_cpf_fingerprint", "photographer_business_profile", ["cpf_fingerprint"])
    op.create_table(
        "photographer_terms_acceptance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("terms_version", sa.String(80), nullable=False),
        sa.Column("terms_text", sa.Text(), nullable=False),
        sa.Column("terms_sha256", sa.String(64), nullable=False),
        sa.Column("provider_identity", sa.String(240), nullable=False),
        sa.Column("photographer_identity", sa.String(400), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.UniqueConstraint("tenant_id", "terms_version", name="uq_photographer_terms_version"),
    )
    op.create_index("ix_photographer_terms_acceptance_admin_user_id", "photographer_terms_acceptance", ["admin_user_id"])
    op.create_index("ix_photographer_terms_acceptance_tenant_id", "photographer_terms_acceptance", ["tenant_id"])
    op.execute(sa.text("""
        CREATE FUNCTION reject_photographer_terms_change() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'photographer terms history is append-only'; END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER photographer_terms_immutable BEFORE UPDATE OR DELETE ON photographer_terms_acceptance
        FOR EACH ROW EXECUTE FUNCTION reject_photographer_terms_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER photographer_terms_no_truncate BEFORE TRUNCATE ON photographer_terms_acceptance
        FOR EACH STATEMENT EXECUTE FUNCTION reject_photographer_terms_change()
    """))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Onboarding progressivo requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE admin_user, photographer_business_profile, photographer_terms_acceptance "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    for table in ("photographer_business_profile", "photographer_terms_acceptance"):
        if bind.scalar(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)")):
            raise RuntimeError(f"Preserve dados de {table}: rollback recusado.")
    op.drop_table("photographer_terms_acceptance")
    op.execute(sa.text("DROP FUNCTION reject_photographer_terms_change()"))
    op.drop_table("photographer_business_profile")
    op.drop_column("admin_user", "totp_enabled")
