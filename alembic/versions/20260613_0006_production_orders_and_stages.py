"""Add production order and orchestration stage models."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260613_0006"
down_revision = "20260606_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_code", sa.String(length=128), nullable=False),
        sa.Column("batch_code", sa.String(length=128), nullable=False),
        sa.Column("source_mode", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("strict_fulfillment", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_code"),
    )
    op.create_table(
        "production_order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=128), nullable=False),
        sa.Column("requested_output_count", sa.Integer(), nullable=False),
        sa.Column("target_platform", sa.String(length=64), nullable=True),
        sa.Column("target_ratio", sa.String(length=16), nullable=True),
        sa.Column("uniqueness_scope", sa.String(length=32), nullable=False),
        sa.Column("duration_mode", sa.String(length=64), nullable=False),
        sa.Column("fixed_duration_sec", sa.Float(), nullable=True),
        sa.Column("min_duration_sec", sa.Float(), nullable=False),
        sa.Column("max_duration_sec", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "production_order_stages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("production_order_item_id", sa.Integer(), nullable=True),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("stage_scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("output_id", sa.Integer(), nullable=True),
        sa.Column("failure_class", sa.String(length=64), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["output_id"], ["outputs.id"]),
        sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"]),
        sa.ForeignKeyConstraint(["production_order_item_id"], ["production_order_items.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("production_order_stages")
    op.drop_table("production_order_items")
    op.drop_table("production_orders")
