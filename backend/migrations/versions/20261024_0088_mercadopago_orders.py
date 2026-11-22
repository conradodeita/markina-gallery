"""Checkout Transparente Orders; DDL congelado, histórico preservado."""
import sqlalchemy as sa
from alembic import op

revision = "20261024_0088"
down_revision = "20261022_0087"
branch_labels = None
depends_on = None

TABLE_DDL = {'postgresql': [('\n'
                'CREATE TABLE mercadopago_account (\n'
                '\tid UUID NOT NULL, \n'
                '\ttenant_id UUID NOT NULL, \n'
                '\tseller_id VARCHAR(32) NOT NULL, \n'
                '\tpublic_key VARCHAR(200) NOT NULL, \n'
                '\taccess_token_envelope JSON NOT NULL, \n'
                '\twebhook_secret_envelope JSON NOT NULL, \n'
                '\ttest_account BOOLEAN NOT NULL, \n'
                '\tstatus VARCHAR(24) NOT NULL, \n'
                '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
                '\tPRIMARY KEY (id), \n'
                "\tCONSTRAINT ck_mp_account_status CHECK (status IN ('active', 'unauthorized')), \n"
                '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
                '\tCONSTRAINT uq_owner_mercadopago_account_id_tenant_id UNIQUE (id, tenant_id)\n'
                ')\n'
                '\n'),
                ('\n'
                'CREATE TABLE payment_preferences (\n'
                '\tid UUID NOT NULL, \n'
                '\ttenant_id UUID NOT NULL, \n'
                '\taccount_id UUID, \n'
                '\tversion INTEGER NOT NULL, \n'
                "\tpix_enabled BOOLEAN DEFAULT 'true' NOT NULL, \n"
                "\tmercadopago_enabled BOOLEAN DEFAULT 'false' NOT NULL, \n"
                '\tPRIMARY KEY (id), \n'
                '\tCONSTRAINT ck_payment_preferences_version CHECK (version >= 0), \n'
                '\tCONSTRAINT ck_payment_preferences_account CHECK (NOT mercadopago_enabled OR '
                'account_id IS NOT NULL), \n'
                '\tUNIQUE (tenant_id), \n'
                '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
                '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
                '\tCONSTRAINT uq_owner_payment_preferences_id_tenant_id UNIQUE (id, tenant_id), \n'
                '\tCONSTRAINT fk_owner_payment_preferences_account_id_tenant_id_merc_2865bf6e '
                'FOREIGN KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, '
                'tenant_id)\n'
                ')\n'
                '\n'),
                ('\n'
                'CREATE TABLE mercadopago_payment (\n'
                '\tid UUID NOT NULL, \n'
                '\ttenant_id UUID NOT NULL, \n'
                '\tclient_id UUID NOT NULL, \n'
                '\taccount_id UUID NOT NULL, \n'
                '\tcheckout_key VARCHAR(36) NOT NULL, \n'
                '\tcart_revision VARCHAR(64) NOT NULL, \n'
                '\ttotal_cents INTEGER NOT NULL, \n'
                '\tmethod VARCHAR(24) NOT NULL, \n'
                '\tstate VARCHAR(32) NOT NULL, \n'
                '\tactive BOOLEAN NOT NULL, \n'
                '\tprovider_order_id VARCHAR(64), \n'
                '\tprovider_payment_id VARCHAR(64), \n'
                '\torder_status VARCHAR(32), \n'
                '\torder_detail VARCHAR(64), \n'
                '\ttransaction_status VARCHAR(32), \n'
                '\ttransaction_detail VARCHAR(64), \n'
                '\tprovider_updated_at TIMESTAMP WITH TIME ZONE, \n'
                '\tpix_copy_paste TEXT, \n'
                '\terror_category VARCHAR(48), \n'
                '\tcheck_attempts INTEGER NOT NULL, \n'
                '\tnext_check_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
                '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
                '\tsent_at TIMESTAMP WITH TIME ZONE, \n'
                '\tconfirmed_at TIMESTAMP WITH TIME ZONE, \n'
                '\tPRIMARY KEY (id), \n'
                '\tCONSTRAINT uq_mp_payment_owner UNIQUE (id, tenant_id, client_id), \n'
                '\tCONSTRAINT uq_mp_checkout_key UNIQUE (tenant_id, client_id, checkout_key), \n'
                '\tCONSTRAINT ck_mp_total CHECK (total_cents > 0), \n'
                "\tCONSTRAINT ck_mp_method CHECK (method IN ('credit_card', 'pix')), \n"
                "\tCONSTRAINT ck_mp_state CHECK (state IN ('prepared', 'sending', 'initiated', "
                "'pending', 'processing', 'confirmed', 'rejected', 'canceled', 'expired', "
                "'refunded', 'partially_refunded', 'charged_back', 'verification_required', "
                "'duplicate_review', 'abandoned')), \n"
                "\tCONSTRAINT ck_mp_confirmed CHECK (state != 'confirmed' OR (provider_order_id IS "
                'NOT NULL AND provider_payment_id IS NOT NULL AND confirmed_at IS NOT NULL)), \n'
                '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
                '\tFOREIGN KEY(client_id) REFERENCES client (id), \n'
                '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
                '\tCONSTRAINT uq_mp_provider_order UNIQUE (tenant_id, account_id, '
                'provider_order_id), \n'
                '\tCONSTRAINT uq_owner_mercadopago_payment_id_tenant_id UNIQUE (id, tenant_id), \n'
                '\tCONSTRAINT fk_owner_mercadopago_payment_client_id_tenant_id_client FOREIGN '
                'KEY(client_id, tenant_id) REFERENCES client (id, tenant_id), \n'
                '\tCONSTRAINT fk_owner_mercadopago_payment_account_id_tenant_id_merc_19fc305a '
                'FOREIGN KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, '
                'tenant_id)\n'
                ')\n'
                '\n'),
                ('\n'
                'CREATE TABLE mercadopago_webhook (\n'
                '\tid UUID NOT NULL, \n'
                '\ttenant_id UUID NOT NULL, \n'
                '\taccount_id UUID NOT NULL, \n'
                '\tprovider_order_id VARCHAR(64) NOT NULL, \n'
                '\tdigest VARCHAR(64) NOT NULL, \n'
                '\tstate VARCHAR(16) NOT NULL, \n'
                '\tattempts INTEGER NOT NULL, \n'
                '\tnext_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
                '\tlease_until TIMESTAMP WITH TIME ZONE, \n'
                '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
                '\tprocessed_at TIMESTAMP WITH TIME ZONE, \n'
                '\tPRIMARY KEY (id), \n'
                "\tCONSTRAINT ck_mp_webhook_state CHECK (state IN ('queued', 'processing', 'done', "
                "'ignored', 'failed')), \n"
                '\tCONSTRAINT ck_mp_webhook_attempts CHECK (attempts >= 0), \n'
                '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
                '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
                '\tCONSTRAINT uq_mp_webhook_digest UNIQUE (tenant_id, account_id, digest), \n'
                '\tCONSTRAINT uq_owner_mercadopago_webhook_id_tenant_id UNIQUE (id, tenant_id), \n'
                '\tCONSTRAINT fk_owner_mercadopago_webhook_account_id_tenant_id_merc_3e5decb4 '
                'FOREIGN KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, '
                'tenant_id)\n'
                ')\n'
                '\n'),
                'CREATE INDEX ix_mercadopago_account_tenant_id ON mercadopago_account (tenant_id)',
                'CREATE INDEX ix_mercadopago_payment_client_id ON mercadopago_payment (client_id)',
                'CREATE INDEX ix_mercadopago_payment_tenant_id ON mercadopago_payment (tenant_id)',
                ('CREATE UNIQUE INDEX uq_mp_active_client ON mercadopago_payment (tenant_id, '
                'client_id) WHERE active = true'),
                'CREATE INDEX ix_mercadopago_webhook_tenant_id ON mercadopago_webhook (tenant_id)',
                'CREATE INDEX ix_mp_webhook_queue ON mercadopago_webhook (state, next_attempt_at)'],
 'sqlite': [('\n'
            'CREATE TABLE mercadopago_account (\n'
            '\tid CHAR(32) NOT NULL, \n'
            '\ttenant_id CHAR(32) NOT NULL, \n'
            '\tseller_id VARCHAR(32) NOT NULL, \n'
            '\tpublic_key VARCHAR(200) NOT NULL, \n'
            '\taccess_token_envelope JSON NOT NULL, \n'
            '\twebhook_secret_envelope JSON NOT NULL, \n'
            '\ttest_account BOOLEAN NOT NULL, \n'
            '\tstatus VARCHAR(24) NOT NULL, \n'
            '\tcreated_at DATETIME NOT NULL, \n'
            '\tPRIMARY KEY (id), \n'
            "\tCONSTRAINT ck_mp_account_status CHECK (status IN ('active', 'unauthorized')), \n"
            '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
            '\tCONSTRAINT uq_owner_mercadopago_account_id_tenant_id UNIQUE (id, tenant_id)\n'
            ')\n'
            '\n'),
            ('\n'
            'CREATE TABLE payment_preferences (\n'
            '\tid CHAR(32) NOT NULL, \n'
            '\ttenant_id CHAR(32) NOT NULL, \n'
            '\taccount_id CHAR(32), \n'
            '\tversion INTEGER NOT NULL, \n'
            "\tpix_enabled BOOLEAN DEFAULT 'true' NOT NULL, \n"
            "\tmercadopago_enabled BOOLEAN DEFAULT 'false' NOT NULL, \n"
            '\tPRIMARY KEY (id), \n'
            '\tCONSTRAINT ck_payment_preferences_version CHECK (version >= 0), \n'
            '\tCONSTRAINT ck_payment_preferences_account CHECK (NOT mercadopago_enabled OR '
            'account_id IS NOT NULL), \n'
            '\tUNIQUE (tenant_id), \n'
            '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
            '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
            '\tCONSTRAINT uq_owner_payment_preferences_id_tenant_id UNIQUE (id, tenant_id), \n'
            '\tCONSTRAINT fk_owner_payment_preferences_account_id_tenant_id_merc_2865bf6e FOREIGN '
            'KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, tenant_id)\n'
            ')\n'
            '\n'),
            ('\n'
            'CREATE TABLE mercadopago_payment (\n'
            '\tid CHAR(32) NOT NULL, \n'
            '\ttenant_id CHAR(32) NOT NULL, \n'
            '\tclient_id CHAR(32) NOT NULL, \n'
            '\taccount_id CHAR(32) NOT NULL, \n'
            '\tcheckout_key VARCHAR(36) NOT NULL, \n'
            '\tcart_revision VARCHAR(64) NOT NULL, \n'
            '\ttotal_cents INTEGER NOT NULL, \n'
            '\tmethod VARCHAR(24) NOT NULL, \n'
            '\tstate VARCHAR(32) NOT NULL, \n'
            '\tactive BOOLEAN NOT NULL, \n'
            '\tprovider_order_id VARCHAR(64), \n'
            '\tprovider_payment_id VARCHAR(64), \n'
            '\torder_status VARCHAR(32), \n'
            '\torder_detail VARCHAR(64), \n'
            '\ttransaction_status VARCHAR(32), \n'
            '\ttransaction_detail VARCHAR(64), \n'
            '\tprovider_updated_at DATETIME, \n'
            '\tpix_copy_paste TEXT, \n'
            '\terror_category VARCHAR(48), \n'
            '\tcheck_attempts INTEGER NOT NULL, \n'
            '\tnext_check_at DATETIME NOT NULL, \n'
            '\tcreated_at DATETIME NOT NULL, \n'
            '\tsent_at DATETIME, \n'
            '\tconfirmed_at DATETIME, \n'
            '\tPRIMARY KEY (id), \n'
            '\tCONSTRAINT uq_mp_payment_owner UNIQUE (id, tenant_id, client_id), \n'
            '\tCONSTRAINT uq_mp_checkout_key UNIQUE (tenant_id, client_id, checkout_key), \n'
            '\tCONSTRAINT ck_mp_total CHECK (total_cents > 0), \n'
            "\tCONSTRAINT ck_mp_method CHECK (method IN ('credit_card', 'pix')), \n"
            "\tCONSTRAINT ck_mp_state CHECK (state IN ('prepared', 'sending', 'initiated', "
            "'pending', 'processing', 'confirmed', 'rejected', 'canceled', 'expired', 'refunded', "
            "'partially_refunded', 'charged_back', 'verification_required', 'duplicate_review', "
            "'abandoned')), \n"
            "\tCONSTRAINT ck_mp_confirmed CHECK (state != 'confirmed' OR (provider_order_id IS NOT "
            'NULL AND provider_payment_id IS NOT NULL AND confirmed_at IS NOT NULL)), \n'
            '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
            '\tFOREIGN KEY(client_id) REFERENCES client (id), \n'
            '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
            '\tCONSTRAINT uq_mp_provider_order UNIQUE (tenant_id, account_id, '
            'provider_order_id), \n'
            '\tCONSTRAINT uq_owner_mercadopago_payment_id_tenant_id UNIQUE (id, tenant_id), \n'
            '\tCONSTRAINT fk_owner_mercadopago_payment_client_id_tenant_id_client FOREIGN '
            'KEY(client_id, tenant_id) REFERENCES client (id, tenant_id), \n'
            '\tCONSTRAINT fk_owner_mercadopago_payment_account_id_tenant_id_merc_19fc305a FOREIGN '
            'KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, tenant_id)\n'
            ')\n'
            '\n'),
            ('\n'
            'CREATE TABLE mercadopago_webhook (\n'
            '\tid CHAR(32) NOT NULL, \n'
            '\ttenant_id CHAR(32) NOT NULL, \n'
            '\taccount_id CHAR(32) NOT NULL, \n'
            '\tprovider_order_id VARCHAR(64) NOT NULL, \n'
            '\tdigest VARCHAR(64) NOT NULL, \n'
            '\tstate VARCHAR(16) NOT NULL, \n'
            '\tattempts INTEGER NOT NULL, \n'
            '\tnext_attempt_at DATETIME NOT NULL, \n'
            '\tlease_until DATETIME, \n'
            '\tcreated_at DATETIME NOT NULL, \n'
            '\tprocessed_at DATETIME, \n'
            '\tPRIMARY KEY (id), \n'
            "\tCONSTRAINT ck_mp_webhook_state CHECK (state IN ('queued', 'processing', 'done', "
            "'ignored', 'failed')), \n"
            '\tCONSTRAINT ck_mp_webhook_attempts CHECK (attempts >= 0), \n'
            '\tFOREIGN KEY(tenant_id) REFERENCES tenant (id), \n'
            '\tFOREIGN KEY(account_id) REFERENCES mercadopago_account (id), \n'
            '\tCONSTRAINT uq_mp_webhook_digest UNIQUE (tenant_id, account_id, digest), \n'
            '\tCONSTRAINT uq_owner_mercadopago_webhook_id_tenant_id UNIQUE (id, tenant_id), \n'
            '\tCONSTRAINT fk_owner_mercadopago_webhook_account_id_tenant_id_merc_3e5decb4 FOREIGN '
            'KEY(account_id, tenant_id) REFERENCES mercadopago_account (id, tenant_id)\n'
            ')\n'
            '\n'),
            'CREATE INDEX ix_mercadopago_account_tenant_id ON mercadopago_account (tenant_id)',
            'CREATE INDEX ix_mercadopago_payment_client_id ON mercadopago_payment (client_id)',
            'CREATE INDEX ix_mercadopago_payment_tenant_id ON mercadopago_payment (tenant_id)',
            ('CREATE UNIQUE INDEX uq_mp_active_client ON mercadopago_payment (tenant_id, client_id) '
            'WHERE active = true'),
            'CREATE INDEX ix_mercadopago_webhook_tenant_id ON mercadopago_webhook (tenant_id)',
            'CREATE INDEX ix_mp_webhook_queue ON mercadopago_webhook (state, next_attempt_at)']}


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect not in TABLE_DDL:
        raise RuntimeError("Migration suporta apenas PostgreSQL e SQLite.")
    for statement in TABLE_DDL[dialect]:
        op.execute(sa.text(statement))
    with op.batch_alter_table("sale_order") as batch:
        batch.add_column(sa.Column("mercadopago_payment_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_sale_order_mercadopago_payment_id", ["mercadopago_payment_id"])
        batch.create_foreign_key("fk_sale_order_mp_owner", "mercadopago_payment",
                                 ["mercadopago_payment_id", "tenant_id", "client_id"],
                                 ["id", "tenant_id", "client_id"])
        batch.create_check_constraint("ck_sale_order_mp_exclusive",
            "mercadopago_payment_id IS NULL OR (payment_group_id IS NULL AND provider_payment_id IS NULL)")
    with op.batch_alter_table("admin_security_challenge") as batch:
        batch.drop_constraint("ck_admin_security_purpose", type_="check")
        batch.create_check_constraint("ck_admin_security_purpose",
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp', 'change_pix_otp', 'change_payment_otp')")
        batch.drop_constraint("ck_admin_challenge_pix_context", type_="check")
        batch.create_check_constraint("ck_admin_challenge_pix_context",
            "purpose NOT IN ('change_pix_otp', 'change_payment_otp') OR tenant_id IS NOT NULL")


def downgrade():
    raise RuntimeError("Reversão exige inventário e plano de preservação dos pagamentos Orders; downgrade automático bloqueado.")
