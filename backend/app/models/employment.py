from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
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
    EmployerVerificationStatus,
    EmploymentType,
    JobApplicationStatus,
    JobStatus,
    WorkplaceMode,
)

if TYPE_CHECKING:
    from app.models.auth import Institution, User
    from app.models.certificate import DigitalCertificate
    from app.models.programme import Programme


class EmployerProfile(Base, TimestampMixin):
    __tablename__ = "employer_profiles"
    __table_args__ = (UniqueConstraint("institution_id", name="uq_employer_profile_institution"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    registered_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    verified_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    industry: Mapped[str] = mapped_column(String(160), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    company_size: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text())
    headquarters: Mapped[str] = mapped_column(String(255), index=True)
    registration_number: Mapped[str | None] = mapped_column(String(120), index=True)
    verification_status: Mapped[EmployerVerificationStatus] = mapped_column(
        Enum(
            EmployerVerificationStatus,
            name="employer_verification_status",
            native_enum=False,
            length=24,
        ),
        default=EmployerVerificationStatus.PENDING,
        server_default=EmployerVerificationStatus.PENDING.value,
        index=True,
    )
    verification_notes: Mapped[str | None] = mapped_column(Text())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    institution: Mapped[Institution] = relationship()
    registered_by: Mapped[User] = relationship(foreign_keys=[registered_by_id])
    verified_by: Mapped[User | None] = relationship(foreign_keys=[verified_by_id])
    jobs: Mapped[list[JobPosting]] = relationship(
        back_populates="employer", cascade="all, delete-orphan"
    )


class TraineeEmploymentProfile(Base, TimestampMixin):
    __tablename__ = "trainee_employment_profiles"
    __table_args__ = (UniqueConstraint("trainee_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    headline: Mapped[str | None] = mapped_column(String(255))
    professional_summary: Mapped[str | None] = mapped_column(Text())
    preferred_roles: Mapped[list[str]] = mapped_column(JSON(), default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(JSON(), default=list)
    open_to_work: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")
    resume_filename: Mapped[str | None] = mapped_column(String(255))
    resume_content_type: Mapped[str | None] = mapped_column(String(120))
    resume_size_bytes: Mapped[int | None] = mapped_column(Integer())
    resume_content: Mapped[bytes | None] = mapped_column(LargeBinary())
    resume_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])


class VerifiedEmploymentSkill(Base, TimestampMixin):
    __tablename__ = "verified_employment_skills"
    __table_args__ = (
        UniqueConstraint(
            "trainee_id", "certificate_id", "name", name="uq_verified_employment_skill"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    certificate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("digital_certificates.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), index=True)

    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])
    certificate: Mapped[DigitalCertificate] = relationship()


class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"
    __table_args__ = (
        CheckConstraint("vacancies > 0", name="ck_job_posting_vacancies_positive"),
        CheckConstraint(
            "minimum_experience_years >= 0",
            name="ck_job_posting_experience_nonnegative",
        ),
        CheckConstraint(
            "salary_minimum IS NULL OR salary_maximum IS NULL OR salary_maximum >= salary_minimum",
            name="ck_job_posting_salary_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    employer_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    updated_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text())
    location: Mapped[str] = mapped_column(String(255), index=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type", native_enum=False, length=24), index=True
    )
    workplace_mode: Mapped[WorkplaceMode] = mapped_column(
        Enum(WorkplaceMode, name="workplace_mode", native_enum=False, length=24), index=True
    )
    required_skills: Mapped[list[str]] = mapped_column(JSON(), default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON(), default=list)
    minimum_experience_years: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    vacancies: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")
    salary_minimum: Mapped[float | None] = mapped_column(Float())
    salary_maximum: Mapped[float | None] = mapped_column(Float())
    application_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False, length=24),
        default=JobStatus.DRAFT,
        server_default=JobStatus.DRAFT.value,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    employer: Mapped[EmployerProfile] = relationship(back_populates="jobs")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])
    programme_requirements: Mapped[list[JobProgrammeRequirement]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list[JobApplication]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    shortlists: Mapped[list[CandidateShortlist]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobProgrammeRequirement(Base):
    __tablename__ = "job_programme_requirements"

    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), primary_key=True
    )

    job: Mapped[JobPosting] = relationship(back_populates="programme_requirements")
    programme: Mapped[Programme] = relationship()


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("job_id", "trainee_id", name="uq_saved_job_trainee"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[JobPosting] = relationship()
    trainee: Mapped[User] = relationship()


class CandidateShortlist(Base, TimestampMixin):
    __tablename__ = "candidate_shortlists"
    __table_args__ = (UniqueConstraint("job_id", "trainee_id", name="uq_candidate_shortlist_job"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    shortlisted_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(Text())

    job: Mapped[JobPosting] = relationship(back_populates="shortlists")
    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])
    shortlisted_by: Mapped[User] = relationship(foreign_keys=[shortlisted_by_id])


class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_id", "trainee_id", name="uq_job_application_trainee"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cover_note: Mapped[str | None] = mapped_column(Text())
    status: Mapped[JobApplicationStatus] = mapped_column(
        Enum(
            JobApplicationStatus,
            name="job_application_status",
            native_enum=False,
            length=32,
        ),
        default=JobApplicationStatus.APPLIED,
        server_default=JobApplicationStatus.APPLIED.value,
        index=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    interview_mode: Mapped[str | None] = mapped_column(String(80))
    interview_details: Mapped[str | None] = mapped_column(Text())
    employer_notes: Mapped[str | None] = mapped_column(Text())

    job: Mapped[JobPosting] = relationship(back_populates="applications")
    trainee: Mapped[User] = relationship(foreign_keys=[trainee_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    certificates: Mapped[list[JobApplicationCertificate]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class JobApplicationCertificate(Base):
    __tablename__ = "job_application_certificates"

    application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    certificate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("digital_certificates.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    application: Mapped[JobApplication] = relationship(back_populates="certificates")
    certificate: Mapped[DigitalCertificate] = relationship()
