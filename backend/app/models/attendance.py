from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
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
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
    BiometricChallengePurpose,
    BiometricChallengeType,
    BiometricVerificationStatus,
    CorrectionStatus,
    KioskDeviceStatus,
)

if TYPE_CHECKING:
    from app.models.auth import Institution, User
    from app.models.profile import ProgrammeEnrollment
    from app.models.programme import Programme, ProgrammeBatch


class KioskDevice(Base, TimestampMixin):
    __tablename__ = "kiosk_devices"
    __table_args__ = (UniqueConstraint("device_code"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    registered_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    device_code: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[KioskDeviceStatus] = mapped_column(
        Enum(KioskDeviceStatus, name="kiosk_device_status", native_enum=False, length=24),
        default=KioskDeviceStatus.ACTIVE,
        server_default=KioskDeviceStatus.ACTIVE.value,
        index=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    institution: Mapped[Institution] = relationship()
    registered_by: Mapped[User] = relationship()


class AttendanceSession(Base, TimestampMixin):
    __tablename__ = "attendance_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_batches.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[AttendanceSessionStatus] = mapped_column(
        Enum(
            AttendanceSessionStatus,
            name="attendance_session_status",
            native_enum=False,
            length=24,
        ),
        default=AttendanceSessionStatus.OPEN,
        server_default=AttendanceSessionStatus.OPEN.value,
        index=True,
    )

    programme: Mapped[Programme] = relationship()
    batch: Mapped[ProgrammeBatch] = relationship()
    created_by: Mapped[User] = relationship()
    check_ins: Mapped[list[AttendanceCheckIn]] = relationship(
        back_populates="attendance_session", cascade="all, delete-orphan"
    )


class AttendanceCheckIn(Base):
    __tablename__ = "attendance_check_ins"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        UniqueConstraint(
            "attendance_session_id",
            "enrollment_id",
            name="uq_attendance_check_in_session_enrollment",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attendance_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    kiosk_device_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kiosk_devices.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    idempotency_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="check_in_attendance_status", native_enum=False, length=24),
        default=AttendanceStatus.PRESENT,
        server_default=AttendanceStatus.PRESENT.value,
        index=True,
    )
    source: Mapped[AttendanceSource] = mapped_column(
        Enum(AttendanceSource, name="attendance_source", native_enum=False, length=24),
        default=AttendanceSource.KIOSK,
        server_default=AttendanceSource.KIOSK.value,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    attendance_session: Mapped[AttendanceSession] = relationship(back_populates="check_ins")
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    kiosk_device: Mapped[KioskDevice | None] = relationship()
    created_by: Mapped[User | None] = relationship()


class AttendanceCorrection(Base, TimestampMixin):
    __tablename__ = "attendance_corrections"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attendance_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    check_in_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("attendance_check_ins.id", ondelete="SET NULL"), index=True
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    previous_status: Mapped[AttendanceStatus | None] = mapped_column(
        Enum(
            AttendanceStatus,
            name="correction_previous_attendance_status",
            native_enum=False,
            length=24,
        )
    )
    requested_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(
            AttendanceStatus,
            name="correction_requested_attendance_status",
            native_enum=False,
            length=24,
        )
    )
    reason: Mapped[str] = mapped_column(Text())
    approval_status: Mapped[CorrectionStatus] = mapped_column(
        Enum(CorrectionStatus, name="correction_status", native_enum=False, length=24),
        default=CorrectionStatus.PENDING,
        server_default=CorrectionStatus.PENDING.value,
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attendance_session: Mapped[AttendanceSession] = relationship()
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    check_in: Mapped[AttendanceCheckIn | None] = relationship()
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])


class BiometricEnrollment(Base, TimestampMixin):
    __tablename__ = "biometric_enrollments"
    __table_args__ = (UniqueConstraint("trainee_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    consent_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("consent_records.id", ondelete="SET NULL"), index=True
    )
    encrypted_embedding: Mapped[bytes] = mapped_column(LargeBinary())
    encryption_nonce: Mapped[bytes] = mapped_column(LargeBinary())
    encryption_key_version: Mapped[str] = mapped_column(String(32))
    provider_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))
    liveness_score: Mapped[float] = mapped_column(Float())

    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])


class BiometricChallenge(Base):
    __tablename__ = "biometric_challenges"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    purpose: Mapped[BiometricChallengePurpose] = mapped_column(
        Enum(
            BiometricChallengePurpose,
            name="biometric_challenge_purpose",
            native_enum=False,
            length=24,
        ),
        index=True,
    )
    challenge_type: Mapped[BiometricChallengeType] = mapped_column(
        Enum(
            BiometricChallengeType,
            name="biometric_challenge_type",
            native_enum=False,
            length=24,
        )
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attendance_session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    kiosk_device_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kiosk_devices.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])
    attendance_session: Mapped[AttendanceSession | None] = relationship()
    kiosk_device: Mapped[KioskDevice | None] = relationship()


class BiometricVerification(Base):
    __tablename__ = "biometric_verifications"
    __table_args__ = (
        UniqueConstraint("challenge_id"),
        UniqueConstraint("idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    challenge_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("biometric_challenges.id", ondelete="RESTRICT"),
        index=True,
    )
    biometric_enrollment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("biometric_enrollments.id", ondelete="SET NULL"),
        index=True,
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    programme_enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programme_enrollments.id", ondelete="CASCADE"),
        index=True,
    )
    attendance_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    kiosk_device_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kiosk_devices.id", ondelete="SET NULL"), index=True
    )
    check_in_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("attendance_check_ins.id", ondelete="SET NULL"), index=True
    )
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    idempotency_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    provider_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float())
    liveness_score: Mapped[float] = mapped_column(Float())
    match_threshold: Mapped[float] = mapped_column(Float())
    status: Mapped[BiometricVerificationStatus] = mapped_column(
        Enum(
            BiometricVerificationStatus,
            name="biometric_verification_status",
            native_enum=False,
            length=24,
        ),
        index=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(String(64))
    review_status: Mapped[CorrectionStatus | None] = mapped_column(
        Enum(
            CorrectionStatus,
            name="biometric_review_status",
            native_enum=False,
            length=24,
        ),
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    challenge: Mapped[BiometricChallenge] = relationship()
    biometric_enrollment: Mapped[BiometricEnrollment | None] = relationship()
    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])
    programme_enrollment: Mapped[ProgrammeEnrollment] = relationship()
    attendance_session: Mapped[AttendanceSession] = relationship()
    kiosk_device: Mapped[KioskDevice | None] = relationship()
    check_in: Mapped[AttendanceCheckIn | None] = relationship()
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
