"""Audita concessões e revogações de créditos pelo proprietário."""

import sqlalchemy as sa
from alembic import op

revision = "20261113_0126"
down_revision = "20261111_0125"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "'tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
    "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
    "'tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened',"
    "'tenant.media_deletion_requested','tenant.media_deletion_retry','tenant.profile_reduced'"
)


def upgrade() -> None:
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action", "platform_admin_event",
        f"action IN ({_PREVIOUS_ACTIONS},'credit.granted','credit.revoked',"
        "'credit.package_created','credit.package_updated','credit.purchase_reviewed')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Auditoria de mutações de crédito requer PostgreSQL.")
    connection.exec_driver_sql(
        "LOCK TABLE platform_admin_event IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event WHERE action IN "
        "('credit.granted','credit.revoked','credit.package_created','credit.package_updated',"
        "'credit.purchase_reviewed'))"
    )):
        raise RuntimeError("Preserve auditorias de concessão/revogação de créditos: rollback recusado.")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action", "platform_admin_event", f"action IN ({_PREVIOUS_ACTIONS})"
    )
