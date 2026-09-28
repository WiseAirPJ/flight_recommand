"""Durable monthly results, leased jobs and idempotent observations."""

import sqlalchemy as sa

from alembic import op

revision = "b17d9a220001"
down_revision = "7a6e54d68711"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monthly_searches",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("lease_until", sa.DateTime(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(200), nullable=True),
    )
    op.add_column(
        "price_observations", sa.Column("observation_key", sa.String(64), nullable=True)
    )
    op.create_index(
        "ix_observation_key", "price_observations", ["observation_key"], unique=True
    )


def downgrade():
    op.drop_index("ix_observation_key", table_name="price_observations")
    op.drop_column("price_observations", "observation_key")
    op.drop_table("monthly_searches")
