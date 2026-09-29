from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    EmployerVerificationStatus,
    EmploymentType,
    JobApplicationStatus,
    JobStatus,
    WorkplaceMode,
)


class EmployerCompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry: str = Field(min_length=2, max_length=160)
    website: str | None = Field(default=None, max_length=500)
    company_size: str | None = Field(default=None, max_length=80)
    description: str = Field(min_length=20, max_length=4000)
    headquarters: str = Field(min_length=2, max_length=255)
    registration_number: str | None = Field(default=None, max_length=120)


class EmployerVerificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EmployerVerificationStatus
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_decision(self) -> "EmployerVerificationUpdate":
        if self.status == EmployerVerificationStatus.PENDING:
            raise ValueError("Verification decisions must be verified or rejected")
        if self.status == EmployerVerificationStatus.REJECTED and not self.notes:
            raise ValueError("Rejection notes are required")
        return self


class EmployerProfilePublic(EmployerCompanyUpdate):
    id: UUID
    institution_id: UUID
    company_name: str
    institution_code: str
    contact_name: str
    contact_email: str
    verification_status: EmployerVerificationStatus
    verification_notes: str | None
    verified_at: datetime | None
    updated_at: datetime


class EmploymentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str | None = Field(default=None, max_length=255)
    professional_summary: str | None = Field(default=None, max_length=4000)
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    open_to_work: bool = True


class VerifiedSkillPublic(BaseModel):
    name: str
    certificate_id: UUID
    certificate_number: str


class EmploymentProfilePublic(EmploymentProfileUpdate):
    trainee_id: UUID
    full_name: str
    location: str | None
    career_interests: list[str]
    placement_visibility_consent: bool
    data_sharing_consent: bool
    verified_skills: list[VerifiedSkillPublic]
    resume_filename: str | None
    resume_size_bytes: int | None
    resume_uploaded_at: datetime | None


class ProgrammeRequirementPublic(BaseModel):
    id: UUID
    code: str
    title: str


class MatchBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    skill_score: int = Field(ge=0, le=40)
    course_score: int = Field(ge=0, le=25)
    location_score: int = Field(ge=0, le=20)
    interest_score: int = Field(ge=0, le=15)
    reasons: list[str]
    gaps: list[str]


class JobBase(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=20, max_length=10000)
    location: str = Field(min_length=2, max_length=255)
    employment_type: EmploymentType
    workplace_mode: WorkplaceMode
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    preferred_skills: list[str] = Field(default_factory=list, max_length=30)
    minimum_experience_years: int = Field(default=0, ge=0, le=60)
    vacancies: int = Field(default=1, ge=1, le=10000)
    salary_minimum: float | None = Field(default=None, ge=0)
    salary_maximum: float | None = Field(default=None, ge=0)
    application_deadline: datetime | None = None
    required_programme_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_salary(self) -> "JobBase":
        if (
            self.salary_minimum is not None
            and self.salary_maximum is not None
            and self.salary_maximum < self.salary_minimum
        ):
            raise ValueError("Maximum salary must be greater than or equal to minimum salary")
        self.required_skills = _clean_terms(self.required_skills)
        self.preferred_skills = _clean_terms(self.preferred_skills)
        return self


class JobCreate(JobBase):
    model_config = ConfigDict(extra="forbid")


class JobUpdate(JobBase):
    model_config = ConfigDict(extra="forbid")


class JobPublic(BaseModel):
    id: UUID
    employer_profile_id: UUID
    company_name: str
    title: str
    description: str
    location: str
    employment_type: EmploymentType
    workplace_mode: WorkplaceMode
    required_skills: list[str]
    preferred_skills: list[str]
    minimum_experience_years: int
    vacancies: int
    salary_minimum: float | None
    salary_maximum: float | None
    application_deadline: datetime | None
    status: JobStatus
    published_at: datetime | None
    closed_at: datetime | None
    required_programmes: list[ProgrammeRequirementPublic]
    saved: bool = False
    application_status: JobApplicationStatus | None = None
    match: MatchBreakdown | None = None


class CertificateSummary(BaseModel):
    id: UUID
    certificate_number: str
    title: str
    programme_title: str
    programme_code: str
    issued_at: datetime
    expires_at: datetime | None
    verification_url: str


class CandidateContact(BaseModel):
    email: str
    phone: str | None


class CandidatePublic(BaseModel):
    trainee_id: UUID
    full_name: str
    headline: str | None
    professional_summary: str | None
    location: str | None
    verified_skills: list[str]
    career_interests: list[str]
    certificates: list[CertificateSummary]
    contact: CandidateContact | None
    contact_locked_reason: str | None
    resume_available: bool
    resume_download_allowed: bool
    shortlisted: bool
    match: MatchBreakdown | None


class CandidateShortlistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainee_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class JobApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cover_note: str | None = Field(default=None, max_length=4000)


class JobApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobApplicationStatus
    interview_at: datetime | None = None
    interview_mode: str | None = Field(default=None, max_length=80)
    interview_details: str | None = Field(default=None, max_length=2000)
    employer_notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_interview(self) -> "JobApplicationStatusUpdate":
        if self.status == JobApplicationStatus.INTERVIEW_SCHEDULED:
            if not self.interview_at or not self.interview_mode:
                raise ValueError("Interview date and mode are required")
        if self.status in {JobApplicationStatus.APPLIED, JobApplicationStatus.WITHDRAWN}:
            raise ValueError("Employers cannot set this application status")
        return self


class JobApplicationPublic(BaseModel):
    id: UUID
    job_id: UUID
    job_title: str
    company_name: str
    trainee_id: UUID
    trainee_name: str
    status: JobApplicationStatus
    cover_note: str | None
    applied_at: datetime
    status_updated_at: datetime
    interview_at: datetime | None
    interview_mode: str | None
    interview_details: str | None
    employer_notes: str | None
    certificates: list[CertificateSummary]
    contact: CandidateContact | None


class EmployerWorkspacePublic(BaseModel):
    profile: EmployerProfilePublic
    jobs: list[JobPublic]
    applications: list[JobApplicationPublic]
    shortlisted_count: int


class TraineeEmploymentWorkspacePublic(BaseModel):
    profile: EmploymentProfilePublic
    recommendations: list[JobPublic]
    saved_jobs: list[JobPublic]
    applications: list[JobApplicationPublic]


def _clean_terms(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))
