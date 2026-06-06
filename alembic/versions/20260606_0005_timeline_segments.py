"""Add timeline segment model."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260606_0005"
down_revision = "20260606_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("composition_plan_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("segment_type", sa.String(length=64), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("start_sec", sa.Float(), nullable=False),
        sa.Column("end_sec", sa.Float(), nullable=False),
        sa.Column("target_duration_sec", sa.Float(), nullable=False),
        sa.Column("message_text", sa.String(length=512), nullable=True),
        sa.Column("preferred_layers_json", sa.Text(), nullable=False),
        sa.Column("text_rule", sa.String(length=128), nullable=True),
        sa.Column("audio_policy", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["composition_plan_id"], ["composition_plans.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("composition_plan_id", "sequence_index", name="uq_timeline_segments_plan_order"),
    )


def downgrade() -> None:
    op.drop_table("timeline_segments")
