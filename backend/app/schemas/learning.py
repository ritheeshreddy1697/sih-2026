from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models import (
    AssessmentAttemptStatus,
    AssessmentType,
    AssignmentSubmissionStatus,
    CourseStatus,
    LearningProgressStatus,
    LessonType,
)


class CourseCreate(BaseModel):
    programme_id: UUID
    title: str = Field(min_length=3, max_length=255)
    summary: str = Field(min_length=10, max_length=1000)
    default_language_code: str = Field(default="en", min_length=2, max_length=16)


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    summary: str | None = Field(default=None, min_length=10, max_length=1000)
    status: CourseStatus | None = None
    default_language_code: str | None = Field(default=None, min_length=2, max_length=16)


class CourseLanguageCreate(BaseModel):
    code: str = Field(min_length=2, max_length=16, pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    name: str = Field(min_length=2, max_length=80)


class CourseLanguagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class SectionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    position: int = Field(gt=0, le=10000)


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    position: int | None = Field(default=None, gt=0, le=10000)


class ModuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=3000)
    position: int = Field(gt=0, le=10000)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=3000)
    position: int | None = Field(default=None, gt=0, le=10000)


class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    lesson_type: LessonType
    position: int = Field(gt=0, le=10000)
    duration_seconds: int | None = Field(default=None, gt=0, le=86400)
    is_required: bool = True

    @model_validator(mode="after")
    def media_has_duration(self) -> "LessonCreate":
        if self.lesson_type in {LessonType.VIDEO, LessonType.AUDIO} and not self.duration_seconds:
            raise ValueError("Video and audio lessons require a duration")
        return self


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    lesson_type: LessonType | None = None
    position: int | None = Field(default=None, gt=0, le=10000)
    duration_seconds: int | None = Field(default=None, gt=0, le=86400)
    is_required: bool | None = None


class LessonProgressPublic(BaseModel):
    status: LearningProgressStatus
    last_position_seconds: int
    viewed_seconds: int
    completed_at: datetime | None


class LessonContentPublic(BaseModel):
    id: UUID
    language_code: str
    title: str
    text_content: str | None
    external_url: str | None
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    has_asset: bool


class LessonPublic(BaseModel):
    id: UUID
    title: str
    lesson_type: LessonType
    position: int
    duration_seconds: int | None
    is_required: bool
    contents: list[LessonContentPublic]
    progress: LessonProgressPublic


class ModulePublic(BaseModel):
    id: UUID
    title: str
    description: str | None
    position: int
    lessons: list[LessonPublic]


class SectionPublic(BaseModel):
    id: UUID
    title: str
    position: int
    modules: list[ModulePublic]


class AssignmentCreate(BaseModel):
    module_id: UUID | None = None
    title: str = Field(min_length=3, max_length=255)
    instructions: str = Field(min_length=10, max_length=10000)
    due_at: datetime | None = None
    max_score: float = Field(default=100, gt=0, le=10000)
    allowed_content_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
        min_length=1,
        max_length=10,
    )
    is_published: bool = False


class AssignmentSubmissionPublic(BaseModel):
    id: UUID
    enrollment_id: UUID
    trainee_name: str
    submission_number: int
    status: AssignmentSubmissionStatus
    filename: str
    content_type: str
    size_bytes: int
    submitted_at: datetime
    score: float | None
    trainer_feedback: str | None
    reviewed_by_name: str | None
    reviewed_at: datetime | None


class AssignmentPublic(BaseModel):
    id: UUID
    module_id: UUID | None
    title: str
    instructions: str
    due_at: datetime | None
    max_score: float
    allowed_content_types: list[str]
    is_published: bool
    latest_submission: AssignmentSubmissionPublic | None


class AssignmentReview(BaseModel):
    score: float | None = Field(default=None, ge=0)
    trainer_feedback: str = Field(min_length=2, max_length=5000)
    status: AssignmentSubmissionStatus = AssignmentSubmissionStatus.REVIEWED

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: AssignmentSubmissionStatus) -> AssignmentSubmissionStatus:
        if value == AssignmentSubmissionStatus.SUBMITTED:
            raise ValueError("Review status must be reviewed or resubmission requested")
        return value


class QuestionBankCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=3000)


class QuestionCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=5000)
    choices: list[str] = Field(min_length=2, max_length=8)
    correct_option_index: int = Field(ge=0, le=7)
    explanation: str | None = Field(default=None, max_length=5000)
    points: float = Field(default=1, gt=0, le=1000)
    position: int = Field(gt=0, le=10000)

    @model_validator(mode="after")
    def validate_correct_option(self) -> "QuestionCreate":
        self.choices = [choice.strip() for choice in self.choices]
        if any(not choice for choice in self.choices):
            raise ValueError("Question choices cannot be empty")
        if self.correct_option_index >= len(self.choices):
            raise ValueError("Correct option index is outside the choices")
        return self


class QuestionManagerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prompt: str
    choices: list[str]
    correct_option_index: int
    explanation: str | None
    points: float
    position: int


class QuestionBankPublic(BaseModel):
    id: UUID
    title: str
    description: str | None
    questions: list[QuestionManagerPublic]


class AssessmentCreate(BaseModel):
    question_bank_id: UUID
    title: str = Field(min_length=3, max_length=255)
    instructions: str | None = Field(default=None, max_length=5000)
    assessment_type: AssessmentType
    attempt_limit: int = Field(default=1, gt=0, le=20)
    passing_score_percent: float = Field(default=60, ge=0, le=100)
    is_published: bool = False


class AssessmentSummary(BaseModel):
    id: UUID
    title: str
    instructions: str | None
    assessment_type: AssessmentType
    attempt_limit: int
    attempts_used: int
    attempts_remaining: int
    passing_score_percent: float
    best_score_percent: float | None
    passed: bool
    is_published: bool


class QuestionForAttempt(BaseModel):
    id: UUID
    prompt: str
    choices: list[str]
    points: float
    position: int


class GradingDetailPublic(BaseModel):
    question_id: UUID
    selected_option_index: int | None
    correct: bool
    points_earned: float
    explanation: str | None


class AssessmentAttemptPublic(BaseModel):
    id: UUID
    assessment_id: UUID
    assessment_title: str
    attempt_number: int
    status: AssessmentAttemptStatus
    questions: list[QuestionForAttempt]
    score_percent: float | None
    points_earned: float | None
    points_available: float | None
    passed: bool | None
    grading_details: list[GradingDetailPublic]
    trainer_feedback: str | None
    started_at: datetime
    submitted_at: datetime | None


class AssessmentAnswerInput(BaseModel):
    question_id: UUID
    option_index: int = Field(ge=0, le=7)


class AssessmentSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[AssessmentAnswerInput] = Field(min_length=1)

    @field_validator("answers")
    @classmethod
    def unique_answers(cls, value: list[AssessmentAnswerInput]) -> list[AssessmentAnswerInput]:
        identifiers = [item.question_id for item in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Submit one answer per question")
        return value


class AssessmentFeedback(BaseModel):
    trainer_feedback: str = Field(min_length=2, max_length=5000)


class ProgressHeartbeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position_seconds: int = Field(ge=0, le=86400)
    elapsed_seconds: int = Field(gt=0, le=30)


class ProgressSyncEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    lesson_id: UUID
    action: Literal["start", "heartbeat", "complete"]
    captured_at: datetime
    position_seconds: int | None = Field(default=None, ge=0, le=86400)
    elapsed_seconds: int | None = Field(default=None, gt=0, le=30)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ProgressSyncEvent":
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        if self.action == "heartbeat":
            if self.position_seconds is None or self.elapsed_seconds is None:
                raise ValueError("Heartbeat events require position and elapsed seconds")
        elif self.position_seconds is not None or self.elapsed_seconds is not None:
            raise ValueError("Only heartbeat events may include position or elapsed seconds")
        return self


class ProgressSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[ProgressSyncEvent] = Field(min_length=1, max_length=250)

    @field_validator("events")
    @classmethod
    def unique_idempotency_keys(
        cls, value: list[ProgressSyncEvent]
    ) -> list[ProgressSyncEvent]:
        keys = [item.idempotency_key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Each progress event must have a unique idempotency key")
        return value


class ProgressSyncResult(BaseModel):
    idempotency_key: UUID
    lesson_id: UUID
    result: Literal["applied", "duplicate", "rejected"]
    detail: str
    progress: LessonProgressPublic | None


class ProgressSyncResponse(BaseModel):
    items: list[ProgressSyncResult]
    applied: int
    duplicates: int
    rejected: int


class CourseListItem(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    title: str
    summary: str
    status: CourseStatus
    languages: list[CourseLanguagePublic]
    lesson_count: int
    completed_lesson_count: int
    progress_percent: int
    resume_lesson_id: UUID | None
    resume_position_seconds: int
    can_manage: bool


class CourseDetail(CourseListItem):
    default_language_code: str
    sections: list[SectionPublic]
    assignments: list[AssignmentPublic]
    assessments: list[AssessmentSummary]


class CourseListResponse(BaseModel):
    items: list[CourseListItem]
    total: int


class ExternalContentInput(BaseModel):
    url: HttpUrl
