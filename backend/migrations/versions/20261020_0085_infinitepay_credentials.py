"""Dedicated encrypted credential versions and immutable payment references."""

import sqlalchemy as sa
from alembic import op

revision = "20261020_0085"
down_revision = "20261017_0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("infinitepay_credential",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("key_id", sa.String(48), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("nonce", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("id", "tenant_id", name="uq_infinitepay_credential_owner"),
        sa.CheckConstraint("(ciphertext IS NOT NULL AND nonce IS NOT NULL AND revoked_at IS NULL) OR "
                           "(ciphertext IS NULL AND nonce IS NULL AND revoked_at IS NOT NULL)",
                           name="ck_infinitepay_credential_envelope"))
    op.create_index("ix_infinitepay_credential_tenant_id", "infinitepay_credential", ["tenant_id"])
    op.add_column("infinitepay_settings", sa.Column("credential_source", sa.String(16),
                  nullable=False, server_default="server_binding"))
    for table, name in (("infinitepay_settings", "fk_infinitepay_settings_credential_owner"),
                        ("provider_payment", "fk_provider_payment_credential_owner")):
        op.add_column(table, sa.Column("credential_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(name, table, "infinitepay_credential", ["credential_id", "tenant_id"],
                              ["id", "tenant_id"])
    op.create_check_constraint("ck_infinitepay_settings_credential_source", "infinitepay_settings",
        "credential_source IN ('server_binding', 'managed') AND "
        "(credential_source != 'server_binding' OR credential_id IS NULL)")


def downgrade() -> None:
    bind = op.get_bind()
    if (bind.scalar(sa.text("SELECT count(*) FROM infinitepay_credential"))
            or bind.scalar(sa.text("SELECT count(*) FROM infinitepay_settings WHERE credential_source = 'managed'"))):
        raise RuntimeError("Downgrade recusado: preserve credenciais e referências financeiras.")
    op.drop_constraint("ck_infinitepay_settings_credential_source", "infinitepay_settings", type_="check")
    for table, name in (("infinitepay_settings", "fk_infinitepay_settings_credential_owner"),
                        ("provider_payment", "fk_provider_payment_credential_owner")):
        op.drop_constraint(name, table, type_="foreignkey")
        op.drop_column(table, "credential_id")
    op.drop_column("infinitepay_settings", "credential_source")
    op.drop_table("infinitepay_credential")
