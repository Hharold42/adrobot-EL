"""Потоки кампаний и привязки офферов (черновики, пины, архив)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-26

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("keitaro_stream_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema", sa.String(length=50), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keitaro_stream_id"),
    )
    op.create_index("ix_streams_campaign_id", "streams", ["campaign_id"])
    op.create_table(
        "stream_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
        sa.Column("share", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("in_keitaro", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("was_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_share", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "offer_id"),
    )
    op.create_index("ix_stream_offers_stream_id", "stream_offers", ["stream_id"])


def downgrade() -> None:
    op.drop_index("ix_stream_offers_stream_id", table_name="stream_offers")
    op.drop_table("stream_offers")
    op.drop_index("ix_streams_campaign_id", table_name="streams")
    op.drop_table("streams")
