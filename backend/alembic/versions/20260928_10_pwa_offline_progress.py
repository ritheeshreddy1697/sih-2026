"""Add idempotent offline learning progress events.

Revision ID: 20260928_10
Revises: 20260928_09
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_10"
down_revision: str | None = "20260928_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_progress_sync_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("position_seconds", sa.Integer(), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "elapsed_seconds IS NULL OR (elapsed_seconds > 0 AND elapsed_seconds <= 30)",
            name="ck_learning_sync_elapsed_bounded",
        ),
        sa.CheckConstraint(
            "position_seconds IS NULL OR position_seconds >= 0",
            name="ck_learning_sync_position_positive",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in (
        "idempotency_key",
        "user_id",
        "enrollment_id",
        "lesson_id",
        "event_type",
        "captured_at",
    ):
        op.create_index(
            op.f(f"ix_learning_progress_sync_events_{column}"),
            "learning_progress_sync_events",
            [column],
        )


def downgrade() -> None:
    op.drop_table("learning_progress_sync_events")
