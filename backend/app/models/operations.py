from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    BedAllocationStatus,
    MealPreference,
    OperationsIssuePriority,
    OperationsIssueStatus,
    OperationsIssueType,
    ScheduleStatus,
    TransportMode,
)

if TYPE_CHECKING:
    from app.models.auth import Institution, User
    from app.models.profile import ProgrammeEnrollment
    from app.models.programme import Programme, ProgrammeBatch


class TrainingVenue(Base, TimestampMixin):
    __tablename__ = "training_venues"
    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_training_venue_institution_name"),
        CheckConstraint("capacity > 0", name="ck_training_venue_capacity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text())
    capacity: Mapped[int] = mapped_column(Integer())
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    institution: Mapped[Institution] = relationship()
    classrooms: Mapped[list[Classroom]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )


class Classroom(Base, TimestampMixin):
    __tablename__ = "classrooms"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_classroom_institution_code"),
        UniqueConstraint("venue_id", "name", name="uq_classroom_venue_name"),
        CheckConstraint("capacity > 0", name="ck_classroom_capacity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    venue_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_venues.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer())
    equipment: Mapped[str | None] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    institution: Mapped[Institution] = relationship()
    venue: Mapped[TrainingVenue] = relationship(back_populates="classrooms")


class TimetableSession(Base, TimestampMixin):
    __tablename__ = "timetable_sessions"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ck_timetable_session_window"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_batches.id", ondelete="CASCADE"), index=True
    )
    trainer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    venue_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_venues.id", ondelete="RESTRICT"), index=True
    )
    classroom_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text())
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status", native_enum=False, length=24),
        default=ScheduleStatus.SCHEDULED,
        server_default=ScheduleStatus.SCHEDULED.value,
        index=True,
    )

    institution: Mapped[Institution] = relationship()
    programme: Mapped[Programme] = relationship()
    batch: Mapped[ProgrammeBatch] = relationship()
    trainer: Mapped[User] = relationship(foreign_keys=[trainer_id])
    venue: Mapped[TrainingVenue] = relationship()
    classroom: Mapped[Classroom | None] = relationship()
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class HostelBuilding(Base, TimestampMixin):
    __tablename__ = "hostel_buildings"
    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_hostel_building_institution_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text())
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    institution: Mapped[Institution] = relationship()
    rooms: Mapped[list[HostelRoom]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )


class HostelRoom(Base, TimestampMixin):
    __tablename__ = "hostel_rooms"
    __table_args__ = (
        UniqueConstraint("building_id", "room_number", name="uq_hostel_room_number"),
        CheckConstraint("capacity > 0", name="ck_hostel_room_capacity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    building_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hostel_buildings.id", ondelete="CASCADE"), index=True
    )
    room_number: Mapped[str] = mapped_column(String(64))
    floor: Mapped[str | None] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer())
    is_accessible: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    building: Mapped[HostelBuilding] = relationship(back_populates="rooms")
    beds: Mapped[list[HostelBed]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class HostelBed(Base, TimestampMixin):
    __tablename__ = "hostel_beds"
    __table_args__ = (UniqueConstraint("room_id", "bed_number", name="uq_hostel_bed_number"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hostel_rooms.id", ondelete="CASCADE"), index=True
    )
    bed_number: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")

    room: Mapped[HostelRoom] = relationship(back_populates="beds")


class BedAllocation(Base, TimestampMixin):
    __tablename__ = "bed_allocations"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_bed_allocation_window"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    bed_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hostel_beds.id", ondelete="RESTRICT"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    allocated_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    start_date: Mapped[date] = mapped_column(Date(), index=True)
    end_date: Mapped[date] = mapped_column(Date(), index=True)
    status: Mapped[BedAllocationStatus] = mapped_column(
        Enum(
            BedAllocationStatus,
            name="bed_allocation_status",
            native_enum=False,
            length=24,
        ),
        default=BedAllocationStatus.RESERVED,
        server_default=BedAllocationStatus.RESERVED.value,
        index=True,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    bed: Mapped[HostelBed] = relationship()
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    allocated_by: Mapped[User] = relationship()


class ParticipantLogistics(Base, TimestampMixin):
    __tablename__ = "participant_logistics"
    __table_args__ = (
        UniqueConstraint("enrollment_id", name="uq_participant_logistics_enrollment"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    meal_preference: Mapped[MealPreference] = mapped_column(
        Enum(MealPreference, name="meal_preference", native_enum=False, length=24),
        default=MealPreference.VEGETARIAN,
        server_default=MealPreference.VEGETARIAN.value,
    )
    dietary_notes: Mapped[str | None] = mapped_column(Text())
    arrival_mode: Mapped[TransportMode | None] = mapped_column(
        Enum(TransportMode, name="arrival_transport_mode", native_enum=False, length=24)
    )
    arrival_details: Mapped[str | None] = mapped_column(Text())
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    departure_mode: Mapped[TransportMode | None] = mapped_column(
        Enum(TransportMode, name="departure_transport_mode", native_enum=False, length=24)
    )
    departure_details: Mapped[str | None] = mapped_column(Text())
    departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emergency_contact_name: Mapped[str] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str] = mapped_column(String(32))
    emergency_contact_relationship: Mapped[str] = mapped_column(String(120))

    enrollment: Mapped[ProgrammeEnrollment] = relationship()


class TrainingMaterial(Base, TimestampMixin):
    __tablename__ = "training_materials"
    __table_args__ = (
        UniqueConstraint("programme_id", "name", name="uq_training_material_programme_name"),
        CheckConstraint("quantity_available >= 0", name="ck_training_material_quantity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text())
    quantity_available: Mapped[int] = mapped_column(Integer())

    institution: Mapped[Institution] = relationship()
    programme: Mapped[Programme] = relationship()
    distributions: Mapped[list[MaterialDistribution]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )


class MaterialDistribution(Base):
    __tablename__ = "material_distributions"
    __table_args__ = (
        UniqueConstraint("material_id", "enrollment_id", name="uq_material_distribution"),
        CheckConstraint("quantity > 0", name="ck_material_distribution_quantity_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    material_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_materials.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="CASCADE"), index=True
    )
    distributed_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    quantity: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")
    distributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    material: Mapped[TrainingMaterial] = relationship(back_populates="distributions")
    enrollment: Mapped[ProgrammeEnrollment] = relationship()
    distributed_by: Mapped[User] = relationship()


class OperationsIssue(Base, TimestampMixin):
    __tablename__ = "operations_issues"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programme_enrollments.id", ondelete="SET NULL"), index=True
    )
    reported_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    issue_type: Mapped[OperationsIssueType] = mapped_column(
        Enum(OperationsIssueType, name="operations_issue_type", native_enum=False, length=24),
        index=True,
    )
    priority: Mapped[OperationsIssuePriority] = mapped_column(
        Enum(
            OperationsIssuePriority,
            name="operations_issue_priority",
            native_enum=False,
            length=24,
        ),
        default=OperationsIssuePriority.MEDIUM,
        server_default=OperationsIssuePriority.MEDIUM.value,
        index=True,
    )
    status: Mapped[OperationsIssueStatus] = mapped_column(
        Enum(
            OperationsIssueStatus,
            name="operations_issue_status",
            native_enum=False,
            length=24,
        ),
        default=OperationsIssueStatus.OPEN,
        server_default=OperationsIssueStatus.OPEN.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text())
    location: Mapped[str | None] = mapped_column(String(255))
    resolution_notes: Mapped[str | None] = mapped_column(Text())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    institution: Mapped[Institution] = relationship()
    enrollment: Mapped[ProgrammeEnrollment | None] = relationship()
    reported_by: Mapped[User] = relationship(foreign_keys=[reported_by_id])
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id])
