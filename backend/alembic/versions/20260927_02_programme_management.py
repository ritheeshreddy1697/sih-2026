"""Add programme management tables.

Revision ID: 20260927_02
Revises: 20260927_01
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_02"
down_revision: str | None = "20260927_01"
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
        "programmes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("eligibility_criteria", sa.Text(), nullable=False),
        sa.Column("eligible_applicant_types", sa.JSON(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=80), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("capacity > 0", name="ck_programmes_capacity_positive"),
        sa.CheckConstraint("duration_days > 0", name="ck_programmes_duration_positive"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column, unique in (
        ("application_deadline", False),
        ("code", True),
        ("created_by_id", False),
        ("institution_id", False),
        ("language", False),
        ("mode", False),
        ("published_at", False),
        ("status", False),
        ("title", False),
    ):
        op.create_index(op.f(f"ix_programmes_{column}"), "programmes", [column], unique=unique)

    op.create_table(
        "programme_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("capacity > 0", name="ck_programme_batches_capacity_positive"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("programme_id", "code", name="uq_programme_batches_programme_code"),
    )
    op.create_index(
        op.f("ix_programme_batches_programme_id"),
        "programme_batches",
        ["programme_id"],
        unique=False,
    )

    op.create_table(
        "programme_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("trainee_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="submitted", nullable=False),
        sa.Column("statement", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trainee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "programme_id", "trainee_id", name="uq_programme_application_trainee"
        ),
    )
    for column in ("programme_id", "status", "trainee_id"):
        op.create_index(
            op.f(f"ix_programme_applications_{column}"),
            "programme_applications",
            [column],
            unique=False,
        )

    op.create_table(
        "programme_nominations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("nominating_institution_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("nomination_type", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=24), server_default="individual", nullable=False),
        sa.Column("candidate_full_name", sa.String(length=255), nullable=False),
        sa.Column("candidate_email", sa.String(length=320), nullable=False),
        sa.Column("candidate_phone", sa.String(length=32), nullable=True),
        sa.Column("member_identifier", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="submitted", nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["nominating_institution_id"], ["institutions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "programme_id", "candidate_email", name="uq_programme_nomination_email"
        ),
    )
    for column in (
        "candidate_email",
        "created_by_id",
        "nominating_institution_id",
        "nomination_type",
        "programme_id",
        "status",
    ):
        op.create_index(
            op.f(f"ix_programme_nominations_{column}"),
            "programme_nominations",
            [column],
            unique=False,
        )

    op.create_table(
        "batch_trainer_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["batch_id"], ["programme_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "trainer_id", name="uq_batch_trainer_assignment"),
    )
    op.create_index(
        op.f("ix_batch_trainer_assignments_batch_id"),
        "batch_trainer_assignments",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_batch_trainer_assignments_trainer_id"),
        "batch_trainer_assignments",
        ["trainer_id"],
        unique=False,
    )

    op.create_table(
        "application_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("nomination_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(application_id IS NOT NULL AND nomination_id IS NULL) OR "
            "(application_id IS NULL AND nomination_id IS NOT NULL)",
            name="ck_application_documents_single_parent",
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_application_documents_size_positive"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["programme_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["nomination_id"], ["programme_nominations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_documents_application_id"),
        "application_documents",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_documents_nomination_id"),
        "application_documents",
        ["nomination_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("application_documents")
    op.drop_table("batch_trainer_assignments")
    op.drop_table("programme_nominations")
    op.drop_table("programme_applications")
    op.drop_table("programme_batches")
    op.drop_table("programmes")
