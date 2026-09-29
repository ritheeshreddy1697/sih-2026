"""Add certificate policies and digital certificates.

Revision ID: 20260928_06
Revises: 20260927_05
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_06"
down_revision: str | None = "20260927_05"
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
        "certificate_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("configured_by_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_title", sa.String(length=255), nullable=False),
        sa.Column(
            "minimum_course_completion_percent",
            sa.Float(),
            server_default="100",
            nullable=False,
        ),
        sa.Column(
            "minimum_attendance_percent",
            sa.Float(),
            server_default="75",
            nullable=False,
        ),
        sa.Column(
            "minimum_assessment_score_percent",
            sa.Float(),
            server_default="60",
            nullable=False,
        ),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "minimum_course_completion_percent >= 0 AND "
            "minimum_course_completion_percent <= 100",
            name="ck_certificate_policy_course_completion_range",
        ),
        sa.CheckConstraint(
            "minimum_attendance_percent >= 0 AND minimum_attendance_percent <= 100",
            name="ck_certificate_policy_attendance_range",
        ),
        sa.CheckConstraint(
            "minimum_assessment_score_percent >= 0 AND "
            "minimum_assessment_score_percent <= 100",
            name="ck_certificate_policy_assessment_range",
        ),
        sa.CheckConstraint(
            "validity_days IS NULL OR validity_days > 0",
            name="ck_certificate_policy_validity_positive",
        ),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["configured_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("programme_id", name="uq_certificate_policy_programme"),
    )
    op.create_index(
        op.f("ix_certificate_policies_programme_id"),
        "certificate_policies",
        ["programme_id"],
    )
    op.create_index(
        op.f("ix_certificate_policies_configured_by_id"),
        "certificate_policies",
        ["configured_by_id"],
    )

    op.create_table(
        "digital_certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("issued_by_id", sa.Uuid(), nullable=False),
        sa.Column("revoked_by_id", sa.Uuid(), nullable=True),
        sa.Column("certificate_number", sa.String(length=64), nullable=False),
        sa.Column("verification_token", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("course_completion_percent", sa.Float(), nullable=False),
        sa.Column("attendance_percent", sa.Float(), nullable=False),
        sa.Column("assessment_score_percent", sa.Float(), nullable=False),
        sa.Column("pdf_content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "course_completion_percent >= 0 AND course_completion_percent <= 100",
            name="ck_digital_certificate_course_completion_range",
        ),
        sa.CheckConstraint(
            "attendance_percent >= 0 AND attendance_percent <= 100",
            name="ck_digital_certificate_attendance_range",
        ),
        sa.CheckConstraint(
            "assessment_score_percent >= 0 AND assessment_score_percent <= 100",
            name="ck_digital_certificate_assessment_range",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["certificate_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["issued_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", name="uq_digital_certificate_enrollment"),
        sa.UniqueConstraint("certificate_number", name="uq_digital_certificate_number"),
        sa.UniqueConstraint(
            "verification_token", name="uq_digital_certificate_verification_token"
        ),
    )
    for column in (
        "enrollment_id",
        "policy_id",
        "issued_by_id",
        "revoked_by_id",
        "certificate_number",
        "verification_token",
        "issued_at",
        "expires_at",
        "revoked_at",
    ):
        op.create_index(
            op.f(f"ix_digital_certificates_{column}"), "digital_certificates", [column]
        )


def downgrade() -> None:
    op.drop_table("digital_certificates")
    op.drop_table("certificate_policies")
