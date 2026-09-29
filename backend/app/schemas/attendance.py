from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import (
    AttendanceSessionStatus,
    AttendanceStatus,
    BiometricChallengeType,
    BiometricVerificationStatus,
    CorrectionStatus,
    KioskDeviceStatus,
)


class AttendanceSessionCreate(BaseModel):
    programme_id: UUID
    batch_id: UUID
    title: str = Field(min_length=3, max_length=255)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid_window(self) -> "AttendanceSessionCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Attendance session end time must be after its start time")
        return self


class AttendanceSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: AttendanceSessionStatus | None = None


class AttendanceSessionPublic(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    batch_id: UUID
    batch_name: str
    title: str
    starts_at: datetime
    ends_at: datetime
    status: AttendanceSessionStatus
    check_in_count: int


class SessionQrPublic(BaseModel):
    payload: str
    expires_at: datetime
    refresh_after_seconds: int


class TraineeIdentityPublic(BaseModel):
    trainee_id: UUID
    full_name: str
    identity_code: str
    qr_payload: str


class SessionTraineePublic(TraineeIdentityPublic):
    enrollment_id: UUID
    checked_in: bool
    attendance_status: AttendanceStatus | None


class KioskDeviceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    institution_id: UUID | None = None


class KioskDevicePublic(BaseModel):
    id: UUID
    institution_id: UUID
    institution_name: str
    name: str
    device_code: str
    status: KioskDeviceStatus
    last_seen_at: datetime | None
    created_at: datetime


class KioskDeviceRegistered(KioskDevicePublic):
    device_token: str


class KioskPairRequest(BaseModel):
    session_qr: str = Field(min_length=20)


class KioskSessionPublic(BaseModel):
    session_id: UUID
    title: str
    programme_title: str
    programme_code: str
    batch_name: str
    starts_at: datetime
    ends_at: datetime
    offline_until: datetime


class OfflineCheckIn(BaseModel):
    idempotency_key: UUID
    session_id: UUID
    trainee_qr: str = Field(min_length=20)
    captured_at: datetime


class CheckInSyncRequest(BaseModel):
    items: list[OfflineCheckIn] = Field(min_length=1, max_length=200)


class CheckInSyncItem(BaseModel):
    idempotency_key: UUID
    result: str
    check_in_id: UUID | None = None
    trainee_name: str | None = None
    detail: str


class CheckInSyncResponse(BaseModel):
    items: list[CheckInSyncItem]
    accepted: int
    duplicates: int
    rejected: int


class AttendanceCorrectionCreate(BaseModel):
    enrollment_id: UUID
    requested_status: AttendanceStatus
    reason: str = Field(min_length=5, max_length=1000)


class AttendanceCorrectionReview(BaseModel):
    decision: CorrectionStatus
    review_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def final_decision_only(self) -> "AttendanceCorrectionReview":
        if self.decision == CorrectionStatus.PENDING:
            raise ValueError("Review decision must be approved or rejected")
        return self


class AttendanceCorrectionPublic(BaseModel):
    id: UUID
    attendance_session_id: UUID
    session_title: str
    enrollment_id: UUID
    trainee_name: str
    previous_status: AttendanceStatus | None
    requested_status: AttendanceStatus
    reason: str
    approval_status: CorrectionStatus
    requested_by_name: str
    reviewed_by_name: str | None
    review_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None


class AttendanceReportRow(BaseModel):
    enrollment_id: UUID
    trainee_id: UUID
    trainee_name: str
    trainee_email: str
    status: AttendanceStatus
    captured_at: datetime | None
    checked_in_at: datetime | None
    device_code: str | None
    source: str | None
    biometric_enrolled: bool


class AttendanceReportPublic(BaseModel):
    session: AttendanceSessionPublic
    expected_count: int
    present_count: int
    absent_count: int
    excused_count: int
    attendance_percent: float
    rows: list[AttendanceReportRow]


class BiometricEnrollmentPublic(BaseModel):
    enrolled: bool
    enrolled_at: datetime | None
    provider_name: str
    provider_mode: str
    is_demo: bool
    consent_version: str
    privacy_notice: str


class BiometricChallengePublic(BaseModel):
    id: UUID
    challenge_type: BiometricChallengeType
    instruction: str
    expires_at: datetime
    trainee_name: str
    provider_mode: str
    is_demo: bool


class KioskBiometricChallengeCreate(BaseModel):
    session_id: UUID
    identity_code: str = Field(min_length=8, max_length=32, pattern=r"^NCCT-[A-Za-z0-9-]+$")


class BiometricVerificationPublic(BaseModel):
    id: UUID
    trainee_id: UUID
    trainee_name: str
    session_id: UUID
    session_title: str
    status: BiometricVerificationStatus
    review_status: CorrectionStatus | None
    confidence: float
    threshold: float
    liveness_score: float
    attendance_recorded: bool
    check_in_id: UUID | None
    detail: str
    captured_at: datetime
    created_at: datetime


class BiometricReviewRequest(BaseModel):
    decision: CorrectionStatus
    review_notes: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def final_decision_only(self) -> "BiometricReviewRequest":
        if self.decision == CorrectionStatus.PENDING:
            raise ValueError("Review decision must be approved or rejected")
        return self


class MessagePublic(BaseModel):
    message: str
