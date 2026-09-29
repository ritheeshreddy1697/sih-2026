from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    AssessmentAttemptStatus,
    AssessmentType,
    AssignmentSubmissionStatus,
    CourseStatus,
    LearningProgressStatus,
    LessonType,
)

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.profile import ProgrammeEnrollment
    from app.models.programme import Programme


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programmes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(String(1000))
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status", native_enum=False, length=24),
        default=CourseStatus.DRAFT,
        server_default=CourseStatus.DRAFT.value,
        index=True,
    )
    default_language_code: Mapped[str] = mapped_column(
        String(16), default="en", server_default="en"
    )

    programme: Mapped[Programme] = relationship()
    created_by: Mapped[User] = relationship()
    languages: Mapped[list[CourseLanguage]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseLanguage.name"
    )
    sections: Mapped[list[CourseSection]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseSection.position"
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Assignment.created_at"
    )
    question_banks: Mapped[list[QuestionBank]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[LearnerAssessment]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class CourseLanguage(Base):
    __tablename__ = "course_languages"
    __table_args__ = (UniqueConstraint("course_id", "code", name="uq_course_language_code"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(80))

    course: Mapped[Course] = relationship(back_populates="languages")


class CourseSection(Base, TimestampMixin):
    __tablename__ = "course_sections"
    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_course_section_position"),
        CheckConstraint("position > 0", name="ck_course_sections_position_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer())

    course: Mapped[Course] = relationship(back_populates="sections")
    modules: Mapped[list[CourseModule]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="CourseModule.position"
    )


class CourseModule(Base, TimestampMixin):
    __tablename__ = "course_modules"
    __table_args__ = (
        UniqueConstraint("section_id", "position", name="uq_course_module_position"),
        CheckConstraint("position > 0", name="ck_course_modules_position_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    section_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_sections.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text())
    position: Mapped[int] = mapped_column(Integer())

    section: Mapped[CourseSection] = relationship(back_populates="modules")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Lesson.position"
    )


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("module_id", "position", name="uq_lesson_position"),
        CheckConstraint("position > 0", name="ck_lessons_position_positive"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_lessons_duration_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    module_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_modules.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    lesson_type: Mapped[LessonType] = mapped_column(
        Enum(LessonType, name="lesson_type", native_enum=False, length=32), index=True
    )
    position: Mapped[int] = mapped_column(Integer())
    duration_seconds: Mapped[int | None] = mapped_column(Integer())
    is_required: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    module: Mapped[CourseModule] = relationship(back_populates="lessons")
    contents: Mapped[list[LessonContent]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonContent.language_code",
    )


class LessonContent(Base, TimestampMixin):
    __tablename__ = "lesson_contents"
    __table_args__ = (
        UniqueConstraint("lesson_id", "language_code", name="uq_lesson_content_language"),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes > 0", name="ck_lesson_contents_size_positive"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lesson_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    language_code: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(255))
    text_content: Mapped[str | None] = mapped_column(Text())
    external_url: Mapped[str | None] = mapped_column(String(1000))
    filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer())
    content: Mapped[bytes | None] = mapped_column(LargeBinary())

    lesson: Mapped[Lesson] = relationship(back_populates="contents")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "lesson_id", name="uq_lesson_progress_enrollment"),
        CheckConstraint("last_position_seconds >= 0", name="ck_lesson_progress_position_positive"),
        CheckConstraint("viewed_seconds >= 0", name="ck_lesson_progress_viewed_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[LearningProgressStatus] = mapped_column(
        Enum(
            LearningProgressStatus,
            name="learning_progress_status",
            native_enum=False,
            length=24,
        ),
        default=LearningProgressStatus.IN_PROGRESS,
        server_default=LearningProgressStatus.IN_PROGRESS.value,
        index=True,
    )
    last_position_seconds: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    viewed_seconds: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    lesson: Mapped[Lesson] = relationship()


class LearningProgressSyncEvent(Base):
    __tablename__ = "learning_progress_sync_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint(
            "position_seconds IS NULL OR position_seconds >= 0",
            name="ck_learning_sync_position_positive",
        ),
        CheckConstraint(
            "elapsed_seconds IS NULL OR (elapsed_seconds > 0 AND elapsed_seconds <= 30)",
            name="ck_learning_sync_elapsed_bounded",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    idempotency_key: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programme_enrollments.id", ondelete="CASCADE"),
        index=True,
    )
    lesson_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    position_seconds: Mapped[int | None] = mapped_column(Integer())
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer())
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship()
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    lesson: Mapped[Lesson] = relationship()


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"
    __table_args__ = (CheckConstraint("max_score > 0", name="ck_assignments_max_score_positive"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    module_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_modules.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text())
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_score: Mapped[float] = mapped_column(Float(), default=100, server_default="100")
    allowed_content_types: Mapped[list[str]] = mapped_column(JSON(), default=list)
    is_published: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")

    course: Mapped[Course] = relationship(back_populates="assignments")
    module: Mapped[CourseModule | None] = relationship()
    submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "enrollment_id",
            "submission_number",
            name="uq_assignment_submission_number",
        ),
        CheckConstraint("submission_number > 0", name="ck_assignment_submission_number_positive"),
        CheckConstraint("size_bytes > 0", name="ck_assignment_submission_size_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    submission_number: Mapped[int] = mapped_column(Integer())
    status: Mapped[AssignmentSubmissionStatus] = mapped_column(
        Enum(
            AssignmentSubmissionStatus,
            name="assignment_submission_status",
            native_enum=False,
            length=32,
        ),
        default=AssignmentSubmissionStatus.SUBMITTED,
        server_default=AssignmentSubmissionStatus.SUBMITTED.value,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer())
    content: Mapped[bytes] = mapped_column(LargeBinary())
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float())
    trainer_feedback: Mapped[str | None] = mapped_column(Text())
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    reviewed_by: Mapped[User | None] = relationship()


class QuestionBank(Base, TimestampMixin):
    __tablename__ = "question_banks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text())

    course: Mapped[Course] = relationship(back_populates="question_banks")
    questions: Mapped[list[Question]] = relationship(
        back_populates="bank", cascade="all, delete-orphan", order_by="Question.position"
    )
    assessments: Mapped[list[LearnerAssessment]] = relationship(back_populates="question_bank")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("question_bank_id", "position", name="uq_question_position"),
        CheckConstraint("position > 0", name="ck_questions_position_positive"),
        CheckConstraint("points > 0", name="ck_questions_points_positive"),
        CheckConstraint("correct_option_index >= 0", name="ck_questions_correct_option_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    question_bank_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), index=True
    )
    prompt: Mapped[str] = mapped_column(Text())
    choices: Mapped[list[str]] = mapped_column(JSON())
    correct_option_index: Mapped[int] = mapped_column(Integer())
    explanation: Mapped[str | None] = mapped_column(Text())
    points: Mapped[float] = mapped_column(Float(), default=1, server_default="1")
    position: Mapped[int] = mapped_column(Integer())

    bank: Mapped[QuestionBank] = relationship(back_populates="questions")


class LearnerAssessment(Base, TimestampMixin):
    __tablename__ = "learner_assessments"
    __table_args__ = (
        CheckConstraint("attempt_limit > 0", name="ck_learner_assessments_attempt_limit_positive"),
        CheckConstraint(
            "passing_score_percent >= 0 AND passing_score_percent <= 100",
            name="ck_learner_assessments_passing_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    question_bank_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_banks.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str | None] = mapped_column(Text())
    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessment_type", native_enum=False, length=24), index=True
    )
    attempt_limit: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")
    passing_score_percent: Mapped[float] = mapped_column(Float(), default=60, server_default="60")
    is_published: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")

    course: Mapped[Course] = relationship(back_populates="assessments")
    question_bank: Mapped[QuestionBank] = relationship(back_populates="assessments")
    attempts: Mapped[list[AssessmentAttempt]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "enrollment_id",
            "attempt_number",
            name="uq_assessment_attempt_number",
        ),
        CheckConstraint("attempt_number > 0", name="ck_assessment_attempt_number_positive"),
        CheckConstraint(
            "score_percent IS NULL OR (score_percent >= 0 AND score_percent <= 100)",
            name="ck_assessment_attempt_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learner_assessments.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer())
    status: Mapped[AssessmentAttemptStatus] = mapped_column(
        Enum(
            AssessmentAttemptStatus,
            name="assessment_attempt_status",
            native_enum=False,
            length=24,
        ),
        default=AssessmentAttemptStatus.IN_PROGRESS,
        server_default=AssessmentAttemptStatus.IN_PROGRESS.value,
        index=True,
    )
    question_ids: Mapped[list[str]] = mapped_column(JSON(), default=list)
    answers: Mapped[dict[str, int]] = mapped_column(JSON(), default=dict)
    grading_details: Mapped[list[dict[str, Any]]] = mapped_column(JSON(), default=list)
    points_earned: Mapped[float | None] = mapped_column(Float())
    points_available: Mapped[float | None] = mapped_column(Float())
    score_percent: Mapped[float | None] = mapped_column(Float())
    passed: Mapped[bool | None] = mapped_column(Boolean())
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trainer_feedback: Mapped[str | None] = mapped_column(Text())
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assessment: Mapped[LearnerAssessment] = relationship(back_populates="attempts")
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    reviewed_by: Mapped[User | None] = relationship()
