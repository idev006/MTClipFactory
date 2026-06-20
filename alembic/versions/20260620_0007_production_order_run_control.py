"""Add production order run-control metadata and order events."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260620_0007"
down_revision = "20260613_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_orders",
        sa.Column("preview_generation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("production_orders", sa.Column("run_mode", sa.String(length=64), nullable=True))
    op.add_column("production_orders", sa.Column("source_root", sa.String(length=1024), nullable=True))
    op.add_column("production_orders", sa.Column("lease_owner", sa.String(length=128), nullable=True))
    op.add_column("production_orders", sa.Column("lease_acquired_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("production_orders", sa.Column("lease_heartbeat_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("production_orders", sa.Column("lease_expires_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("production_orders", sa.Column("blocking_reason", sa.Text(), nullable=True))

    op.create_table(
        "production_order_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("production_order_item_id", sa.Integer(), nullable=True),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"]),
        sa.ForeignKeyConstraint(["production_order_item_id"], ["production_order_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_order_id", "sequence_index", name="uq_production_order_events_order_seq"),
    )


def downgrade() -> None:
    op.drop_table("production_order_events")
    op.drop_column("production_orders", "blocking_reason")
    op.drop_column("production_orders", "lease_expires_at")
    op.drop_column("production_orders", "lease_heartbeat_at")
    op.drop_column("production_orders", "lease_acquired_at")
    op.drop_column("production_orders", "lease_owner")
    op.drop_column("production_orders", "source_root")
    op.drop_column("production_orders", "run_mode")
    op.drop_column("production_orders", "preview_generation_enabled")
