from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
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

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.profile import ProgrammeEnrollment
    from app.models.programme import Programme


class CertificatePolicy(Base, TimestampMixin):
    __tablename__ = "certificate_policies"
    __table_args__ = (
        UniqueConstraint("programme_id", name="uq_certificate_policy_programme"),
        CheckConstraint(
            "minimum_course_completion_percent >= 0 AND minimum_course_completion_percent <= 100",
            name="ck_certificate_policy_course_completion_range",
        ),
        CheckConstraint(
            "minimum_attendance_percent >= 0 AND minimum_attendance_percent <= 100",
            name="ck_certificate_policy_attendance_range",
        ),
        CheckConstraint(
            "minimum_assessment_score_percent >= 0 AND minimum_assessment_score_percent <= 100",
            name="ck_certificate_policy_assessment_range",
        ),
        CheckConstraint(
            "validity_days IS NULL OR validity_days > 0",
            name="ck_certificate_policy_validity_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    configured_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    certificate_title: Mapped[str] = mapped_column(String(255))
    minimum_course_completion_percent: Mapped[float] = mapped_column(
        Float(), default=100, server_default="100"
    )
    minimum_attendance_percent: Mapped[float] = mapped_column(
        Float(), default=75, server_default="75"
    )
    minimum_assessment_score_percent: Mapped[float] = mapped_column(
        Float(), default=60, server_default="60"
    )
    validity_days: Mapped[int | None] = mapped_column(Integer())
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    programme: Mapped[Programme] = relationship()
    configured_by: Mapped[User] = relationship()
    certificates: Mapped[list[DigitalCertificate]] = relationship(back_populates="policy")


class DigitalCertificate(Base, TimestampMixin):
    __tablename__ = "digital_certificates"
    __table_args__ = (
        UniqueConstraint("enrollment_id", name="uq_digital_certificate_enrollment"),
        UniqueConstraint("certificate_number", name="uq_digital_certificate_number"),
        UniqueConstraint("verification_token", name="uq_digital_certificate_verification_token"),
        CheckConstraint(
            "course_completion_percent >= 0 AND course_completion_percent <= 100",
            name="ck_digital_certificate_course_completion_range",
        ),
        CheckConstraint(
            "attendance_percent >= 0 AND attendance_percent <= 100",
            name="ck_digital_certificate_attendance_range",
        ),
        CheckConstraint(
            "assessment_score_percent >= 0 AND assessment_score_percent <= 100",
            name="ck_digital_certificate_assessment_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    policy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("certificate_policies.id", ondelete="RESTRICT"), index=True
    )
    issued_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    revoked_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    certificate_number: Mapped[str] = mapped_column(String(64), index=True)
    verification_token: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    course_completion_percent: Mapped[float] = mapped_column(Float())
    attendance_percent: Mapped[float] = mapped_column(Float())
    assessment_score_percent: Mapped[float] = mapped_column(Float())
    pdf_content: Mapped[bytes] = mapped_column(LargeBinary())
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text())

    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    policy: Mapped[CertificatePolicy] = relationship(back_populates="certificates")
    issued_by: Mapped[User] = relationship(foreign_keys=[issued_by_id])
    revoked_by: Mapped[User | None] = relationship(foreign_keys=[revoked_by_id])
