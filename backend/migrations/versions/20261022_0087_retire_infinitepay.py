"""Retire InfinitePay checkout operations while retaining financial history."""

import sqlalchemy as sa
from alembic import op

revision = "20261022_0087"
down_revision = "20261021_0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Challenges may hold an encrypted InfinitePay key proposal.
    op.execute(sa.text("DELETE FROM admin_security_challenge WHERE purpose = 'change_infinitepay_otp'"))
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        challenge = sa.Table("admin_security_challenge", sa.MetaData(), autoload_with=bind)
        for constraint in list(challenge.constraints):
            if constraint.name in {"ck_admin_security_purpose", "ck_admin_challenge_infinitepay_context"}:
                challenge.constraints.remove(constraint)
        challenge.append_constraint(sa.CheckConstraint(
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp', 'change_pix_otp')",
            name="ck_admin_security_purpose",
        ))
        with op.batch_alter_table("admin_security_challenge", copy_from=challenge, recreate="always"):
            pass
    else:
        op.drop_constraint("ck_admin_security_purpose", "admin_security_challenge", type_="check")
        op.drop_constraint("ck_admin_challenge_infinitepay_context", "admin_security_challenge", type_="check")
        op.create_check_constraint(
            "ck_admin_security_purpose", "admin_security_challenge",
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp', 'change_pix_otp')",
        )

    op.drop_table("infinitepay_settings")
    if bind.dialect.name == "sqlite":
        payment = sa.Table("provider_payment", sa.MetaData(), autoload_with=bind)
        for constraint in list(payment.foreign_key_constraints):
            if any(element.parent.name == "credential_id" for element in constraint.elements):
                payment.constraints.remove(constraint)
        with op.batch_alter_table("provider_payment", copy_from=payment, recreate="always") as batch:
            batch.drop_column("credential_id")
            batch.drop_column("checkout_url")
    else:
        op.drop_constraint("fk_provider_payment_credential_owner", "provider_payment", type_="foreignkey")
        op.drop_column("provider_payment", "credential_id")
        op.drop_column("provider_payment", "checkout_url")
    op.drop_table("infinitepay_credential")


def downgrade() -> None:
    raise RuntimeError(
        "Migração irreversível: credenciais, URLs de checkout e desafios InfinitePay foram removidos; "
        "restaure backup anterior se for necessário reverter."
    )
