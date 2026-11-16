"""Auditoria preservadora para recuperação assistida do autenticador."""

import sqlalchemy as sa
from alembic import op

revision = "20261104_0102"
down_revision = "20261104_0101"
branch_labels = None
depends_on = None

OLD_ACTIONS = "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied')"
NEW_ACTIONS = "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied','photographer.totp_revoked','photographer.totp_revoke_denied')"


def upgrade():
    op.add_column("platform_admin_event", sa.Column("reason_code", sa.String(32), nullable=True))
    op.add_column("platform_admin_event", sa.Column("target_version", sa.String(64), nullable=True))
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", NEW_ACTIONS)
    op.create_check_constraint("ck_platform_admin_reason", "platform_admin_event",
                               "reason_code IS NULL OR reason_code IN ('lost_device','authenticator_unavailable','assisted_recovery')")
    op.create_check_constraint("ck_platform_admin_support_version", "platform_admin_event",
                               "target_version IS NULL OR length(target_version) = 64")
    op.create_check_constraint("ck_platform_admin_support_context", "platform_admin_event",
                               "action NOT IN ('photographer.totp_revoked','photographer.totp_revoke_denied') OR (reason_code IS NOT NULL AND target_version IS NOT NULL AND object_id IS NOT NULL AND (action != 'photographer.totp_revoked' OR tenant_id IS NOT NULL))")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Recuperação assistida TOTP requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE platform_admin_event IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event WHERE reason_code IS NOT NULL OR target_version IS NOT NULL "
        "OR action IN ('photographer.totp_revoked','photographer.totp_revoke_denied'))"
    )):
        raise RuntimeError("Preserve histórico de recuperação assistida: rollback recusado.")
    op.drop_constraint("ck_platform_admin_support_context", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_support_version", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_reason", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", OLD_ACTIONS)
    op.drop_column("platform_admin_event", "target_version")
    op.drop_column("platform_admin_event", "reason_code")
