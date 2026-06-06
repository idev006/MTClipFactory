"""Add composition plan and render decision models."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260606_0004"
down_revision = "20260606_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "composition_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("duration_source", sa.String(length=64), nullable=False),
        sa.Column("target_duration_sec", sa.Float(), nullable=True),
        sa.Column("resolved_duration_sec", sa.Float(), nullable=True),
        sa.Column("layer_assignments_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id"),
    )
    op.create_table(
        "render_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("composition_plan_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("asset_role", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["composition_plan_id"], ["composition_plans.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("render_decisions")
    op.drop_table("composition_plans")
