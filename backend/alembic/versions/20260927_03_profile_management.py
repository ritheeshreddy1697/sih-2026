"""Add institution hierarchy and trainee profile management.

Revision ID: 20260927_03
Revises: 20260927_02
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_03"
down_revision: str | None = "20260927_02"
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
    for column in (
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("registration_number", sa.String(length=120), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
    ):
        op.add_column("institutions", column)
    op.create_foreign_key(
        "fk_institutions_parent_id_institutions",
        "institutions",
        "institutions",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    for column in ("parent_id", "state", "district"):
        op.create_index(op.f(f"ix_institutions_{column}"), "institutions", [column])

    op.create_table(
        "trainee_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=80), nullable=True),
        sa.Column("alternate_email", sa.String(length=320), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=12), nullable=True),
        sa.Column("preferred_language", sa.String(length=80), nullable=True),
        sa.Column("preferred_location", sa.String(length=160), nullable=True),
        sa.Column("career_interests", sa.Text(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column(
            "placement_visibility_consent", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("communication_consent", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("data_sharing_consent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("completion_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_trainee_profiles_completion_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column, unique in (
        ("user_id", True),
        ("state", False),
        ("preferred_language", False),
        ("preferred_location", False),
    ):
        op.create_index(
            op.f(f"ix_trainee_profiles_{column}"), "trainee_profiles", [column], unique=unique
        )

    op.create_table(
        "education_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("qualification", sa.String(length=160), nullable=False),
        sa.Column("field_of_study", sa.String(length=160), nullable=True),
        sa.Column("institution_name", sa.String(length=255), nullable=False),
        sa.Column("completion_year", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=80), nullable=True),
        sa.Column(
            "is_highest_qualification", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["trainee_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_education_records_profile_id"), "education_records", ["profile_id"])

    op.create_table(
        "employment_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("employer_name", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=160), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["trainee_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employment_records_profile_id"), "employment_records", ["profile_id"])

    op.create_table(
        "cooperative_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=False),
        sa.Column("membership_type", sa.String(length=120), nullable=False),
        sa.Column("member_number", sa.String(length=120), nullable=True),
        sa.Column("joined_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["trainee_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cooperative_memberships_profile_id"), "cooperative_memberships", ["profile_id"]
    )

    op.create_table(
        "trainee_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "validation_status", sa.String(length=24), server_default="pending", nullable=False
        ),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("validated_by_id", sa.Uuid(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_trainee_documents_size_positive"),
        sa.ForeignKeyConstraint(["profile_id"], ["trainee_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("profile_id", "validation_status"):
        op.create_index(op.f(f"ix_trainee_documents_{column}"), "trainee_documents", [column])

    op.create_table(
        "programme_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="enrolled", nullable=False),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["programme_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trainee_id", "programme_id", name="uq_enrollment_trainee_programme"),
    )
    for column in ("trainee_id", "programme_id", "batch_id", "status"):
        op.create_index(
            op.f(f"ix_programme_enrollments_{column}"), "programme_enrollments", [column]
        )

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_attendance_records_enrollment_id"), "attendance_records", ["enrollment_id"]
    )

    op.create_table(
        "assessment_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("maximum_score", sa.Float(), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("enrollment_id", "result"):
        op.create_index(op.f(f"ix_assessment_records_{column}"), "assessment_records", [column])

    op.create_table(
        "certificate_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_number", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificate_records_enrollment_id"), "certificate_records", ["enrollment_id"]
    )
    op.create_index(
        op.f("ix_certificate_records_certificate_number"),
        "certificate_records",
        ["certificate_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("certificate_records")
    op.drop_table("assessment_records")
    op.drop_table("attendance_records")
    op.drop_table("programme_enrollments")
    op.drop_table("trainee_documents")
    op.drop_table("cooperative_memberships")
    op.drop_table("employment_records")
    op.drop_table("education_records")
    op.drop_table("trainee_profiles")
    for column in ("district", "state", "parent_id"):
        op.drop_index(op.f(f"ix_institutions_{column}"), table_name="institutions")
    op.drop_constraint("fk_institutions_parent_id_institutions", "institutions", type_="foreignkey")
    for column in (
        "is_demo",
        "profile_summary",
        "registration_number",
        "website",
        "contact_phone",
        "contact_email",
        "address",
        "district",
        "state",
        "parent_id",
    ):
        op.drop_column("institutions", column)
