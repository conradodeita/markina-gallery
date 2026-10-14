"""Prepare tenant-owned InfinitePay settings without enabling payments."""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0075"
down_revision = "20261011_0074"
branch_labels = None
depends_on = None

PURPOSES = "'password_recovery_otp', 'change_password_otp', 'change_email_otp', 'change_pix_otp'"


def challenge_constraints(include_credit: bool) -> None:
    bind = op.get_bind()
    table = sa.Table("admin_security_challenge", sa.MetaData(), autoload_with=bind)
    previous = [c for c in table.constraints
                if isinstance(c, sa.CheckConstraint) and c.name == "ck_admin_security_purpose"]
    if len(previous) != 1:
        raise RuntimeError("Contrato de desafios administrativos inesperado; migração recusada.")
    expression = f"purpose IN ({PURPOSES}"
    expression += ", 'change_infinitepay_otp')" if include_credit else ")"
    if bind.dialect.name == "sqlite":
        table.constraints.remove(previous[0])
        for constraint in list(table.constraints):
            if constraint.name == "ck_admin_challenge_infinitepay_context":
                table.constraints.remove(constraint)
        table.append_constraint(sa.CheckConstraint(expression, name="ck_admin_security_purpose"))
        if include_credit:
            table.append_constraint(sa.CheckConstraint(
                "purpose != 'change_infinitepay_otp' OR tenant_id IS NOT NULL",
                name="ck_admin_challenge_infinitepay_context"))
        with op.batch_alter_table(table.name, copy_from=table, recreate="always"):
            pass
    else:
        op.drop_constraint(previous[0].name, table.name, type_="check")
        op.create_check_constraint("ck_admin_security_purpose", table.name, expression)
        if include_credit:
            op.create_check_constraint("ck_admin_challenge_infinitepay_context", table.name,
                                       "purpose != 'change_infinitepay_otp' OR tenant_id IS NOT NULL")
        else:
            op.drop_constraint("ck_admin_challenge_infinitepay_context", table.name, type_="check")


def upgrade() -> None:
    op.create_table(
        "infinitepay_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("handle", sa.String(100), nullable=True),
        sa.Column("verification_profile", sa.String(100), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tenant_id", name="uq_infinitepay_settings_tenant"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_owner_infinitepay_settings_id_tenant_id"),
        sa.ForeignKeyConstraint(["admin_user_id", "tenant_id"],
                                ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"],
                                name="fk_owner_infinitepay_settings_admin_user_id_tenant_id__49447614"),
        sa.CheckConstraint("version >= 0", name="ck_infinitepay_settings_version"),
        sa.CheckConstraint("status IN ('pending', 'inactive', 'active')",
                           name="ck_infinitepay_settings_status"),
        sa.CheckConstraint("status = 'inactive' OR handle IS NOT NULL",
                           name="ck_infinitepay_settings_handle"),
        sa.CheckConstraint("status != 'active' OR (verification_profile IS NOT NULL "
                           "AND verified_at IS NOT NULL)", name="ck_infinitepay_settings_activation"),
    )
    op.create_index("ix_infinitepay_settings_tenant_id", "infinitepay_settings", ["tenant_id"])
    challenge_constraints(True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT COUNT(*) FROM infinitepay_settings")) or bind.scalar(sa.text(
        "SELECT COUNT(*) FROM admin_security_challenge WHERE purpose = 'change_infinitepay_otp'"
    )):
        raise RuntimeError("Downgrade recusado: preserve configurações e desafios InfinitePay auditáveis.")
    challenge_constraints(False)
    op.drop_table("infinitepay_settings")
