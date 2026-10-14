"""Centraliza PIX sem remover configurações e snapshots legados.

Revision ID: 20260906_0046
Revises: 20260906_0045
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.global_pix import normalize_configuration
from app.pix import PixCodeError

revision = "20260906_0046"
down_revision = "20260906_0045"
branch_labels = None
depends_on = None


def _purpose_constraint(include_pix: bool) -> None:
    bind = op.get_bind()
    purposes = "'password_recovery_otp', 'change_password_otp', 'change_email_otp'"
    if include_pix:
        purposes += ", 'change_pix_otp'"
    expression = f"purpose IN ({purposes})"
    table = sa.Table("admin_security_challenge", sa.MetaData(), autoload_with=bind)
    constraints = [
        c
        for c in table.constraints
        if isinstance(c, sa.CheckConstraint) and "purpose" in str(c.sqltext)
    ]
    if bind.dialect.name == "sqlite":
        for constraint in constraints:
            table.constraints.remove(constraint)
        table.append_constraint(sa.CheckConstraint(expression, name="ck_admin_security_purpose"))
        with op.batch_alter_table(table.name, copy_from=table, recreate="always"):
            pass
    else:
        for constraint in constraints:
            op.drop_constraint(constraint.name, table.name, type_="check")
        op.create_check_constraint("ck_admin_security_purpose", table.name, expression)


def upgrade() -> None:
    op.create_table(
        "global_pix_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("singleton", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False, unique=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_type", sa.String(16)),
        sa.Column("pix_key", sa.String(160)),
        sa.Column("copy_paste", sa.Text()),
        sa.Column("receiver_name", sa.String(25)),
        sa.Column("receiver_city", sa.String(15)),
        sa.Column("instructions", sa.String(500)),
        sa.Column("legacy_group_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'unconfigured', 'review_required')"),
        sa.CheckConstraint("version >= 0"),
        sa.CheckConstraint("singleton = 1"),
        sa.CheckConstraint("status != 'active' OR copy_paste IS NOT NULL"),
    )
    op.add_column("sale_order", sa.Column("pix_configuration_snapshot", sa.JSON(), nullable=True))
    _purpose_constraint(True)
    bind = op.get_bind()
    admin = sa.Table("admin_user", sa.MetaData(), autoload_with=bind)
    admin_ids = list(bind.scalars(sa.select(admin.c.id)))
    if not admin_ids:
        return
    if len(admin_ids) != 1:
        raise RuntimeError("PIX global requer um único fotógrafo no MVP; revisar administradores.")
    legacy = sa.Table("pix_checkout_settings", sa.MetaData(), autoload_with=bind)
    groups = {}
    invalid = False
    for row in bind.execute(sa.select(legacy)).mappings():
        if not any(
            row[key] for key in ("copy_paste", "qr_code_payload", "pix_key", "instructions")
        ):
            continue
        try:
            if row["review_required"]:
                raise PixCodeError("Revisão legada pendente.")
            normalized = normalize_configuration(
                {
                    "copy_paste": row["pix_key"] or row["copy_paste"] or row["qr_code_payload"],
                    "receiver_name": row["receiver_name"],
                    "receiver_city": row["receiver_city"],
                    "instructions": row["instructions"],
                }
            )
            if row["copy_paste"] and normalized["copy_paste"] != row["copy_paste"].strip():
                raise PixCodeError("Código legado divergente da chave.")
            if (
                row["qr_code_payload"]
                and normalized["copy_paste"] != row["qr_code_payload"].strip()
            ):
                raise PixCodeError("Código legado divergente do QR.")
            signature = json.dumps([normalized["copy_paste"], normalized["instructions"]])
            groups[signature] = normalized
        except PixCodeError:
            invalid = True
    configuration = normalize_configuration(None)
    if invalid or len(groups) > 1:
        configuration["status"] = "review_required"
    elif groups:
        configuration = next(iter(groups.values()))
    table = sa.Table("global_pix_settings", sa.MetaData(), autoload_with=bind)
    bind.execute(
        table.insert().values(
            id=uuid4().hex if bind.dialect.name == "sqlite" else uuid4(),
            singleton=1,
            admin_user_id=admin_ids[0],
            version=1 if configuration["status"] == "active" else 0,
            legacy_group_count=len(groups),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            **configuration,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(
        sa.text("SELECT COUNT(*) FROM sale_order WHERE pix_configuration_snapshot IS NOT NULL")
    ):
        raise RuntimeError("Preserve os snapshots PIX globais; use rollback da aplicação.")
    if bind.scalar(
        sa.text("SELECT COUNT(*) FROM admin_security_challenge WHERE purpose = 'change_pix_otp'")
    ):
        raise RuntimeError("Preserve os desafios PIX auditáveis; use rollback da aplicação.")
    _purpose_constraint(False)
    op.drop_column("sale_order", "pix_configuration_snapshot")
    op.drop_table("global_pix_settings")
