"""Импорт кампаний из Keitaro: nullable гео/потоки, флаг imported

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("campaigns", "geo_code", existing_type=sa.String(length=2), nullable=True)
    op.alter_column("campaigns", "geo_stream_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("campaigns", "offer_stream_id", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "campaigns",
        sa.Column("imported", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "imported")
    op.alter_column("campaigns", "offer_stream_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("campaigns", "geo_stream_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("campaigns", "geo_code", existing_type=sa.String(length=2), nullable=False)
