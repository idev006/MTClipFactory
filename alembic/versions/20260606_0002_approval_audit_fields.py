"""Add approval audit fields to recipes and outputs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260606_0002"
down_revision = "20260605_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.add_column(sa.Column("decision_actor", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("decision_at", sa.DateTime(timezone=False), nullable=True))
        batch_op.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))

    with op.batch_alter_table("outputs") as batch_op:
        batch_op.add_column(sa.Column("approved_by", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(timezone=False), nullable=True))
        batch_op.add_column(sa.Column("approval_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("outputs") as batch_op:
        batch_op.drop_column("approval_reason")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by")

    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_column("decision_reason")
        batch_op.drop_column("decision_at")
        batch_op.drop_column("decision_actor")
