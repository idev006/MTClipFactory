"""Add creative preset request fields to production order items."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260627_0009"
down_revision = "20260625_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_order_items",
        sa.Column(
            "creative_preset_mode",
            sa.String(length=64),
            nullable=False,
            server_default="auto_best_fit",
        ),
    )
    op.add_column(
        "production_order_items",
        sa.Column(
            "creative_preset_codes_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("production_order_items", "creative_preset_codes_json")
    op.drop_column("production_order_items", "creative_preset_mode")
