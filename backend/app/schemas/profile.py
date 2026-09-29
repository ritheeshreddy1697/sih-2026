from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import (
    AccountStatus,
    AssessmentResult,
    AttendanceStatus,
    DocumentValidationStatus,
    EnrollmentStatus,
    InstitutionType,
    ProfileDocumentType,
)


class InstitutionSummary(BaseModel):
    id: UUID
    name: str
    code: str
    institution_type: InstitutionType


class InstitutionInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    institution_type: InstitutionType
    parent_id: UUID | None = None
    state: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    website: str | None = Field(default=None, max_length=500)
    registration_number: str | None = Field(default=None, max_length=120)
    profile_summary: str | None = Field(default=None, max_length=4000)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class InstitutionCreate(InstitutionInput):
    pass


class InstitutionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    institution_type: InstitutionType | None = None
    parent_id: UUID | None = None
    state: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    website: str | None = Field(default=None, max_length=500)
    registration_number: str | None = Field(default=None, max_length=120)
    profile_summary: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class InstitutionPublic(InstitutionSummary):
    parent: InstitutionSummary | None
    state: str | None
    district: str | None
    address: str | None
    contact_email: str | None
    contact_phone: str | None
    website: str | None
    registration_number: str | None
    profile_summary: str | None
    is_active: bool
    is_demo: bool
    child_count: int
    children: list[InstitutionSummary] = Field(default_factory=list)


class InstitutionListResponse(BaseModel):
    items: list[InstitutionPublic]
    total: int
    page: int
    page_size: int
    pages: int


class PersonalProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    designation: str | None = Field(default=None, max_length=160)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=80)
    alternate_email: EmailStr | None = None
    address_line: str | None = Field(default=None, max_length=2000)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=12, pattern=r"^[0-9A-Za-z -]*$")
    preferred_language: str | None = Field(default=None, max_length=80)
    preferred_location: str | None = Field(default=None, max_length=160)
    career_interests: str | None = Field(default=None, max_length=3000)
    skills: list[str] | None = Field(default=None, max_length=30)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if any(len(item) > 80 for item in cleaned):
            raise ValueError("Each skill must be 80 characters or fewer")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def date_of_birth_is_past(cls, value: date | None) -> date | None:
        if value and value >= date.today():
            raise ValueError("Date of birth must be in the past")
        return value


class EducationCreate(BaseModel):
    qualification: str = Field(min_length=2, max_length=160)
    field_of_study: str | None = Field(default=None, max_length=160)
    institution_name: str = Field(min_length=2, max_length=255)
    completion_year: int | None = Field(default=None, ge=1900, le=date.today().year + 10)
    grade: str | None = Field(default=None, max_length=80)
    is_highest_qualification: bool = False


class EducationPublic(EducationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class EmploymentCreate(BaseModel):
    employer_name: str = Field(min_length=2, max_length=255)
    job_title: str = Field(min_length=2, max_length=160)
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    responsibilities: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_dates(self) -> "EmploymentCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Employment end date must be on or after its start date")
        if self.is_current and self.end_date:
            raise ValueError("Current employment cannot have an end date")
        return self


class EmploymentPublic(EmploymentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class MembershipCreate(BaseModel):
    institution_name: str = Field(min_length=2, max_length=255)
    membership_type: str = Field(min_length=2, max_length=120)
    member_number: str | None = Field(default=None, max_length=120)
    joined_on: date | None = None
    is_active: bool = True


class MembershipPublic(MembershipCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class ProfileDocumentPublic(BaseModel):
    id: UUID
    document_type: ProfileDocumentType
    filename: str
    content_type: str
    size_bytes: int
    validation_status: DocumentValidationStatus
    validation_notes: str | None
    validated_by_name: str | None
    validated_at: datetime | None
    uploaded_at: datetime


class DocumentValidationUpdate(BaseModel):
    status: DocumentValidationStatus
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def rejection_has_notes(self) -> "DocumentValidationUpdate":
        if self.status == DocumentValidationStatus.PENDING:
            raise ValueError("Validation status must be verified or rejected")
        if self.status == DocumentValidationStatus.REJECTED and not self.notes:
            raise ValueError("Add a reason when rejecting a document")
        return self


class AttendancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_date: date
    topic: str
    status: AttendanceStatus


class AssessmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    score: float | None
    maximum_score: float | None
    result: AssessmentResult
    assessed_at: datetime | None


class CertificatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    certificate_number: str
    title: str
    issued_at: datetime


class EnrollmentPublic(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    batch_name: str | None
    status: EnrollmentStatus
    enrolled_at: datetime
    completed_at: datetime | None
    attendance: list[AttendancePublic]
    assessments: list[AssessmentPublic]
    certificates: list[CertificatePublic]


class ConsentPreferences(BaseModel):
    placement_visibility_consent: bool
    communication_consent: bool
    data_sharing_consent: bool


class AuditEventPublic(BaseModel):
    id: UUID
    event_type: str
    success: bool
    actor_name: str
    details: dict[str, Any]
    created_at: datetime


class ProfileCompletion(BaseModel):
    percent: int
    completed_sections: list[str]
    missing_sections: list[str]


class TraineeListItem(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    phone: str | None
    institution: InstitutionSummary | None
    account_status: AccountStatus
    preferred_language: str | None
    preferred_location: str | None
    state: str | None
    skills: list[str]
    completion_percent: int
    pending_documents: int
    is_demo: bool


class TraineeListResponse(BaseModel):
    items: list[TraineeListItem]
    total: int
    page: int
    page_size: int
    pages: int


class TrainerListItem(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    phone: str | None
    designation: str | None
    institution: InstitutionSummary | None
    account_status: AccountStatus


class TrainerListResponse(BaseModel):
    items: list[TrainerListItem]
    total: int
    page: int
    page_size: int
    pages: int


class TraineeProfileDetail(TraineeListItem):
    designation: str | None
    date_of_birth: date | None
    gender: str | None
    alternate_email: str | None
    address_line: str | None
    city: str | None
    postal_code: str | None
    career_interests: str | None
    completion: ProfileCompletion
    education: list[EducationPublic]
    employment: list[EmploymentPublic]
    memberships: list[MembershipPublic]
    documents: list[ProfileDocumentPublic]
    enrollments: list[EnrollmentPublic]
    consent_preferences: ConsentPreferences
    audit_history: list[AuditEventPublic]
