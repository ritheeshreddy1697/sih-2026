"""Add employment exchange.

Revision ID: 20260928_08
Revises: 20260928_07
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_08"
down_revision: str | None = "20260928_07"
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


def indexes(table: str, *columns: str) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])


def upgrade() -> None:
    op.create_table(
        "employer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("registered_by_id", sa.Uuid(), nullable=False),
        sa.Column("verified_by_id", sa.Uuid(), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("company_size", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("headquarters", sa.String(length=255), nullable=False),
        sa.Column("registration_number", sa.String(length=120), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(length=24),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registered_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", name="uq_employer_profile_institution"),
    )
    indexes(
        "employer_profiles",
        "institution_id",
        "registered_by_id",
        "verified_by_id",
        "industry",
        "headquarters",
        "registration_number",
        "verification_status",
        "verified_at",
    )

    op.create_table(
        "trainee_employment_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=True),
        sa.Column("professional_summary", sa.Text(), nullable=True),
        sa.Column("preferred_roles", sa.JSON(), nullable=False),
        sa.Column("preferred_locations", sa.JSON(), nullable=False),
        sa.Column("open_to_work", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("resume_filename", sa.String(length=255), nullable=True),
        sa.Column("resume_content_type", sa.String(length=120), nullable=True),
        sa.Column("resume_size_bytes", sa.Integer(), nullable=True),
        sa.Column("resume_content", sa.LargeBinary(), nullable=True),
        sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trainee_id"),
    )
    indexes("trainee_employment_profiles", "trainee_id")

    op.create_table(
        "verified_employment_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["certificate_id"], ["digital_certificates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trainee_id", "certificate_id", "name", name="uq_verified_employment_skill"
        ),
    )
    indexes("verified_employment_skills", "trainee_id", "certificate_id", "name")

    op.create_table(
        "job_postings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employer_profile_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("employment_type", sa.String(length=24), nullable=False),
        sa.Column("workplace_mode", sa.String(length=24), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_skills", sa.JSON(), nullable=False),
        sa.Column("minimum_experience_years", sa.Integer(), server_default="0", nullable=False),
        sa.Column("vacancies", sa.Integer(), server_default="1", nullable=False),
        sa.Column("salary_minimum", sa.Float(), nullable=True),
        sa.Column("salary_maximum", sa.Float(), nullable=True),
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("vacancies > 0", name="ck_job_posting_vacancies_positive"),
        sa.CheckConstraint(
            "minimum_experience_years >= 0", name="ck_job_posting_experience_nonnegative"
        ),
        sa.CheckConstraint(
            "salary_minimum IS NULL OR salary_maximum IS NULL OR salary_maximum >= salary_minimum",
            name="ck_job_posting_salary_range",
        ),
        sa.ForeignKeyConstraint(
            ["employer_profile_id"], ["employer_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    indexes(
        "job_postings",
        "employer_profile_id",
        "created_by_id",
        "title",
        "location",
        "employment_type",
        "workplace_mode",
        "application_deadline",
        "status",
        "published_at",
        "closed_at",
    )

    op.create_table(
        "job_programme_requirements",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "programme_id"),
    )

    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "trainee_id", name="uq_saved_job_trainee"),
    )
    indexes("saved_jobs", "job_id", "trainee_id")

    op.create_table(
        "candidate_shortlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("shortlisted_by_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shortlisted_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "trainee_id", name="uq_candidate_shortlist_job"),
    )
    indexes("candidate_shortlists", "job_id", "trainee_id")

    op.create_table(
        "job_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("cover_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="applied", nullable=False),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_mode", sa.String(length=80), nullable=True),
        sa.Column("interview_details", sa.Text(), nullable=True),
        sa.Column("employer_notes", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "trainee_id", name="uq_job_application_trainee"),
    )
    indexes("job_applications", "job_id", "trainee_id", "status", "applied_at", "interview_at")

    op.create_table(
        "job_application_certificates",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["certificate_id"], ["digital_certificates.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("application_id", "certificate_id"),
    )


def downgrade() -> None:
    for table in (
        "job_application_certificates",
        "job_applications",
        "candidate_shortlists",
        "saved_jobs",
        "job_programme_requirements",
        "job_postings",
        "verified_employment_skills",
        "trainee_employment_profiles",
        "employer_profiles",
    ):
        op.drop_table(table)
