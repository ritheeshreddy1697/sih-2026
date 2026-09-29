from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
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
    AssessmentResult,
    AttendanceStatus,
    DocumentValidationStatus,
    EnrollmentStatus,
    ProfileDocumentType,
)

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.programme import Programme, ProgrammeBatch


class TraineeProfile(Base, TimestampMixin):
    __tablename__ = "trainee_profiles"
    __table_args__ = (
        CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_trainee_profiles_completion_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date())
    gender: Mapped[str | None] = mapped_column(String(80))
    alternate_email: Mapped[str | None] = mapped_column(String(320))
    address_line: Mapped[str | None] = mapped_column(Text())
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120), index=True)
    postal_code: Mapped[str | None] = mapped_column(String(12))
    preferred_language: Mapped[str | None] = mapped_column(String(80), index=True)
    preferred_location: Mapped[str | None] = mapped_column(String(160), index=True)
    career_interests: Mapped[str | None] = mapped_column(Text())
    skills: Mapped[list[str]] = mapped_column(JSON(), default=list)
    placement_visibility_consent: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="false"
    )
    communication_consent: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default="true"
    )
    data_sharing_consent: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="false"
    )
    completion_percent: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    is_demo: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    qr_identity_version: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")

    user: Mapped[User] = relationship(back_populates="trainee_profile")
    education: Mapped[list[EducationRecord]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    employment: Mapped[list[EmploymentRecord]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    memberships: Mapped[list[CooperativeMembership]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    documents: Mapped[list[TraineeDocument]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class EducationRecord(Base, TimestampMixin):
    __tablename__ = "education_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trainee_profiles.id", ondelete="CASCADE"), index=True
    )
    qualification: Mapped[str] = mapped_column(String(160))
    field_of_study: Mapped[str | None] = mapped_column(String(160))
    institution_name: Mapped[str] = mapped_column(String(255))
    completion_year: Mapped[int | None] = mapped_column(Integer())
    grade: Mapped[str | None] = mapped_column(String(80))
    is_highest_qualification: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="false"
    )

    profile: Mapped[TraineeProfile] = relationship(back_populates="education")


class EmploymentRecord(Base, TimestampMixin):
    __tablename__ = "employment_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trainee_profiles.id", ondelete="CASCADE"), index=True
    )
    employer_name: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date | None] = mapped_column(Date())
    is_current: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    responsibilities: Mapped[str | None] = mapped_column(Text())

    profile: Mapped[TraineeProfile] = relationship(back_populates="employment")


class CooperativeMembership(Base, TimestampMixin):
    __tablename__ = "cooperative_memberships"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trainee_profiles.id", ondelete="CASCADE"), index=True
    )
    institution_name: Mapped[str] = mapped_column(String(255))
    membership_type: Mapped[str] = mapped_column(String(120))
    member_number: Mapped[str | None] = mapped_column(String(120))
    joined_on: Mapped[date | None] = mapped_column(Date())
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    profile: Mapped[TraineeProfile] = relationship(back_populates="memberships")


class TraineeDocument(Base):
    __tablename__ = "trainee_documents"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="ck_trainee_documents_size_positive"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trainee_profiles.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    document_type: Mapped[ProfileDocumentType] = mapped_column(
        Enum(ProfileDocumentType, name="profile_document_type", native_enum=False, length=32)
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer())
    content: Mapped[bytes] = mapped_column(LargeBinary())
    validation_status: Mapped[DocumentValidationStatus] = mapped_column(
        Enum(
            DocumentValidationStatus,
            name="document_validation_status",
            native_enum=False,
            length=24,
        ),
        default=DocumentValidationStatus.PENDING,
        server_default=DocumentValidationStatus.PENDING.value,
        index=True,
    )
    validation_notes: Mapped[str | None] = mapped_column(Text())
    validated_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped[TraineeProfile] = relationship(back_populates="documents")
    uploaded_by: Mapped[User] = relationship(foreign_keys=[uploaded_by_id])
    validated_by: Mapped[User | None] = relationship(foreign_keys=[validated_by_id])


class ProgrammeEnrollment(Base, TimestampMixin):
    __tablename__ = "programme_enrollments"
    __table_args__ = (
        UniqueConstraint("trainee_id", "programme_id", name="uq_enrollment_trainee_programme"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_batches.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, name="enrollment_status", native_enum=False, length=24),
        default=EnrollmentStatus.ENROLLED,
        server_default=EnrollmentStatus.ENROLLED.value,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trainee: Mapped[User] = relationship()
    programme: Mapped[Programme] = relationship()
    batch: Mapped[ProgrammeBatch | None] = relationship()
    attendance: Mapped[list[AttendanceRecord]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[AssessmentRecord]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )
    certificates: Mapped[list[CertificateRecord]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    session_date: Mapped[date] = mapped_column(Date())
    topic: Mapped[str] = mapped_column(String(255))
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status", native_enum=False, length=24)
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    enrollment: Mapped[ProgrammeEnrollment] = relationship(back_populates="attendance")


class AssessmentRecord(Base):
    __tablename__ = "assessment_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    score: Mapped[float | None] = mapped_column(Float())
    maximum_score: Mapped[float | None] = mapped_column(Float())
    result: Mapped[AssessmentResult] = mapped_column(
        Enum(AssessmentResult, name="assessment_result", native_enum=False, length=24), index=True
    )
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enrollment: Mapped[ProgrammeEnrollment] = relationship(back_populates="assessments")


class CertificateRecord(Base):
    __tablename__ = "certificate_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    certificate_number: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    enrollment: Mapped[ProgrammeEnrollment] = relationship(back_populates="certificates")
