"""Add learning management and assessment tables.

Revision ID: 20260927_04
Revises: 20260927_03
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_04"
down_revision: str | None = "20260927_03"
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
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column(
            "default_language_code", sa.String(length=16), server_default="en", nullable=False
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_programme_id"), "courses", ["programme_id"], unique=True)
    op.create_index(op.f("ix_courses_status"), "courses", ["status"])

    op.create_table(
        "course_languages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "code", name="uq_course_language_code"),
    )
    op.create_index(op.f("ix_course_languages_course_id"), "course_languages", ["course_id"])

    op.create_table(
        "course_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("position > 0", name="ck_course_sections_position_positive"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "position", name="uq_course_section_position"),
    )
    op.create_index(op.f("ix_course_sections_course_id"), "course_sections", ["course_id"])

    op.create_table(
        "course_modules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("position > 0", name="ck_course_modules_position_positive"),
        sa.ForeignKeyConstraint(["section_id"], ["course_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("section_id", "position", name="uq_course_module_position"),
    )
    op.create_index(op.f("ix_course_modules_section_id"), "course_modules", ["section_id"])

    op.create_table(
        "lessons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("lesson_type", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("position > 0", name="ck_lessons_position_positive"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_lessons_duration_positive",
        ),
        sa.ForeignKeyConstraint(["module_id"], ["course_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_id", "position", name="uq_lesson_position"),
    )
    op.create_index(op.f("ix_lessons_lesson_type"), "lessons", ["lesson_type"])
    op.create_index(op.f("ix_lessons_module_id"), "lessons", ["module_id"])

    op.create_table(
        "lesson_contents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("external_url", sa.String(length=1000), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("content", sa.LargeBinary(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes > 0", name="ck_lesson_contents_size_positive"
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "language_code", name="uq_lesson_content_language"),
    )
    op.create_index(op.f("ix_lesson_contents_language_code"), "lesson_contents", ["language_code"])
    op.create_index(op.f("ix_lesson_contents_lesson_id"), "lesson_contents", ["lesson_id"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="in_progress", nullable=False),
        sa.Column("last_position_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("viewed_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_position_seconds >= 0", name="ck_lesson_progress_position_positive"
        ),
        sa.CheckConstraint("viewed_seconds >= 0", name="ck_lesson_progress_viewed_positive"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "lesson_id", name="uq_lesson_progress_enrollment"),
    )
    for column in ("enrollment_id", "lesson_id", "status", "last_accessed_at"):
        op.create_index(op.f(f"ix_lesson_progress_{column}"), "lesson_progress", [column])

    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_score", sa.Float(), server_default="100", nullable=False),
        sa.Column("allowed_content_types", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("max_score > 0", name="ck_assignments_max_score_positive"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["course_modules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assignments_course_id"), "assignments", ["course_id"])
    op.create_index(op.f("ix_assignments_module_id"), "assignments", ["module_id"])

    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("submission_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="submitted", nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("trainer_feedback", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "submission_number > 0", name="ck_assignment_submission_number_positive"
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_assignment_submission_size_positive"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "enrollment_id",
            "submission_number",
            name="uq_assignment_submission_number",
        ),
    )
    for column in ("assignment_id", "enrollment_id", "status"):
        op.create_index(
            op.f(f"ix_assignment_submissions_{column}"), "assignment_submissions", [column]
        )

    op.create_table(
        "question_banks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_banks_course_id"), "question_banks", ["course_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_bank_id", sa.Uuid(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", sa.JSON(), nullable=False),
        sa.Column("correct_option_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("points", sa.Float(), server_default="1", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("position > 0", name="ck_questions_position_positive"),
        sa.CheckConstraint("points > 0", name="ck_questions_points_positive"),
        sa.CheckConstraint(
            "correct_option_index >= 0", name="ck_questions_correct_option_positive"
        ),
        sa.ForeignKeyConstraint(["question_bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_bank_id", "position", name="uq_question_position"),
    )
    op.create_index(op.f("ix_questions_question_bank_id"), "questions", ["question_bank_id"])

    op.create_table(
        "learner_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("question_bank_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("assessment_type", sa.String(length=24), nullable=False),
        sa.Column("attempt_limit", sa.Integer(), server_default="1", nullable=False),
        sa.Column("passing_score_percent", sa.Float(), server_default="60", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "attempt_limit > 0", name="ck_learner_assessments_attempt_limit_positive"
        ),
        sa.CheckConstraint(
            "passing_score_percent >= 0 AND passing_score_percent <= 100",
            name="ck_learner_assessments_passing_score_range",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_bank_id"], ["question_banks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("course_id", "question_bank_id", "assessment_type"):
        op.create_index(op.f(f"ix_learner_assessments_{column}"), "learner_assessments", [column])

    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="in_progress", nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("grading_details", sa.JSON(), nullable=False),
        sa.Column("points_earned", sa.Float(), nullable=True),
        sa.Column("points_available", sa.Float(), nullable=True),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trainer_feedback", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_assessment_attempt_number_positive"),
        sa.CheckConstraint(
            "score_percent IS NULL OR (score_percent >= 0 AND score_percent <= 100)",
            name="ck_assessment_attempt_score_range",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["learner_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "enrollment_id",
            "attempt_number",
            name="uq_assessment_attempt_number",
        ),
    )
    for column in ("assessment_id", "enrollment_id", "status"):
        op.create_index(op.f(f"ix_assessment_attempts_{column}"), "assessment_attempts", [column])


def downgrade() -> None:
    op.drop_table("assessment_attempts")
    op.drop_table("learner_assessments")
    op.drop_table("questions")
    op.drop_table("question_banks")
    op.drop_table("assignment_submissions")
    op.drop_table("assignments")
    op.drop_table("lesson_progress")
    op.drop_table("lesson_contents")
    op.drop_table("lessons")
    op.drop_table("course_modules")
    op.drop_table("course_sections")
    op.drop_table("course_languages")
    op.drop_table("courses")
