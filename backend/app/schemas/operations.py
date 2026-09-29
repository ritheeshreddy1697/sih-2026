from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    BedAllocationStatus,
    MealPreference,
    OperationsIssuePriority,
    OperationsIssueStatus,
    OperationsIssueType,
    ScheduleStatus,
    TransportMode,
)


class InstitutionOption(BaseModel):
    id: UUID
    name: str
    code: str


class BatchOption(BaseModel):
    id: UUID
    name: str
    code: str


class ProgrammeOption(BaseModel):
    id: UUID
    title: str
    code: str
    batches: list[BatchOption]


class PersonOption(BaseModel):
    id: UUID
    full_name: str
    email: str


class EnrollmentOption(BaseModel):
    id: UUID
    trainee: PersonOption
    programme_id: UUID
    programme_title: str
    batch_id: UUID | None
    batch_name: str | None


class VenueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: UUID
    name: str = Field(min_length=2, max_length=255)
    address: str = Field(min_length=5, max_length=2000)
    capacity: int = Field(gt=0, le=100000)


class ClassroomCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    venue_id: UUID
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=64)
    capacity: int = Field(gt=0, le=10000)
    equipment: str | None = Field(default=None, max_length=2000)


class ClassroomPublic(BaseModel):
    id: UUID
    venue_id: UUID
    name: str
    code: str
    capacity: int
    equipment: str | None
    is_active: bool


class VenuePublic(BaseModel):
    id: UUID
    institution_id: UUID
    name: str
    address: str
    capacity: int
    is_active: bool
    classrooms: list[ClassroomPublic]


class TimetableSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programme_id: UUID
    batch_id: UUID
    trainer_id: UUID
    venue_id: UUID
    classroom_id: UUID | None = None
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "TimetableSessionCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Session end time must be after its start time")
        return self


class TimetableSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_id: UUID | None = None
    venue_id: UUID | None = None
    classroom_id: UUID | None = None
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: ScheduleStatus | None = None


class TimetableSessionPublic(BaseModel):
    id: UUID
    institution_id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    batch_id: UUID
    batch_name: str
    trainer_id: UUID
    trainer_name: str
    venue_id: UUID
    venue_name: str
    classroom_id: UUID | None
    classroom_name: str | None
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    status: ScheduleStatus


class HostelBuildingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: UUID
    name: str = Field(min_length=2, max_length=255)
    address: str = Field(min_length=5, max_length=2000)
    contact_phone: str | None = Field(default=None, max_length=32)


class HostelRoomCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_number: str = Field(min_length=1, max_length=64)
    floor: str | None = Field(default=None, max_length=64)
    capacity: int = Field(gt=0, le=100)
    bed_numbers: list[str] = Field(min_length=1, max_length=100)
    is_accessible: bool = False

    @model_validator(mode="after")
    def validate_beds(self) -> "HostelRoomCreate":
        numbers = [number.strip() for number in self.bed_numbers]
        if any(not number for number in numbers):
            raise ValueError("Bed numbers cannot be blank")
        if len(numbers) != len(set(numbers)):
            raise ValueError("Bed numbers must be unique")
        if len(numbers) > self.capacity:
            raise ValueError("Bed count cannot exceed room capacity")
        self.bed_numbers = numbers
        return self


class HostelBedPublic(BaseModel):
    id: UUID
    bed_number: str
    is_active: bool


class HostelRoomPublic(BaseModel):
    id: UUID
    room_number: str
    floor: str | None
    capacity: int
    is_accessible: bool
    is_active: bool
    beds: list[HostelBedPublic]


class HostelBuildingPublic(BaseModel):
    id: UUID
    institution_id: UUID
    name: str
    address: str
    contact_phone: str | None
    is_active: bool
    rooms: list[HostelRoomPublic]


class BedAllocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bed_id: UUID
    enrollment_id: UUID
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_window(self) -> "BedAllocationCreate":
        if self.end_date < self.start_date:
            raise ValueError("Allocation end date cannot be before its start date")
        return self


class BedAllocationPublic(BaseModel):
    id: UUID
    bed_id: UUID
    bed_number: str
    room_id: UUID
    room_number: str
    building_id: UUID
    building_name: str
    enrollment_id: UUID
    trainee_name: str
    programme_title: str
    start_date: date
    end_date: date
    status: BedAllocationStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None


class ParticipantLogisticsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_preference: MealPreference
    dietary_notes: str | None = Field(default=None, max_length=2000)
    arrival_mode: TransportMode | None = None
    arrival_details: str | None = Field(default=None, max_length=2000)
    arrival_at: datetime | None = None
    departure_mode: TransportMode | None = None
    departure_details: str | None = Field(default=None, max_length=2000)
    departure_at: datetime | None = None
    emergency_contact_name: str = Field(min_length=2, max_length=255)
    emergency_contact_phone: str = Field(min_length=7, max_length=32)
    emergency_contact_relationship: str = Field(min_length=2, max_length=120)


class ParticipantLogisticsPublic(ParticipantLogisticsUpdate):
    id: UUID
    enrollment_id: UUID
    trainee_name: str
    programme_title: str


class TrainingMaterialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programme_id: UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    quantity_available: int = Field(ge=0, le=1000000)


class MaterialDistributionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_id: UUID
    quantity: int = Field(gt=0, le=10000)


class MaterialDistributionPublic(BaseModel):
    id: UUID
    enrollment_id: UUID
    trainee_name: str
    quantity: int
    distributed_at: datetime


class TrainingMaterialPublic(BaseModel):
    id: UUID
    programme_id: UUID
    programme_title: str
    name: str
    description: str | None
    quantity_available: int
    quantity_distributed: int
    distributions: list[MaterialDistributionPublic]


class OperationsIssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: UUID | None = None
    enrollment_id: UUID | None = None
    issue_type: OperationsIssueType
    priority: OperationsIssuePriority = OperationsIssuePriority.MEDIUM
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5, max_length=4000)
    location: str | None = Field(default=None, max_length=255)


class OperationsIssueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OperationsIssueStatus
    resolution_notes: str | None = Field(default=None, max_length=4000)


class OperationsIssuePublic(BaseModel):
    id: UUID
    institution_id: UUID
    enrollment_id: UUID | None
    trainee_name: str | None
    reported_by_name: str
    issue_type: OperationsIssueType
    priority: OperationsIssuePriority
    status: OperationsIssueStatus
    title: str
    description: str
    location: str | None
    resolution_notes: str | None
    resolved_by_name: str | None
    resolved_at: datetime | None
    created_at: datetime


class OperationsWorkspacePublic(BaseModel):
    institution: InstitutionOption
    available_institutions: list[InstitutionOption]
    programmes: list[ProgrammeOption]
    trainers: list[PersonOption]
    enrollments: list[EnrollmentOption]
    venues: list[VenuePublic]
    timetable: list[TimetableSessionPublic]
    hostels: list[HostelBuildingPublic]
    bed_allocations: list[BedAllocationPublic]
    participant_logistics: list[ParticipantLogisticsPublic]
    materials: list[TrainingMaterialPublic]
    issues: list[OperationsIssuePublic]


class TraineeProgrammeOperations(BaseModel):
    enrollment_id: UUID
    programme_id: UUID
    programme_title: str
    programme_code: str
    batch_name: str | None
    timetable: list[TimetableSessionPublic]
    logistics: ParticipantLogisticsPublic | None
    accommodation: BedAllocationPublic | None
    materials: list[TrainingMaterialPublic]
    issues: list[OperationsIssuePublic]


class TraineeOperationsPublic(BaseModel):
    programmes: list[TraineeProgrammeOperations]
