from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.operations import (
    BedAllocationCreate,
    BedAllocationPublic,
    ClassroomCreate,
    ClassroomPublic,
    HostelBuildingCreate,
    HostelBuildingPublic,
    HostelRoomCreate,
    HostelRoomPublic,
    MaterialDistributionCreate,
    OperationsIssueCreate,
    OperationsIssuePublic,
    OperationsIssueUpdate,
    OperationsWorkspacePublic,
    ParticipantLogisticsPublic,
    ParticipantLogisticsUpdate,
    TimetableSessionCreate,
    TimetableSessionPublic,
    TimetableSessionUpdate,
    TraineeOperationsPublic,
    TrainingMaterialCreate,
    TrainingMaterialPublic,
    VenueCreate,
    VenuePublic,
)
from app.services import operations as operations_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
ManageAuth = Annotated[AuthContext, Depends(require_permission(Permission.OPERATIONS_MANAGE))]
SelfAuth = Annotated[AuthContext, Depends(require_permission(Permission.OPERATIONS_SELF))]


@router.get("/workspace", response_model=OperationsWorkspacePublic)
def get_operations_workspace(
    db: DbSession,
    auth: ManageAuth,
    institution_id: Annotated[UUID | None, Query()] = None,
) -> OperationsWorkspacePublic:
    return operations_service.get_workspace(db, auth.user, institution_id)


@router.get("/me", response_model=TraineeOperationsPublic)
def get_my_operations(db: DbSession, auth: SelfAuth) -> TraineeOperationsPublic:
    return operations_service.get_trainee_operations(db, auth.user)


@router.post("/venues", response_model=VenuePublic, status_code=201)
def create_venue(
    payload: VenueCreate, request: Request, db: DbSession, auth: ManageAuth
) -> VenuePublic:
    return operations_service.create_venue(db, request, auth.user, payload)


@router.post("/classrooms", response_model=ClassroomPublic, status_code=201)
def create_classroom(
    payload: ClassroomCreate, request: Request, db: DbSession, auth: ManageAuth
) -> ClassroomPublic:
    return operations_service.create_classroom(db, request, auth.user, payload)


@router.post("/timetable", response_model=TimetableSessionPublic, status_code=201)
def create_timetable_session(
    payload: TimetableSessionCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> TimetableSessionPublic:
    return operations_service.create_session(db, request, auth.user, payload)


@router.patch("/timetable/{session_id}", response_model=TimetableSessionPublic)
def update_timetable_session(
    session_id: UUID,
    payload: TimetableSessionUpdate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> TimetableSessionPublic:
    return operations_service.update_session(db, request, auth.user, session_id, payload)


@router.post("/hostels", response_model=HostelBuildingPublic, status_code=201)
def create_hostel(
    payload: HostelBuildingCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> HostelBuildingPublic:
    return operations_service.create_hostel(db, request, auth.user, payload)


@router.post("/hostels/{building_id}/rooms", response_model=HostelRoomPublic, status_code=201)
def create_hostel_room(
    building_id: UUID,
    payload: HostelRoomCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> HostelRoomPublic:
    return operations_service.create_hostel_room(db, request, auth.user, building_id, payload)


@router.post("/bed-allocations", response_model=BedAllocationPublic, status_code=201)
def allocate_bed(
    payload: BedAllocationCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> BedAllocationPublic:
    return operations_service.create_bed_allocation(db, request, auth.user, payload)


@router.post("/bed-allocations/{allocation_id}/check-in", response_model=BedAllocationPublic)
def check_in(
    allocation_id: UUID, request: Request, db: DbSession, auth: ManageAuth
) -> BedAllocationPublic:
    return operations_service.set_check_in_state(
        db, request, auth.user, allocation_id, check_out=False
    )


@router.post("/bed-allocations/{allocation_id}/check-out", response_model=BedAllocationPublic)
def check_out(
    allocation_id: UUID, request: Request, db: DbSession, auth: ManageAuth
) -> BedAllocationPublic:
    return operations_service.set_check_in_state(
        db, request, auth.user, allocation_id, check_out=True
    )


@router.put(
    "/enrollments/{enrollment_id}/logistics",
    response_model=ParticipantLogisticsPublic,
)
def update_participant_logistics(
    enrollment_id: UUID,
    payload: ParticipantLogisticsUpdate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> ParticipantLogisticsPublic:
    return operations_service.upsert_logistics(db, request, auth.user, enrollment_id, payload)


@router.post("/materials", response_model=TrainingMaterialPublic, status_code=201)
def create_training_material(
    payload: TrainingMaterialCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> TrainingMaterialPublic:
    return operations_service.create_material(db, request, auth.user, payload)


@router.post(
    "/materials/{material_id}/distributions",
    response_model=TrainingMaterialPublic,
    status_code=201,
)
def distribute_training_material(
    material_id: UUID,
    payload: MaterialDistributionCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> TrainingMaterialPublic:
    return operations_service.distribute_material(db, request, auth.user, material_id, payload)


@router.post("/issues/me", response_model=OperationsIssuePublic, status_code=201)
def report_my_issue(
    payload: OperationsIssueCreate,
    request: Request,
    db: DbSession,
    auth: SelfAuth,
) -> OperationsIssuePublic:
    return operations_service.create_issue(db, request, auth.user, payload, self_report=True)


@router.post("/issues", response_model=OperationsIssuePublic, status_code=201)
def create_operations_issue(
    payload: OperationsIssueCreate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> OperationsIssuePublic:
    return operations_service.create_issue(db, request, auth.user, payload, self_report=False)


@router.patch("/issues/{issue_id}", response_model=OperationsIssuePublic)
def update_operations_issue(
    issue_id: UUID,
    payload: OperationsIssueUpdate,
    request: Request,
    db: DbSession,
    auth: ManageAuth,
) -> OperationsIssuePublic:
    return operations_service.update_issue(db, request, auth.user, issue_id, payload)
