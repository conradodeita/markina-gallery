"""Pin the serving engine for each facial search."""

import sqlalchemy as sa
from alembic import op

revision = "20261011_0074"
down_revision = "20261011_0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "facial_search_request",
        sa.Column(
            "search_engine",
            sa.String(length=64),
            nullable=False,
            server_default="opencv-yunet-sface",
        ),
    )
    with op.batch_alter_table("facial_search_request") as batch:
        batch.create_check_constraint(
            "ck_facial_search_engine",
            "search_engine IN ('opencv-yunet-sface', 'google-embeddinggemma-2')",
        )
    with op.batch_alter_table("facial_job") as batch:
        batch.drop_constraint("ck_facial_job_kind", type_="check")
        batch.create_check_constraint(
            "ck_facial_job_kind",
            "kind IN ('index', 'index_gemma', 'purge', 'search', 'search_gemma', 'cleanup')",
        )


def downgrade() -> None:
    raise RuntimeError("Downgrade recusado: preserve o engine fixado em consultas faciais.")
