"""Rascunho owner-only e versões imutáveis dos Termos do fotógrafo."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0110"
down_revision = "20261107_0109"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Versionamento dos Termos requer PostgreSQL.")
    op.alter_column("photographer_terms_acceptance", "provider_identity",
                    existing_type=sa.String(240), type_=sa.String(520), existing_nullable=False)
    op.alter_column("photographer_terms_acceptance", "photographer_identity",
                    existing_type=sa.String(400), type_=sa.String(600), existing_nullable=False)
    op.create_table(
        "photographer_terms_draft",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Uuid(), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("provider_legal_name", sa.String(160), nullable=True),
        sa.Column("provider_contact_email", sa.String(320), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_photographer_terms_draft_singleton"),
        sa.CheckConstraint("length(template_text) BETWEEN 1 AND 50000", name="ck_photographer_terms_draft_length"),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["admin_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "photographer_terms_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("terms_version", sa.String(80), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("template_sha256", sa.String(64), nullable=False),
        sa.Column("provider_legal_name", sa.String(160), nullable=False),
        sa.Column("provider_contact_email", sa.String(320), nullable=False),
        sa.Column("published_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(template_sha256) = 64", name="ck_photographer_terms_template_sha256"),
        sa.CheckConstraint("length(template_text) BETWEEN 1 AND 50000", name="ck_photographer_terms_template_length"),
        sa.ForeignKeyConstraint(["published_by_admin_id"], ["admin_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_number", name="uq_photographer_terms_version_number"),
        sa.UniqueConstraint("terms_version", name="uq_photographer_terms_published_version"),
    )
    op.execute(sa.text("""
        CREATE FUNCTION reject_photographer_terms_version_change() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'published photographer terms are append-only'; END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER photographer_terms_version_immutable BEFORE UPDATE OR DELETE ON photographer_terms_version
        FOR EACH ROW EXECUTE FUNCTION reject_photographer_terms_version_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER photographer_terms_version_no_truncate BEFORE TRUNCATE ON photographer_terms_version
        FOR EACH STATEMENT EXECUTE FUNCTION reject_photographer_terms_version_change()
    """))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Versionamento dos Termos requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photographer_terms_acceptance, photographer_terms_draft, "
        "photographer_terms_version IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    for table in ("photographer_terms_version", "photographer_terms_draft"):
        if bind.scalar(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)")):
            raise RuntimeError(f"Preserve dados de {table}: rollback recusado.")
    if bind.scalar(sa.text("""
        SELECT EXISTS(SELECT 1 FROM photographer_terms_acceptance
                      WHERE length(provider_identity) > 240 OR length(photographer_identity) > 400)
    """)):
        raise RuntimeError("Preserve protocolos com identidade extensa: rollback recusado.")
    op.drop_table("photographer_terms_version")
    op.execute(sa.text("DROP FUNCTION reject_photographer_terms_version_change()"))
    op.drop_table("photographer_terms_draft")
    op.alter_column("photographer_terms_acceptance", "photographer_identity",
                    existing_type=sa.String(600), type_=sa.String(400), existing_nullable=False)
    op.alter_column("photographer_terms_acceptance", "provider_identity",
                    existing_type=sa.String(520), type_=sa.String(240), existing_nullable=False)
