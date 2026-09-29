"""Add persistent user notifications.

Revision ID: 20260930_13
Revises: 20260928_12
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930_13"
down_revision: str | None = "20260928_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_sender_id"), "notifications", ["sender_id"])
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"])

    op.create_table(
        "notification_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id", "recipient_id", name="uq_notification_recipient"
        ),
    )
    op.create_index(
        op.f("ix_notification_receipts_notification_id"),
        "notification_receipts",
        ["notification_id"],
    )
    op.create_index(
        op.f("ix_notification_receipts_recipient_id"),
        "notification_receipts",
        ["recipient_id"],
    )
    op.create_index(
        op.f("ix_notification_receipts_read_at"), "notification_receipts", ["read_at"]
    )


def downgrade() -> None:
    op.drop_table("notification_receipts")
    op.drop_table("notifications")
