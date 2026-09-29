"""Add kiosk attendance sessions, check-ins and corrections.

Revision ID: 20260927_05
Revises: 20260927_04
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_05"
down_revision: str | None = "20260927_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.add_column(
        "trainee_profiles",
        sa.Column("qr_identity_version", sa.Integer(), server_default="1", nullable=False),
    )

    op.create_table(
        "kiosk_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("registered_by_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("device_code", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["registered_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_code"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("institution_id", "registered_by_id", "device_code", "status", "last_seen_at"):
        op.create_index(op.f(f"ix_kiosk_devices_{column}"), "kiosk_devices", [column])

    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["programme_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("programme_id", "batch_id", "created_by_id", "starts_at", "ends_at", "status"):
        op.create_index(
            op.f(f"ix_attendance_sessions_{column}"), "attendance_sessions", [column]
        )

    op.create_table(
        "attendance_check_ins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attendance_session_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("kiosk_device_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="present", nullable=False),
        sa.Column("source", sa.String(length=24), server_default="kiosk", nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"], ["attendance_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["kiosk_device_id"], ["kiosk_devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint(
            "attendance_session_id",
            "enrollment_id",
            name="uq_attendance_check_in_session_enrollment",
        ),
    )
    for column in (
        "attendance_session_id",
        "enrollment_id",
        "kiosk_device_id",
        "idempotency_key",
        "status",
        "captured_at",
        "checked_in_at",
    ):
        op.create_index(
            op.f(f"ix_attendance_check_ins_{column}"), "attendance_check_ins", [column]
        )

    op.create_table(
        "attendance_corrections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attendance_session_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("check_in_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("previous_status", sa.String(length=24), nullable=True),
        sa.Column("requested_status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "approval_status", sa.String(length=24), server_default="pending", nullable=False
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"], ["attendance_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["check_in_id"], ["attendance_check_ins.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "attendance_session_id",
        "enrollment_id",
        "check_in_id",
        "requested_by_id",
        "reviewed_by_id",
        "approval_status",
    ):
        op.create_index(
            op.f(f"ix_attendance_corrections_{column}"), "attendance_corrections", [column]
        )


def downgrade() -> None:
    op.drop_table("attendance_corrections")
    op.drop_table("attendance_check_ins")
    op.drop_table("attendance_sessions")
    op.drop_table("kiosk_devices")
    op.drop_column("trainee_profiles", "qr_identity_version")
