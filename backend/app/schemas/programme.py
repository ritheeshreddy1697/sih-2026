from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import (
    ApplicationStatus,
    DocumentType,
    EligibilityType,
    NominationSource,
    ProgrammeMode,
    ProgrammeStatus,
)


class InstitutionBrief(BaseModel):
    id: UUID
    name: str
    code: str


class TrainerBrief(BaseModel):
    id: UUID
    full_name: str
    email: str


class BatchTrainerPublic(BaseModel):
    id: UUID
    trainer: TrainerBrief
    assigned_at: datetime


class ProgrammeBatchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    capacity: int = Field(gt=0, le=10000)
    start_date: date
    end_date: date
    location: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_dates(self) -> "ProgrammeBatchCreate":
        if self.end_date < self.start_date:
            raise ValueError("Batch end date must be on or after its start date")
        return self


class ProgrammeBatchPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    capacity: int
    start_date: date
    end_date: date
    location: str | None
    trainers: list[BatchTrainerPublic]


class ProgrammeBase(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    summary: str = Field(min_length=10, max_length=500)
    description: str = Field(min_length=20, max_length=10000)
    mode: ProgrammeMode
    eligibility_criteria: str = Field(min_length=5, max_length=5000)
    eligible_applicant_types: list[EligibilityType] = Field(min_length=1)
    capacity: int = Field(gt=0, le=10000)
    location: str | None = Field(default=None, max_length=255)
    language: str = Field(min_length=2, max_length=80)
    duration_days: int = Field(gt=0, le=3650)
    application_deadline: datetime
    start_date: date
    end_date: date

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_schedule(self) -> "ProgrammeBase":
        if self.end_date < self.start_date:
            raise ValueError("Programme end date must be on or after its start date")
        if self.mode in {ProgrammeMode.OFFLINE, ProgrammeMode.HYBRID} and not self.location:
            raise ValueError("A location is required for offline and hybrid programmes")
        return self


class ProgrammeCreate(ProgrammeBase):
    institution_id: UUID | None = None


class ProgrammeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    summary: str | None = Field(default=None, min_length=10, max_length=500)
    description: str | None = Field(default=None, min_length=20, max_length=10000)
    mode: ProgrammeMode | None = None
    eligibility_criteria: str | None = Field(default=None, min_length=5, max_length=5000)
    eligible_applicant_types: list[EligibilityType] | None = None
    capacity: int | None = Field(default=None, gt=0, le=10000)
    location: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, min_length=2, max_length=80)
    duration_days: int | None = Field(default=None, gt=0, le=3650)
    application_deadline: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ProgrammePublic(BaseModel):
    id: UUID
    institution: InstitutionBrief
    title: str
    code: str
    summary: str
    mode: ProgrammeMode
    status: ProgrammeStatus
    eligible_applicant_types: list[EligibilityType]
    capacity: int
    available_capacity: int
    location: str | None
    language: str
    duration_days: int
    application_deadline: datetime
    start_date: date
    end_date: date
    can_apply: bool
    has_applied: bool


class ProgrammeDetail(ProgrammePublic):
    description: str
    eligibility_criteria: str
    rejection_reason: str | None
    batches: list[ProgrammeBatchPublic]
    application_count: int
    nomination_count: int
    approved_count: int


class TrainerAssignmentCreate(BaseModel):
    trainer_id: UUID


class ProgrammeDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=5000)


class DocumentPublic(BaseModel):
    id: UUID
    document_type: DocumentType
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class ProgrammeApplicationCreate(BaseModel):
    statement: str | None = Field(default=None, max_length=5000)


class ReviewUpdate(BaseModel):
    status: ApplicationStatus
    review_notes: str | None = Field(default=None, max_length=5000)


class ProgrammeApplicationPublic(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    trainee_id: UUID
    trainee_name: str
    trainee_email: str
    status: ApplicationStatus
    statement: str | None
    review_notes: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    documents: list[DocumentPublic]


class ProgrammeNominationCreate(BaseModel):
    nomination_type: EligibilityType
    candidate_full_name: str = Field(min_length=2, max_length=255)
    candidate_email: EmailStr
    candidate_phone: str | None = Field(default=None, max_length=32)
    member_identifier: str | None = Field(default=None, max_length=120)


class ProgrammeNominationPublic(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    nominating_institution: InstitutionBrief
    nomination_type: EligibilityType
    source: NominationSource
    candidate_full_name: str
    candidate_email: str
    candidate_phone: str | None
    member_identifier: str | None
    status: ApplicationStatus
    review_notes: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    documents: list[DocumentPublic]


class BulkNominationResult(BaseModel):
    created: int
    nominations: list[ProgrammeNominationPublic]


class ProgrammeListResponse(BaseModel):
    items: list[ProgrammePublic]
    total: int
