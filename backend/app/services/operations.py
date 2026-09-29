from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.permissions import Permission, has_permission
from app.models import (
    AuditLog,
    BedAllocation,
    BedAllocationStatus,
    Classroom,
    EnrollmentStatus,
    HostelBed,
    HostelBuilding,
    HostelRoom,
    Institution,
    MaterialDistribution,
    OperationsIssue,
    OperationsIssueStatus,
    ParticipantLogistics,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    Role,
    RoleCode,
    ScheduleStatus,
    TimetableSession,
    TrainingMaterial,
    TrainingVenue,
    User,
)
from app.schemas.operations import (
    BatchOption,
    BedAllocationCreate,
    BedAllocationPublic,
    ClassroomCreate,
    ClassroomPublic,
    EnrollmentOption,
    HostelBedPublic,
    HostelBuildingCreate,
    HostelBuildingPublic,
    HostelRoomCreate,
    HostelRoomPublic,
    InstitutionOption,
    MaterialDistributionCreate,
    MaterialDistributionPublic,
    OperationsIssueCreate,
    OperationsIssuePublic,
    OperationsIssueUpdate,
    OperationsWorkspacePublic,
    ParticipantLogisticsPublic,
    ParticipantLogisticsUpdate,
    PersonOption,
    ProgrammeOption,
    TimetableSessionCreate,
    TimetableSessionPublic,
    TimetableSessionUpdate,
    TraineeOperationsPublic,
    TraineeProgrammeOperations,
    TrainingMaterialCreate,
    TrainingMaterialPublic,
    VenueCreate,
    VenuePublic,
)
from app.services.auth import get_client_details


def utc_now() -> datetime:
    return datetime.now(UTC)


def role_codes(user: User) -> set[RoleCode]:
    return {role.code for role in user.roles}


def is_platform_admin(user: User) -> bool:
    return has_permission(role_codes(user), Permission.PLATFORM_MANAGE)


def display_name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def add_audit(
    db: Session,
    request: Request,
    event_type: str,
    user: User,
    details: dict[str, Any],
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id,
            event_type=event_type,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    )


def institution_option(item: Institution) -> InstitutionOption:
    return InstitutionOption(id=item.id, name=item.name, code=item.code)


def ensure_institution_access(user: User, institution_id: UUID) -> None:
    if is_platform_admin(user):
        return
    if RoleCode.INSTITUTE_ADMIN in role_codes(user) and user.institution_id == institution_id:
        return
    raise HTTPException(
        status_code=403,
        detail="You can manage operations only for your own institution",
    )


def resolve_institution(db: Session, user: User, requested_id: UUID | None = None) -> Institution:
    institution_id = requested_id or user.institution_id
    if institution_id is None:
        raise HTTPException(status_code=422, detail="Select an institution")
    ensure_institution_access(user, institution_id)
    institution = db.get(Institution, institution_id)
    if institution is None or not institution.is_active:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


def programme_options() -> tuple[Any, ...]:
    return (selectinload(Programme.batches),)


def enrollment_options() -> tuple[Any, ...]:
    return (
        joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile),
        joinedload(ProgrammeEnrollment.programme),
        joinedload(ProgrammeEnrollment.batch),
    )


def session_options() -> tuple[Any, ...]:
    return (
        joinedload(TimetableSession.programme),
        joinedload(TimetableSession.batch),
        joinedload(TimetableSession.trainer).joinedload(User.profile),
        joinedload(TimetableSession.venue),
        joinedload(TimetableSession.classroom),
    )


def allocation_options() -> tuple[Any, ...]:
    return (
        joinedload(BedAllocation.bed).joinedload(HostelBed.room).joinedload(HostelRoom.building),
        joinedload(BedAllocation.enrollment)
        .joinedload(ProgrammeEnrollment.trainee)
        .joinedload(User.profile),
        joinedload(BedAllocation.enrollment).joinedload(ProgrammeEnrollment.programme),
    )


def logistics_options() -> tuple[Any, ...]:
    return (
        joinedload(ParticipantLogistics.enrollment)
        .joinedload(ProgrammeEnrollment.trainee)
        .joinedload(User.profile),
        joinedload(ParticipantLogistics.enrollment).joinedload(ProgrammeEnrollment.programme),
    )


def material_options() -> tuple[Any, ...]:
    return (
        joinedload(TrainingMaterial.programme),
        selectinload(TrainingMaterial.distributions)
        .joinedload(MaterialDistribution.enrollment)
        .joinedload(ProgrammeEnrollment.trainee)
        .joinedload(User.profile),
    )


def issue_options() -> tuple[Any, ...]:
    return (
        joinedload(OperationsIssue.reported_by).joinedload(User.profile),
        joinedload(OperationsIssue.resolved_by).joinedload(User.profile),
        joinedload(OperationsIssue.enrollment)
        .joinedload(ProgrammeEnrollment.trainee)
        .joinedload(User.profile),
    )


def venue_public(item: TrainingVenue) -> VenuePublic:
    return VenuePublic(
        id=item.id,
        institution_id=item.institution_id,
        name=item.name,
        address=item.address,
        capacity=item.capacity,
        is_active=item.is_active,
        classrooms=[
            ClassroomPublic(
                id=room.id,
                venue_id=room.venue_id,
                name=room.name,
                code=room.code,
                capacity=room.capacity,
                equipment=room.equipment,
                is_active=room.is_active,
            )
            for room in sorted(item.classrooms, key=lambda value: value.name)
        ],
    )


def session_public(item: TimetableSession) -> TimetableSessionPublic:
    return TimetableSessionPublic(
        id=item.id,
        institution_id=item.institution_id,
        programme_id=item.programme_id,
        programme_title=item.programme.title,
        programme_code=item.programme.code,
        batch_id=item.batch_id,
        batch_name=item.batch.name,
        trainer_id=item.trainer_id,
        trainer_name=display_name(item.trainer),
        venue_id=item.venue_id,
        venue_name=item.venue.name,
        classroom_id=item.classroom_id,
        classroom_name=item.classroom.name if item.classroom else None,
        title=item.title,
        description=item.description,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        status=item.status,
    )


def hostel_public(item: HostelBuilding) -> HostelBuildingPublic:
    return HostelBuildingPublic(
        id=item.id,
        institution_id=item.institution_id,
        name=item.name,
        address=item.address,
        contact_phone=item.contact_phone,
        is_active=item.is_active,
        rooms=[
            HostelRoomPublic(
                id=room.id,
                room_number=room.room_number,
                floor=room.floor,
                capacity=room.capacity,
                is_accessible=room.is_accessible,
                is_active=room.is_active,
                beds=[
                    HostelBedPublic(
                        id=bed.id,
                        bed_number=bed.bed_number,
                        is_active=bed.is_active,
                    )
                    for bed in sorted(room.beds, key=lambda value: value.bed_number)
                ],
            )
            for room in sorted(item.rooms, key=lambda value: value.room_number)
        ],
    )


def allocation_public(item: BedAllocation) -> BedAllocationPublic:
    enrollment = item.enrollment
    room = item.bed.room
    return BedAllocationPublic(
        id=item.id,
        bed_id=item.bed_id,
        bed_number=item.bed.bed_number,
        room_id=room.id,
        room_number=room.room_number,
        building_id=room.building_id,
        building_name=room.building.name,
        enrollment_id=item.enrollment_id,
        trainee_name=display_name(enrollment.trainee),
        programme_title=enrollment.programme.title,
        start_date=item.start_date,
        end_date=item.end_date,
        status=item.status,
        checked_in_at=item.checked_in_at,
        checked_out_at=item.checked_out_at,
    )


def logistics_public(item: ParticipantLogistics) -> ParticipantLogisticsPublic:
    enrollment = item.enrollment
    return ParticipantLogisticsPublic(
        id=item.id,
        enrollment_id=item.enrollment_id,
        trainee_name=display_name(enrollment.trainee),
        programme_title=enrollment.programme.title,
        meal_preference=item.meal_preference,
        dietary_notes=item.dietary_notes,
        arrival_mode=item.arrival_mode,
        arrival_details=item.arrival_details,
        arrival_at=item.arrival_at,
        departure_mode=item.departure_mode,
        departure_details=item.departure_details,
        departure_at=item.departure_at,
        emergency_contact_name=item.emergency_contact_name,
        emergency_contact_phone=item.emergency_contact_phone,
        emergency_contact_relationship=item.emergency_contact_relationship,
    )


def material_public(
    item: TrainingMaterial, enrollment_id: UUID | None = None
) -> TrainingMaterialPublic:
    visible_distributions = [
        value
        for value in item.distributions
        if enrollment_id is None or value.enrollment_id == enrollment_id
    ]
    distributions = [
        MaterialDistributionPublic(
            id=value.id,
            enrollment_id=value.enrollment_id,
            trainee_name=display_name(value.enrollment.trainee),
            quantity=value.quantity,
            distributed_at=value.distributed_at,
        )
        for value in sorted(visible_distributions, key=lambda row: row.distributed_at)
    ]
    return TrainingMaterialPublic(
        id=item.id,
        programme_id=item.programme_id,
        programme_title=item.programme.title,
        name=item.name,
        description=item.description,
        quantity_available=item.quantity_available,
        quantity_distributed=sum(value.quantity for value in item.distributions),
        distributions=distributions,
    )


def issue_public(item: OperationsIssue) -> OperationsIssuePublic:
    return OperationsIssuePublic(
        id=item.id,
        institution_id=item.institution_id,
        enrollment_id=item.enrollment_id,
        trainee_name=(
            display_name(item.enrollment.trainee) if item.enrollment is not None else None
        ),
        reported_by_name=display_name(item.reported_by),
        issue_type=item.issue_type,
        priority=item.priority,
        status=item.status,
        title=item.title,
        description=item.description,
        location=item.location,
        resolution_notes=item.resolution_notes,
        resolved_by_name=display_name(item.resolved_by) if item.resolved_by else None,
        resolved_at=item.resolved_at,
        created_at=item.created_at,
    )


def get_workspace(
    db: Session, user: User, institution_id: UUID | None
) -> OperationsWorkspacePublic:
    institution = resolve_institution(db, user, institution_id)
    available = (
        db.scalars(
            select(Institution).where(Institution.is_active.is_(True)).order_by(Institution.name)
        ).all()
        if is_platform_admin(user)
        else [institution]
    )
    programmes = db.scalars(
        select(Programme)
        .where(Programme.institution_id == institution.id)
        .options(*programme_options())
        .order_by(Programme.start_date.desc())
    ).all()
    trainers = db.scalars(
        select(User)
        .where(
            User.institution_id == institution.id,
            User.roles.any(Role.code == RoleCode.TRAINER),
        )
        .options(joinedload(User.profile))
        .order_by(User.email)
    ).all()
    enrollments = db.scalars(
        select(ProgrammeEnrollment)
        .join(Programme)
        .where(
            Programme.institution_id == institution.id,
            ProgrammeEnrollment.status != EnrollmentStatus.WITHDRAWN,
        )
        .options(*enrollment_options())
        .order_by(ProgrammeEnrollment.enrolled_at.desc())
    ).all()
    venues = db.scalars(
        select(TrainingVenue)
        .where(TrainingVenue.institution_id == institution.id)
        .options(selectinload(TrainingVenue.classrooms))
        .order_by(TrainingVenue.name)
    ).all()
    sessions = db.scalars(
        select(TimetableSession)
        .where(TimetableSession.institution_id == institution.id)
        .options(*session_options())
        .order_by(TimetableSession.starts_at)
    ).all()
    hostels = db.scalars(
        select(HostelBuilding)
        .where(HostelBuilding.institution_id == institution.id)
        .options(selectinload(HostelBuilding.rooms).selectinload(HostelRoom.beds))
        .order_by(HostelBuilding.name)
    ).all()
    allocations = db.scalars(
        select(BedAllocation)
        .join(BedAllocation.bed)
        .join(HostelBed.room)
        .join(HostelRoom.building)
        .where(HostelBuilding.institution_id == institution.id)
        .options(*allocation_options())
        .order_by(BedAllocation.start_date.desc())
    ).all()
    logistics = db.scalars(
        select(ParticipantLogistics)
        .join(ParticipantLogistics.enrollment)
        .join(ProgrammeEnrollment.programme)
        .where(Programme.institution_id == institution.id)
        .options(*logistics_options())
        .order_by(ParticipantLogistics.updated_at.desc())
    ).all()
    materials = db.scalars(
        select(TrainingMaterial)
        .where(TrainingMaterial.institution_id == institution.id)
        .options(*material_options())
        .order_by(TrainingMaterial.name)
    ).all()
    issues = db.scalars(
        select(OperationsIssue)
        .where(OperationsIssue.institution_id == institution.id)
        .options(*issue_options())
        .order_by(OperationsIssue.created_at.desc())
    ).all()
    return OperationsWorkspacePublic(
        institution=institution_option(institution),
        available_institutions=[institution_option(value) for value in available],
        programmes=[
            ProgrammeOption(
                id=value.id,
                title=value.title,
                code=value.code,
                batches=[
                    BatchOption(id=batch.id, name=batch.name, code=batch.code)
                    for batch in sorted(value.batches, key=lambda row: row.start_date)
                ],
            )
            for value in programmes
        ],
        trainers=[
            PersonOption(id=value.id, full_name=display_name(value), email=value.email)
            for value in trainers
        ],
        enrollments=[
            EnrollmentOption(
                id=value.id,
                trainee=PersonOption(
                    id=value.trainee_id,
                    full_name=display_name(value.trainee),
                    email=value.trainee.email,
                ),
                programme_id=value.programme_id,
                programme_title=value.programme.title,
                batch_id=value.batch_id,
                batch_name=value.batch.name if value.batch else None,
            )
            for value in enrollments
        ],
        venues=[venue_public(value) for value in venues],
        timetable=[session_public(value) for value in sessions],
        hostels=[hostel_public(value) for value in hostels],
        bed_allocations=[allocation_public(value) for value in allocations],
        participant_logistics=[logistics_public(value) for value in logistics],
        materials=[material_public(value) for value in materials],
        issues=[issue_public(value) for value in issues],
    )


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def create_venue(db: Session, request: Request, user: User, payload: VenueCreate) -> VenuePublic:
    resolve_institution(db, user, payload.institution_id)
    item = TrainingVenue(
        id=uuid4(),
        institution_id=payload.institution_id,
        name=payload.name.strip(),
        address=payload.address.strip(),
        capacity=payload.capacity,
    )
    db.add(item)
    add_audit(db, request, "operations.venue_created", user, {"venue_id": str(item.id)})
    _commit_or_conflict(db, "A venue with this name already exists")
    db.refresh(item)
    return venue_public(item)


def create_classroom(
    db: Session, request: Request, user: User, payload: ClassroomCreate
) -> ClassroomPublic:
    venue = db.get(TrainingVenue, payload.venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    ensure_institution_access(user, venue.institution_id)
    if payload.capacity > venue.capacity:
        raise HTTPException(
            status_code=422, detail="Classroom capacity cannot exceed venue capacity"
        )
    item = Classroom(
        id=uuid4(),
        institution_id=venue.institution_id,
        venue_id=venue.id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        capacity=payload.capacity,
        equipment=payload.equipment,
    )
    db.add(item)
    add_audit(db, request, "operations.classroom_created", user, {"classroom_id": str(item.id)})
    _commit_or_conflict(db, "A classroom with this name or code already exists")
    db.refresh(item)
    return ClassroomPublic(
        id=item.id,
        venue_id=item.venue_id,
        name=item.name,
        code=item.code,
        capacity=item.capacity,
        equipment=item.equipment,
        is_active=item.is_active,
    )


def _session_resources(
    db: Session,
    user: User,
    programme_id: UUID,
    batch_id: UUID,
    trainer_id: UUID,
    venue_id: UUID,
    classroom_id: UUID | None,
) -> tuple[Programme, ProgrammeBatch, User, TrainingVenue, Classroom | None]:
    programme = db.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    ensure_institution_access(user, programme.institution_id)
    batch = db.get(ProgrammeBatch, batch_id)
    if batch is None or batch.programme_id != programme.id:
        raise HTTPException(status_code=422, detail="Batch does not belong to the programme")
    trainer = db.scalar(
        select(User)
        .where(User.id == trainer_id)
        .options(selectinload(User.roles), joinedload(User.profile))
    )
    if (
        trainer is None
        or trainer.institution_id != programme.institution_id
        or RoleCode.TRAINER not in role_codes(trainer)
    ):
        raise HTTPException(status_code=422, detail="Select a trainer from this institution")
    venue = db.get(TrainingVenue, venue_id)
    if venue is None or venue.institution_id != programme.institution_id or not venue.is_active:
        raise HTTPException(status_code=422, detail="Select an active institution venue")
    classroom = db.get(Classroom, classroom_id) if classroom_id else None
    if classroom_id and (
        classroom is None or classroom.venue_id != venue.id or not classroom.is_active
    ):
        raise HTTPException(status_code=422, detail="Classroom does not belong to the venue")
    capacity = classroom.capacity if classroom else venue.capacity
    if capacity < batch.capacity:
        raise HTTPException(
            status_code=422,
            detail="The allocated room does not have enough capacity for this batch",
        )
    return programme, batch, trainer, venue, classroom


def _check_schedule_conflicts(
    db: Session,
    *,
    trainer_id: UUID,
    venue_id: UUID,
    classroom_id: UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: UUID | None = None,
) -> None:
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="Session end time must follow start time")
    for model, resource_id in (
        (User, trainer_id),
        (TrainingVenue, venue_id),
        (Classroom, classroom_id),
    ):
        if resource_id is not None:
            db.execute(select(model.id).where(model.id == resource_id).with_for_update())
    overlap = (
        TimetableSession.starts_at < ends_at,
        TimetableSession.ends_at > starts_at,
        TimetableSession.status != ScheduleStatus.CANCELLED,
    )
    base = select(TimetableSession.id).where(*overlap)
    if exclude_id:
        base = base.where(TimetableSession.id != exclude_id)
    if db.scalar(base.where(TimetableSession.trainer_id == trainer_id)):
        raise HTTPException(status_code=409, detail="Trainer is already booked for this time")
    if classroom_id and db.scalar(base.where(TimetableSession.classroom_id == classroom_id)):
        raise HTTPException(status_code=409, detail="Classroom is already booked for this time")
    venue_conflict = base.where(TimetableSession.venue_id == venue_id)
    if classroom_id:
        venue_conflict = venue_conflict.where(TimetableSession.classroom_id.is_(None))
    if db.scalar(venue_conflict):
        raise HTTPException(status_code=409, detail="Venue is already booked for this time")


def create_session(
    db: Session, request: Request, user: User, payload: TimetableSessionCreate
) -> TimetableSessionPublic:
    programme, _, _, _, _ = _session_resources(
        db,
        user,
        payload.programme_id,
        payload.batch_id,
        payload.trainer_id,
        payload.venue_id,
        payload.classroom_id,
    )
    _check_schedule_conflicts(
        db,
        trainer_id=payload.trainer_id,
        venue_id=payload.venue_id,
        classroom_id=payload.classroom_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    item = TimetableSession(
        id=uuid4(),
        institution_id=programme.institution_id,
        created_by_id=user.id,
        **payload.model_dump(),
    )
    db.add(item)
    add_audit(db, request, "operations.session_created", user, {"session_id": str(item.id)})
    db.commit()
    return session_public(load_session(db, user, item.id))


def load_session(db: Session, user: User, session_id: UUID) -> TimetableSession:
    item = db.scalar(
        select(TimetableSession)
        .where(TimetableSession.id == session_id)
        .options(*session_options())
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Timetable session not found")
    ensure_institution_access(user, item.institution_id)
    return item


def update_session(
    db: Session,
    request: Request,
    user: User,
    session_id: UUID,
    payload: TimetableSessionUpdate,
) -> TimetableSessionPublic:
    item = load_session(db, user, session_id)
    changes = payload.model_dump(exclude_unset=True)
    trainer_id = changes.get("trainer_id", item.trainer_id)
    venue_id = changes.get("venue_id", item.venue_id)
    classroom_id = changes.get("classroom_id", item.classroom_id)
    starts_at = changes.get("starts_at", item.starts_at)
    ends_at = changes.get("ends_at", item.ends_at)
    _session_resources(
        db,
        user,
        item.programme_id,
        item.batch_id,
        trainer_id,
        venue_id,
        classroom_id,
    )
    if changes.get("status", item.status) != ScheduleStatus.CANCELLED:
        _check_schedule_conflicts(
            db,
            trainer_id=trainer_id,
            venue_id=venue_id,
            classroom_id=classroom_id,
            starts_at=starts_at,
            ends_at=ends_at,
            exclude_id=item.id,
        )
    for field, value in changes.items():
        setattr(item, field, value)
    add_audit(db, request, "operations.session_updated", user, {"session_id": str(item.id)})
    db.commit()
    return session_public(load_session(db, user, item.id))


def create_hostel(
    db: Session, request: Request, user: User, payload: HostelBuildingCreate
) -> HostelBuildingPublic:
    resolve_institution(db, user, payload.institution_id)
    item = HostelBuilding(
        id=uuid4(),
        institution_id=payload.institution_id,
        name=payload.name.strip(),
        address=payload.address.strip(),
        contact_phone=payload.contact_phone,
    )
    db.add(item)
    add_audit(db, request, "operations.hostel_created", user, {"hostel_id": str(item.id)})
    _commit_or_conflict(db, "A hostel building with this name already exists")
    db.refresh(item)
    return hostel_public(item)


def create_hostel_room(
    db: Session,
    request: Request,
    user: User,
    building_id: UUID,
    payload: HostelRoomCreate,
) -> HostelRoomPublic:
    building = db.get(HostelBuilding, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Hostel building not found")
    ensure_institution_access(user, building.institution_id)
    room = HostelRoom(
        id=uuid4(),
        building_id=building.id,
        room_number=payload.room_number.strip(),
        floor=payload.floor,
        capacity=payload.capacity,
        is_accessible=payload.is_accessible,
    )
    room.beds = [HostelBed(id=uuid4(), bed_number=number) for number in payload.bed_numbers]
    db.add(room)
    add_audit(db, request, "operations.hostel_room_created", user, {"room_id": str(room.id)})
    _commit_or_conflict(db, "This room or bed number already exists")
    db.refresh(room)
    return HostelRoomPublic(
        id=room.id,
        room_number=room.room_number,
        floor=room.floor,
        capacity=room.capacity,
        is_accessible=room.is_accessible,
        is_active=room.is_active,
        beds=[
            HostelBedPublic(id=bed.id, bed_number=bed.bed_number, is_active=bed.is_active)
            for bed in room.beds
        ],
    )


def _load_enrollment(db: Session, enrollment_id: UUID) -> ProgrammeEnrollment:
    item = db.scalar(
        select(ProgrammeEnrollment)
        .where(ProgrammeEnrollment.id == enrollment_id)
        .options(*enrollment_options())
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return item


def create_bed_allocation(
    db: Session, request: Request, user: User, payload: BedAllocationCreate
) -> BedAllocationPublic:
    bed = db.scalar(
        select(HostelBed)
        .where(HostelBed.id == payload.bed_id)
        .options(joinedload(HostelBed.room).joinedload(HostelRoom.building))
    )
    if bed is None:
        raise HTTPException(status_code=404, detail="Hostel bed not found")
    if not bed.is_active or not bed.room.is_active or not bed.room.building.is_active:
        raise HTTPException(status_code=422, detail="Select an active hostel bed")
    ensure_institution_access(user, bed.room.building.institution_id)
    enrollment = _load_enrollment(db, payload.enrollment_id)
    if enrollment.programme.institution_id != bed.room.building.institution_id:
        raise HTTPException(status_code=422, detail="Enrollment belongs to another institution")
    db.execute(select(HostelBed.id).where(HostelBed.id == bed.id).with_for_update())
    db.execute(
        select(ProgrammeEnrollment.id)
        .where(ProgrammeEnrollment.id == enrollment.id)
        .with_for_update()
    )
    overlap = (
        BedAllocation.start_date <= payload.end_date,
        BedAllocation.end_date >= payload.start_date,
        BedAllocation.status != BedAllocationStatus.CANCELLED,
    )
    if db.scalar(select(BedAllocation.id).where(BedAllocation.bed_id == bed.id, *overlap)):
        raise HTTPException(
            status_code=409, detail="Hostel bed is already allocated for these dates"
        )
    if db.scalar(
        select(BedAllocation.id).where(BedAllocation.enrollment_id == enrollment.id, *overlap)
    ):
        raise HTTPException(
            status_code=409, detail="Trainee already has accommodation for these dates"
        )
    item = BedAllocation(
        id=uuid4(),
        bed_id=bed.id,
        enrollment_id=enrollment.id,
        allocated_by_id=user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(item)
    add_audit(
        db,
        request,
        "operations.bed_allocated",
        user,
        {"allocation_id": str(item.id), "enrollment_id": str(enrollment.id)},
    )
    db.commit()
    return allocation_public(load_allocation(db, user, item.id))


def load_allocation(db: Session, user: User, allocation_id: UUID) -> BedAllocation:
    item = db.scalar(
        select(BedAllocation)
        .where(BedAllocation.id == allocation_id)
        .options(*allocation_options())
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Bed allocation not found")
    ensure_institution_access(user, item.bed.room.building.institution_id)
    return item


def set_check_in_state(
    db: Session,
    request: Request,
    user: User,
    allocation_id: UUID,
    *,
    check_out: bool,
) -> BedAllocationPublic:
    item = load_allocation(db, user, allocation_id)
    if check_out:
        if item.status != BedAllocationStatus.CHECKED_IN:
            raise HTTPException(status_code=409, detail="Only checked-in stays can be checked out")
        item.status = BedAllocationStatus.CHECKED_OUT
        item.checked_out_at = utc_now()
        event_type = "operations.hostel_checked_out"
    else:
        if item.status != BedAllocationStatus.RESERVED:
            raise HTTPException(status_code=409, detail="Only reserved stays can be checked in")
        item.status = BedAllocationStatus.CHECKED_IN
        item.checked_in_at = utc_now()
        event_type = "operations.hostel_checked_in"
    add_audit(db, request, event_type, user, {"allocation_id": str(item.id)})
    db.commit()
    return allocation_public(load_allocation(db, user, item.id))


def upsert_logistics(
    db: Session,
    request: Request,
    user: User,
    enrollment_id: UUID,
    payload: ParticipantLogisticsUpdate,
) -> ParticipantLogisticsPublic:
    enrollment = _load_enrollment(db, enrollment_id)
    ensure_institution_access(user, enrollment.programme.institution_id)
    item = db.scalar(
        select(ParticipantLogistics).where(ParticipantLogistics.enrollment_id == enrollment.id)
    )
    if item is None:
        item = ParticipantLogistics(enrollment_id=enrollment.id, **payload.model_dump())
        db.add(item)
    else:
        for field, value in payload.model_dump().items():
            setattr(item, field, value)
    add_audit(
        db,
        request,
        "operations.participant_logistics_updated",
        user,
        {"enrollment_id": str(enrollment.id)},
    )
    db.commit()
    loaded = db.scalar(
        select(ParticipantLogistics)
        .where(ParticipantLogistics.enrollment_id == enrollment.id)
        .options(*logistics_options())
        .execution_options(populate_existing=True)
    )
    assert loaded is not None
    return logistics_public(loaded)


def create_material(
    db: Session, request: Request, user: User, payload: TrainingMaterialCreate
) -> TrainingMaterialPublic:
    programme = db.get(Programme, payload.programme_id)
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    ensure_institution_access(user, programme.institution_id)
    item = TrainingMaterial(
        id=uuid4(),
        institution_id=programme.institution_id,
        programme_id=programme.id,
        name=payload.name.strip(),
        description=payload.description,
        quantity_available=payload.quantity_available,
    )
    db.add(item)
    add_audit(db, request, "operations.material_created", user, {"material_id": str(item.id)})
    _commit_or_conflict(db, "A material with this name already exists for the programme")
    loaded = db.scalar(
        select(TrainingMaterial).where(TrainingMaterial.id == item.id).options(*material_options())
    )
    assert loaded is not None
    return material_public(loaded)


def distribute_material(
    db: Session,
    request: Request,
    user: User,
    material_id: UUID,
    payload: MaterialDistributionCreate,
) -> TrainingMaterialPublic:
    item = db.scalar(
        select(TrainingMaterial)
        .where(TrainingMaterial.id == material_id)
        .options(*material_options())
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Training material not found")
    ensure_institution_access(user, item.institution_id)
    enrollment = _load_enrollment(db, payload.enrollment_id)
    if enrollment.programme_id != item.programme_id:
        raise HTTPException(status_code=422, detail="Enrollment is for another programme")
    db.execute(select(TrainingMaterial.id).where(TrainingMaterial.id == item.id).with_for_update())
    if db.scalar(
        select(MaterialDistribution.id).where(
            MaterialDistribution.material_id == item.id,
            MaterialDistribution.enrollment_id == enrollment.id,
        )
    ):
        raise HTTPException(status_code=409, detail="Material was already distributed to trainee")
    distributed = db.scalar(
        select(func.coalesce(func.sum(MaterialDistribution.quantity), 0)).where(
            MaterialDistribution.material_id == item.id
        )
    )
    if int(distributed or 0) + payload.quantity > item.quantity_available:
        raise HTTPException(status_code=409, detail="Not enough material stock is available")
    db.add(
        MaterialDistribution(
            material_id=item.id,
            enrollment_id=enrollment.id,
            distributed_by_id=user.id,
            quantity=payload.quantity,
        )
    )
    add_audit(
        db,
        request,
        "operations.material_distributed",
        user,
        {"material_id": str(item.id), "enrollment_id": str(enrollment.id)},
    )
    db.commit()
    loaded = db.scalar(
        select(TrainingMaterial)
        .where(TrainingMaterial.id == item.id)
        .options(*material_options())
        .execution_options(populate_existing=True)
    )
    assert loaded is not None
    return material_public(loaded)


def _issue_institution(
    db: Session, user: User, payload: OperationsIssueCreate, self_report: bool
) -> tuple[Institution, ProgrammeEnrollment | None]:
    enrollment = _load_enrollment(db, payload.enrollment_id) if payload.enrollment_id else None
    if self_report:
        if enrollment is None or enrollment.trainee_id != user.id:
            raise HTTPException(status_code=403, detail="You can report issues only for yourself")
        institution_id = enrollment.programme.institution_id
    elif enrollment:
        institution_id = enrollment.programme.institution_id
        if payload.institution_id and payload.institution_id != institution_id:
            raise HTTPException(status_code=422, detail="Enrollment belongs to another institution")
    elif payload.institution_id:
        institution_id = payload.institution_id
    else:
        raise HTTPException(status_code=422, detail="Institution or enrollment is required")
    return resolve_institution(db, user, institution_id) if not self_report else _get_institution(
        db, institution_id
    ), enrollment


def _get_institution(db: Session, institution_id: UUID) -> Institution:
    item = db.get(Institution, institution_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return item


def create_issue(
    db: Session,
    request: Request,
    user: User,
    payload: OperationsIssueCreate,
    *,
    self_report: bool,
) -> OperationsIssuePublic:
    institution, enrollment = _issue_institution(db, user, payload, self_report)
    item = OperationsIssue(
        id=uuid4(),
        institution_id=institution.id,
        enrollment_id=enrollment.id if enrollment else None,
        reported_by_id=user.id,
        issue_type=payload.issue_type,
        priority=payload.priority,
        title=payload.title.strip(),
        description=payload.description.strip(),
        location=payload.location,
    )
    db.add(item)
    add_audit(db, request, "operations.issue_reported", user, {"issue_id": str(item.id)})
    db.commit()
    return issue_public(load_issue(db, item.id))


def load_issue(db: Session, issue_id: UUID) -> OperationsIssue:
    item = db.scalar(
        select(OperationsIssue)
        .where(OperationsIssue.id == issue_id)
        .options(*issue_options())
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Operations issue not found")
    return item


def update_issue(
    db: Session,
    request: Request,
    user: User,
    issue_id: UUID,
    payload: OperationsIssueUpdate,
) -> OperationsIssuePublic:
    item = load_issue(db, issue_id)
    ensure_institution_access(user, item.institution_id)
    if payload.status in {OperationsIssueStatus.RESOLVED, OperationsIssueStatus.CLOSED}:
        if not payload.resolution_notes or len(payload.resolution_notes.strip()) < 5:
            raise HTTPException(status_code=422, detail="Resolution notes are required")
        item.resolved_by_id = user.id
        item.resolved_at = utc_now()
    else:
        item.resolved_by_id = None
        item.resolved_at = None
    item.status = payload.status
    item.resolution_notes = payload.resolution_notes
    add_audit(db, request, "operations.issue_updated", user, {"issue_id": str(item.id)})
    db.commit()
    return issue_public(load_issue(db, item.id))


def get_trainee_operations(db: Session, user: User) -> TraineeOperationsPublic:
    enrollments = db.scalars(
        select(ProgrammeEnrollment)
        .where(
            ProgrammeEnrollment.trainee_id == user.id,
            ProgrammeEnrollment.status != EnrollmentStatus.WITHDRAWN,
        )
        .options(*enrollment_options())
        .order_by(ProgrammeEnrollment.enrolled_at.desc())
    ).all()
    results: list[TraineeProgrammeOperations] = []
    for enrollment in enrollments:
        sessions = (
            db.scalars(
                select(TimetableSession)
                .where(
                    TimetableSession.batch_id == enrollment.batch_id,
                    TimetableSession.status != ScheduleStatus.CANCELLED,
                )
                .options(*session_options())
                .order_by(TimetableSession.starts_at)
            ).all()
            if enrollment.batch_id
            else []
        )
        logistics = db.scalar(
            select(ParticipantLogistics)
            .where(ParticipantLogistics.enrollment_id == enrollment.id)
            .options(*logistics_options())
        )
        allocation = db.scalar(
            select(BedAllocation)
            .where(
                BedAllocation.enrollment_id == enrollment.id,
                BedAllocation.status != BedAllocationStatus.CANCELLED,
            )
            .options(*allocation_options())
            .order_by(BedAllocation.end_date.desc())
        )
        materials = (
            db.scalars(
                select(TrainingMaterial)
                .join(TrainingMaterial.distributions)
                .where(MaterialDistribution.enrollment_id == enrollment.id)
                .options(*material_options())
                .order_by(TrainingMaterial.name)
            )
            .unique()
            .all()
        )
        issues = db.scalars(
            select(OperationsIssue)
            .where(
                OperationsIssue.enrollment_id == enrollment.id,
                OperationsIssue.institution_id == enrollment.programme.institution_id,
            )
            .options(*issue_options())
            .order_by(OperationsIssue.created_at.desc())
        ).all()
        results.append(
            TraineeProgrammeOperations(
                enrollment_id=enrollment.id,
                programme_id=enrollment.programme_id,
                programme_title=enrollment.programme.title,
                programme_code=enrollment.programme.code,
                batch_name=enrollment.batch.name if enrollment.batch else None,
                timetable=[session_public(value) for value in sessions],
                logistics=logistics_public(logistics) if logistics else None,
                accommodation=allocation_public(allocation) if allocation else None,
                materials=[material_public(value, enrollment.id) for value in materials],
                issues=[issue_public(value) for value in issues],
            )
        )
    return TraineeOperationsPublic(programmes=results)
