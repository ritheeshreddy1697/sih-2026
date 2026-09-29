from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
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
    ApplicationStatus,
    DocumentType,
    EligibilityType,
    NominationSource,
    ProgrammeMode,
    ProgrammeStatus,
)

if TYPE_CHECKING:
    from app.models.auth import Institution, User


class Programme(Base, TimestampMixin):
    __tablename__ = "programmes"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_programmes_capacity_positive"),
        CheckConstraint("duration_days > 0", name="ck_programmes_duration_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    updated_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text())
    mode: Mapped[ProgrammeMode] = mapped_column(
        Enum(ProgrammeMode, name="programme_mode", native_enum=False, length=24), index=True
    )
    status: Mapped[ProgrammeStatus] = mapped_column(
        Enum(ProgrammeStatus, name="programme_status", native_enum=False, length=32),
        default=ProgrammeStatus.DRAFT,
        server_default=ProgrammeStatus.DRAFT.value,
        index=True,
    )
    eligibility_criteria: Mapped[str] = mapped_column(Text())
    eligible_applicant_types: Mapped[list[str]] = mapped_column(JSON(), default=list)
    capacity: Mapped[int] = mapped_column(Integer())
    location: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(80), index=True)
    duration_days: Mapped[int] = mapped_column(Integer())
    application_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date] = mapped_column(Date())
    rejection_reason: Mapped[str | None] = mapped_column(Text())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    institution: Mapped[Institution] = relationship("Institution")
    created_by: Mapped[User] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship("User", foreign_keys=[updated_by_id])
    approved_by: Mapped[User | None] = relationship("User", foreign_keys=[approved_by_id])
    batches: Mapped[list[ProgrammeBatch]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )
    applications: Mapped[list[ProgrammeApplication]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )
    nominations: Mapped[list[ProgrammeNomination]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )


class ProgrammeBatch(Base, TimestampMixin):
    __tablename__ = "programme_batches"
    __table_args__ = (
        UniqueConstraint("programme_id", "code", name="uq_programme_batches_programme_code"),
        CheckConstraint("capacity > 0", name="ck_programme_batches_capacity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer())
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date] = mapped_column(Date())
    location: Mapped[str | None] = mapped_column(String(255))

    programme: Mapped[Programme] = relationship(back_populates="batches")
    trainer_assignments: Mapped[list[BatchTrainerAssignment]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class BatchTrainerAssignment(Base):
    __tablename__ = "batch_trainer_assignments"
    __table_args__ = (
        UniqueConstraint("batch_id", "trainer_id", name="uq_batch_trainer_assignment"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_batches.id", ondelete="CASCADE"), index=True
    )
    trainer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    assigned_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch: Mapped[ProgrammeBatch] = relationship(back_populates="trainer_assignments")
    trainer: Mapped[User] = relationship("User", foreign_keys=[trainer_id])
    assigned_by: Mapped[User] = relationship("User", foreign_keys=[assigned_by_id])


class ProgrammeApplication(Base, TimestampMixin):
    __tablename__ = "programme_applications"
    __table_args__ = (
        UniqueConstraint("programme_id", "trainee_id", name="uq_programme_application_trainee"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", native_enum=False, length=32),
        default=ApplicationStatus.SUBMITTED,
        server_default=ApplicationStatus.SUBMITTED.value,
        index=True,
    )
    statement: Mapped[str | None] = mapped_column(Text())
    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_notes: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    programme: Mapped[Programme] = relationship(back_populates="applications")
    trainee: Mapped[User] = relationship("User", foreign_keys=[trainee_id])
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id])
    documents: Mapped[list[ApplicationDocument]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ProgrammeNomination(Base, TimestampMixin):
    __tablename__ = "programme_nominations"
    __table_args__ = (
        UniqueConstraint("programme_id", "candidate_email", name="uq_programme_nomination_email"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    nominating_institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    nomination_type: Mapped[EligibilityType] = mapped_column(
        Enum(EligibilityType, name="eligibility_type", native_enum=False, length=40), index=True
    )
    source: Mapped[NominationSource] = mapped_column(
        Enum(NominationSource, name="nomination_source", native_enum=False, length=24),
        default=NominationSource.INDIVIDUAL,
        server_default=NominationSource.INDIVIDUAL.value,
    )
    candidate_full_name: Mapped[str] = mapped_column(String(255))
    candidate_email: Mapped[str] = mapped_column(String(320), index=True)
    candidate_phone: Mapped[str | None] = mapped_column(String(32))
    member_identifier: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="nomination_status", native_enum=False, length=32),
        default=ApplicationStatus.SUBMITTED,
        server_default=ApplicationStatus.SUBMITTED.value,
        index=True,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_notes: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    programme: Mapped[Programme] = relationship(back_populates="nominations")
    nominating_institution: Mapped[Institution] = relationship("Institution")
    created_by: Mapped[User] = relationship("User", foreign_keys=[created_by_id])
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id])
    documents: Mapped[list[ApplicationDocument]] = relationship(
        back_populates="nomination", cascade="all, delete-orphan"
    )


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    __table_args__ = (
        CheckConstraint(
            "(application_id IS NOT NULL AND nomination_id IS NULL) OR "
            "(application_id IS NULL AND nomination_id IS NOT NULL)",
            name="ck_application_documents_single_parent",
        ),
        CheckConstraint("size_bytes > 0", name="ck_application_documents_size_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_applications.id", ondelete="CASCADE"), index=True
    )
    nomination_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_nominations.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=False, length=32)
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer())
    content: Mapped[bytes] = mapped_column(LargeBinary())
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped[ProgrammeApplication | None] = relationship(back_populates="documents")
    nomination: Mapped[ProgrammeNomination | None] = relationship(back_populates="documents")
    uploaded_by: Mapped[User] = relationship("User")
