"""Add consent-based biometric attendance verification.

Revision ID: 20260928_12
Revises: 20260928_11
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_12"
down_revision: str | None = "20260928_11"
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
    op.create_table(
        "biometric_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("consent_record_id", sa.Uuid(), nullable=True),
        sa.Column("encrypted_embedding", sa.LargeBinary(), nullable=False),
        sa.Column("encryption_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("encryption_key_version", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("liveness_score", sa.Float(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["consent_record_id"], ["consent_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trainee_id"),
    )
    op.create_index(
        op.f("ix_biometric_enrollments_trainee_id"),
        "biometric_enrollments",
        ["trainee_id"],
    )
    op.create_index(
        op.f("ix_biometric_enrollments_consent_record_id"),
        "biometric_enrollments",
        ["consent_record_id"],
    )

    op.create_table(
        "biometric_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("challenge_type", sa.String(length=24), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("attendance_session_id", sa.Uuid(), nullable=True),
        sa.Column("kiosk_device_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"], ["attendance_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["kiosk_device_id"], ["kiosk_devices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "purpose",
        "trainee_id",
        "attendance_session_id",
        "kiosk_device_id",
        "expires_at",
        "used_at",
        "created_at",
    ):
        op.create_index(
            op.f(f"ix_biometric_challenges_{column}"), "biometric_challenges", [column]
        )

    op.create_table(
        "biometric_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("biometric_enrollment_id", sa.Uuid(), nullable=True),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("programme_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("attendance_session_id", sa.Uuid(), nullable=False),
        sa.Column("kiosk_device_id", sa.Uuid(), nullable=True),
        sa.Column("check_in_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("liveness_score", sa.Float(), nullable=False),
        sa.Column("match_threshold", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column("review_status", sa.String(length=24), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"], ["biometric_challenges.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["biometric_enrollment_id"], ["biometric_enrollments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["programme_enrollment_id"],
            ["programme_enrollments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"], ["attendance_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["kiosk_device_id"], ["kiosk_devices.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["check_in_id"], ["attendance_check_ins.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in (
        "challenge_id",
        "biometric_enrollment_id",
        "trainee_id",
        "programme_enrollment_id",
        "attendance_session_id",
        "kiosk_device_id",
        "check_in_id",
        "reviewed_by_id",
        "idempotency_key",
        "status",
        "review_status",
        "captured_at",
        "created_at",
    ):
        op.create_index(
            op.f(f"ix_biometric_verifications_{column}"),
            "biometric_verifications",
            [column],
        )


def downgrade() -> None:
    op.drop_table("biometric_verifications")
    op.drop_table("biometric_challenges")
    op.drop_table("biometric_enrollments")
