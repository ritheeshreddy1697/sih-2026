from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CertificateState, EnrollmentStatus


class CertificatePolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_title: str = Field(min_length=3, max_length=255)
    minimum_course_completion_percent: float = Field(ge=0, le=100)
    minimum_attendance_percent: float = Field(ge=0, le=100)
    minimum_assessment_score_percent: float = Field(ge=0, le=100)
    validity_days: int | None = Field(default=None, gt=0, le=36500)
    is_active: bool = True


class CertificatePolicyPublic(CertificatePolicyUpdate):
    id: UUID
    programme_id: UUID
    configured_by_name: str
    updated_at: datetime


class CertificateMetrics(BaseModel):
    course_completion_percent: float
    attendance_percent: float
    assessment_score_percent: float


class EligibilityMetrics(CertificateMetrics):
    required_lessons: int
    completed_lessons: int
    attendance_sessions: int
    attended_sessions: int


class CertificateAuditEvent(BaseModel):
    event_type: str
    actor_name: str | None
    details: dict[str, str | float | bool | None]
    created_at: datetime


class CertificateRecordPublic(BaseModel):
    id: UUID
    enrollment_id: UUID
    certificate_number: str
    title: str
    recipient_name: str
    recipient_email: str
    programme_id: UUID
    programme_title: str
    programme_code: str
    institution_name: str
    state: CertificateState
    valid: bool
    metrics: CertificateMetrics
    issued_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    revocation_reason: str | None
    verification_url: str
    audit_history: list[CertificateAuditEvent] = Field(default_factory=list)


class CertificateCandidatePublic(BaseModel):
    enrollment_id: UUID
    trainee_name: str
    trainee_email: str
    enrollment_status: EnrollmentStatus
    metrics: EligibilityMetrics
    eligible: bool
    reasons: list[str]
    certificate: CertificateRecordPublic | None


class CertificateIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_id: UUID


class CertificateRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=1000)


class CertificateVerificationPublic(BaseModel):
    certificate_number: str
    title: str
    recipient_name: str
    programme_title: str
    institution_name: str
    state: CertificateState
    valid: bool
    issued_at: datetime
    expires_at: datetime | None


class SkillWalletPublic(BaseModel):
    certificates: list[CertificateRecordPublic]
    total: int
    valid_count: int
