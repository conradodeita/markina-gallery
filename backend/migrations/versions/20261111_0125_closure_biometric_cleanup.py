"""Limpeza biométrica verificada no fechamento do tenant."""
import sqlalchemy as sa
from alembic import op

revision = "20261111_0125"
down_revision = "20261110_0124"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenant_closure_request",
        sa.Column("biometric_cleanup_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_closure_request",
        sa.Column("biometric_cleanup_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_tenant_closure_biometric_cleanup_order",
        "tenant_closure_request",
        "biometric_cleanup_completed_at IS NULL OR biometric_cleanup_started_at IS NOT NULL",
    )
    op.create_table(
        "facial_search_consent_proof",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_search_request_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("authorization_method", sa.String(length=32), nullable=False),
        sa.Column("consent_version", sa.String(length=80), nullable=True),
        sa.Column("legal_notice_version", sa.String(length=80), nullable=False),
        sa.Column("subject_declaration", sa.String(length=16), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "authorization_method IN ('legacy', 'explicit_consent', 'direct_region')",
            name="ck_facial_consent_proof_method",
        ),
        sa.CheckConstraint(
            "subject_declaration IS NULL OR subject_declaration IN ('adult', 'minor', 'conditional')",
            name="ck_facial_consent_proof_subject",
        ),
        sa.CheckConstraint(
            "consent_version IS NOT NULL OR authorization_method IN ('legacy', 'direct_region')",
            name="ck_facial_consent_proof_consent_method",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "source_search_request_id",
            name="uq_facial_consent_proof_request",
        ),
    )
    op.create_index(
        "ix_facial_search_consent_proof_tenant_id",
        "facial_search_consent_proof",
        ["tenant_id"],
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Cleanup biométrico de encerramento requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE facial_search_consent_proof, tenant_closure_request "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM facial_search_consent_proof)")):
        raise RuntimeError("Preserve os comprovantes mínimos de consentimento facial; downgrade recusado.")
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM tenant_closure_request "
        "WHERE biometric_cleanup_started_at IS NOT NULL OR biometric_cleanup_completed_at IS NOT NULL)"
    )):
        raise RuntimeError("Preserve o estado de limpeza biométrica do encerramento; downgrade recusado.")
    op.drop_index("ix_facial_search_consent_proof_tenant_id", table_name="facial_search_consent_proof")
    op.drop_table("facial_search_consent_proof")
    op.drop_constraint(
        "ck_tenant_closure_biometric_cleanup_order",
        "tenant_closure_request",
        type_="check",
    )
    op.drop_column("tenant_closure_request", "biometric_cleanup_completed_at")
    op.drop_column("tenant_closure_request", "biometric_cleanup_started_at")
