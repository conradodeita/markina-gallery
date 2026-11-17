"""Atendimento de recuperação do fotógrafo; DDL congelado, sem credenciais reais."""
import sqlalchemy as sa
from alembic import op

revision = "20261110_0124"
down_revision = "20261110_0123"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Recuperação assistida requer PostgreSQL.")
    op.execute(sa.text("CREATE TABLE photographer_access_recovery (\n\tid UUID NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tadmin_user_id UUID NOT NULL, \n\tactor_admin_id UUID NOT NULL, \n\tclosure_request_id UUID, \n\tidentity_confirmed BOOLEAN NOT NULL, \n\treason_code VARCHAR(24) NOT NULL, \n\treset_totp BOOLEAN NOT NULL, \n\texpected_version VARCHAR(64) NOT NULL, \n\trequest_fingerprint VARCHAR(64) NOT NULL, \n\trecipient_fingerprint VARCHAR(64) NOT NULL, \n\ttoken_hash VARCHAR(64), \n\tencrypted_payload TEXT, \n\tstate VARCHAR(24) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\temail_verified_at TIMESTAMP WITH TIME ZONE, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_access_recovery_target_membership FOREIGN KEY(admin_user_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id), \n\tCONSTRAINT fk_access_recovery_closure FOREIGN KEY(closure_request_id, tenant_id) REFERENCES tenant_closure_request (id, tenant_id), \n\tCONSTRAINT ck_access_recovery_state CHECK (state IN ('email_pending','email_verified','completed','expired')), \n\tCONSTRAINT ck_access_recovery_reason CHECK (reason_code IN ('lost_email','lost_all_access')), \n\tCONSTRAINT ck_access_recovery_identity_confirmed CHECK (identity_confirmed), \n\tCONSTRAINT ck_access_recovery_versions CHECK (length(expected_version) = 64 AND length(request_fingerprint) = 64), \n\tCONSTRAINT ck_access_recovery_pending_payload CHECK (state NOT IN ('email_pending','email_verified') OR encrypted_payload IS NOT NULL), \n\tCONSTRAINT ck_access_recovery_pending_token CHECK (state != 'email_pending' OR token_hash IS NOT NULL), \n\tCONSTRAINT ck_access_recovery_email_verified CHECK (state NOT IN ('email_verified','completed') OR email_verified_at IS NOT NULL), \n\tCONSTRAINT ck_access_recovery_completed CHECK (state != 'completed' OR (completed_at IS NOT NULL AND token_hash IS NULL AND encrypted_payload IS NULL)), \n\tCONSTRAINT ck_access_recovery_expired CHECK (state != 'expired' OR (token_hash IS NULL AND encrypted_payload IS NULL)), \n\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n\tFOREIGN KEY(admin_user_id) REFERENCES admin_user (id), \n\tFOREIGN KEY(actor_admin_id) REFERENCES admin_user (id), \n\tUNIQUE (token_hash)\n)"))
    op.execute(sa.text('CREATE INDEX ix_photographer_access_recovery_admin_user_id ON photographer_access_recovery (admin_user_id)'))
    op.execute(sa.text('CREATE INDEX ix_photographer_access_recovery_tenant_id ON photographer_access_recovery (tenant_id)'))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Recuperação de acesso requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photographer_access_recovery IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM photographer_access_recovery)")):
        raise RuntimeError("Preserve o histórico de recuperação assistida; rollback recusado.")
    op.drop_table("photographer_access_recovery")
