"""Initial schema for MTClipFactory."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260605_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("brand_name", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_platform", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("asset_code", sa.String(length=128), nullable=False, unique=True),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("ratio", sa.String(length=16), nullable=True),
        sa.Column("file_size_mb", sa.Float(), nullable=True),
        sa.Column("codec", sa.String(length=64), nullable=True),
        sa.Column("has_audio", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("thumbnail_path", sa.String(length=1024), nullable=True),
        sa.Column("proxy_path", sa.String(length=1024), nullable=True),
        sa.Column("alpha_path", sa.String(length=1024), nullable=True),
        sa.Column("rgba_cache_path", sa.String(length=1024), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tag_name", sa.String(length=128), nullable=False),
        sa.Column("tag_group", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("tag_name", "tag_group", name="uq_tags_name_group"),
    )

    op.create_table(
        "asset_tags",
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
    )

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("recipe_code", sa.String(length=128), nullable=False, unique=True),
        sa.Column("target_platform", sa.String(length=64), nullable=True),
        sa.Column("target_ratio", sa.String(length=16), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("mood", sa.String(length=64), nullable=True),
        sa.Column("script_angle", sa.String(length=128), nullable=True),
        sa.Column("target_audience", sa.String(length=128), nullable=True),
        sa.Column("hook_text", sa.String(length=512), nullable=True),
        sa.Column("cta_text", sa.String(length=512), nullable=True),
        sa.Column("recipe_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("duplicate_risk", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )

    op.create_table(
        "recipe_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_code", sa.String(length=128), nullable=False, unique=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id"), nullable=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
    )

    op.create_table(
        "outputs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("output_code", sa.String(length=128), nullable=False, unique=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("ratio", sa.String(length=16), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("duplicate_risk", sa.Float(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("outputs")
    op.drop_table("jobs")
    op.drop_table("recipe_items")
    op.drop_table("recipes")
    op.drop_table("asset_tags")
    op.drop_table("tags")
    op.drop_table("assets")
    op.drop_table("products")

