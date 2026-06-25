"""Add output history-scope and rendered clip formula hash fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260625_0008"
down_revision = "20260620_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outputs", sa.Column("clip_formula_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "outputs",
        sa.Column(
            "history_scope",
            sa.String(length=32),
            nullable=False,
            server_default="draft_preview",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE outputs "
            "SET history_scope = CASE "
            "WHEN approved = 1 THEN 'approved_output' "
            "ELSE 'draft_preview' "
            "END"
        )
    )


def downgrade() -> None:
    op.drop_column("outputs", "history_scope")
    op.drop_column("outputs", "clip_formula_hash")
