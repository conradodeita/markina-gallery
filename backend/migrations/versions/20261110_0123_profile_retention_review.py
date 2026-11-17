"""Revisão manual do perfil encerrado, preservando identidade mínima e auditoria."""

import sqlalchemy as sa
from alembic import op

revision = "20261110_0123"
down_revision = "20261110_0122"
branch_labels = None
depends_on = None

_ACTIONS = (
    "'tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
    "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
    "'tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened',"
    "'tenant.media_deletion_requested','tenant.media_deletion_retry'"
)


def upgrade() -> None:
    op.alter_column("photographer_business_profile", "cpf_envelope",
                    existing_type=sa.String(length=768), nullable=True)
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event",
                               f"action IN ({_ACTIONS},'tenant.profile_reduced')")
    op.create_check_constraint(
        "ck_platform_admin_profile_reduced_context", "platform_admin_event",
        "action != 'tenant.profile_reduced' OR (result = 'success' AND tenant_id IS NOT NULL "
        "AND object_id IS NOT NULL AND previous_status IS NOT NULL AND next_status IS NOT NULL "
        "AND previous_status = 'retained' AND next_status = 'reduced')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Retenção de perfil requer PostgreSQL.")
    connection.exec_driver_sql(
        "LOCK TABLE photographer_business_profile, platform_admin_event "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event WHERE action='tenant.profile_reduced')"
    )):
        raise RuntimeError("Preserve auditorias de redução de perfil: rollback recusado.")
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM photographer_business_profile WHERE cpf_envelope IS NULL)"
    )):
        raise RuntimeError("Preserve perfis reduzidos: rollback recusado.")
    op.drop_constraint("ck_platform_admin_profile_reduced_context", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", f"action IN ({_ACTIONS})")
    op.alter_column("photographer_business_profile", "cpf_envelope",
                    existing_type=sa.String(length=768), nullable=False)
