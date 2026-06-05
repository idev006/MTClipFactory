"""Add append-only decision event history."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260606_0003"
down_revision = "20260606_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("output_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["output_id"], ["outputs.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("decision_events")
