from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.permissions import Permission
from app.core.uploads import attachment_header
from app.db.session import get_db
from app.models import (
    DocumentType,
    EligibilityType,
    Institution,
    InstitutionType,
    ProgrammeBatch,
    ProgrammeMode,
    ProgrammeStatus,
)
from app.schemas.programme import (
    BatchTrainerPublic,
    BulkNominationResult,
    DocumentPublic,
    InstitutionBrief,
    ProgrammeApplicationCreate,
    ProgrammeApplicationPublic,
    ProgrammeBatchCreate,
    ProgrammeBatchPublic,
    ProgrammeCreate,
    ProgrammeDecision,
    ProgrammeDetail,
    ProgrammeListResponse,
    ProgrammeNominationCreate,
    ProgrammeNominationPublic,
    ProgrammeUpdate,
    ReviewUpdate,
    TrainerAssignmentCreate,
    TrainerBrief,
)
from app.services import programmes as programme_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


@router.get("", response_model=ProgrammeListResponse)
def get_programmes(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_VIEW))],
    q: Annotated[str | None, Query(max_length=120)] = None,
    status: ProgrammeStatus | None = None,
    mode: ProgrammeMode | None = None,
    language: Annotated[str | None, Query(max_length=80)] = None,
    institution_id: UUID | None = None,
) -> ProgrammeListResponse:
    items = programme_service.list_programmes(
        db,
        auth.user,
        query_text=q,
        programme_status=status,
        mode=mode,
        language=language,
        institution_id=institution_id,
    )
    return ProgrammeListResponse(items=items, total=len(items))


@router.post("", response_model=ProgrammeDetail, status_code=201)
def create_programme(
    payload: ProgrammeCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeDetail:
    programme = programme_service.create_programme(db, request, auth.user, payload)
    return programme_service.programme_detail(db, programme, auth.user)


@router.get("/applications", response_model=list[ProgrammeApplicationPublic])
def get_applications(
    db: DbSession,
    auth: CurrentAuth,
    programme_id: UUID | None = None,
) -> list[ProgrammeApplicationPublic]:
    if not (
        programme_service.user_has(auth.user, Permission.APPLICATIONS_APPLY)
        or programme_service.user_has(auth.user, Permission.APPLICATIONS_REVIEW)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    return programme_service.list_applications(db, auth.user, programme_id)


@router.patch("/applications/{application_id}", response_model=ProgrammeApplicationPublic)
def update_application_status(
    application_id: UUID,
    payload: ReviewUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
) -> ProgrammeApplicationPublic:
    application = programme_service.load_application(db, application_id)
    updated = programme_service.review_application(db, request, auth.user, application, payload)
    return programme_service.application_public(updated)


@router.post(
    "/applications/{application_id}/documents",
    response_model=DocumentPublic,
    status_code=201,
)
async def upload_application_document(
    application_id: UUID,
    request: Request,
    db: DbSession,
    auth: CurrentAuth,
    document_type: Annotated[DocumentType, Form()],
    document: Annotated[UploadFile, File()],
) -> DocumentPublic:
    application = programme_service.load_application(db, application_id)
    stored = await programme_service.store_document(
        db,
        request,
        auth.user,
        document,
        document_type,
        application=application,
    )
    return programme_service.document_public(stored)


@router.get("/nominations", response_model=list[ProgrammeNominationPublic])
def get_nominations(
    db: DbSession,
    auth: CurrentAuth,
    programme_id: UUID | None = None,
) -> list[ProgrammeNominationPublic]:
    if not (
        programme_service.user_has(auth.user, Permission.NOMINATIONS_CREATE)
        or programme_service.user_has(auth.user, Permission.APPLICATIONS_REVIEW)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    return programme_service.list_nominations(db, auth.user, programme_id)


@router.patch("/nominations/{nomination_id}", response_model=ProgrammeNominationPublic)
def update_nomination_status(
    nomination_id: UUID,
    payload: ReviewUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
) -> ProgrammeNominationPublic:
    nomination = programme_service.load_nomination(db, nomination_id)
    updated = programme_service.review_nomination(db, request, auth.user, nomination, payload)
    return programme_service.nomination_public(updated)


@router.post(
    "/nominations/{nomination_id}/documents",
    response_model=DocumentPublic,
    status_code=201,
)
async def upload_nomination_document(
    nomination_id: UUID,
    request: Request,
    db: DbSession,
    auth: CurrentAuth,
    document_type: Annotated[DocumentType, Form()],
    document: Annotated[UploadFile, File()],
) -> DocumentPublic:
    nomination = programme_service.load_nomination(db, nomination_id)
    stored = await programme_service.store_document(
        db,
        request,
        auth.user,
        document,
        document_type,
        nomination=nomination,
    )
    return programme_service.document_public(stored)


@router.get("/documents/{document_id}")
def download_document(document_id: UUID, db: DbSession, auth: CurrentAuth) -> Response:
    document = programme_service.load_document_for_user(db, auth.user, document_id)
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={"Content-Disposition": attachment_header(document.filename)},
    )


@router.get("/trainers", response_model=list[TrainerBrief])
def get_trainers(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> list[TrainerBrief]:
    return programme_service.list_trainers(db, auth.user)


@router.get("/institutions", response_model=list[InstitutionBrief])
def get_training_institutions(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_APPROVE))],
) -> list[InstitutionBrief]:
    del auth
    institutions = db.scalars(
        select(Institution)
        .where(
            Institution.institution_type.in_(
                [
                    InstitutionType.TRAINING_INSTITUTE,
                    InstitutionType.VAMNICOM,
                    InstitutionType.RICM,
                    InstitutionType.ICM,
                ]
            ),
            Institution.is_active.is_(True),
        )
        .order_by(Institution.name)
    )
    return [InstitutionBrief(id=item.id, name=item.name, code=item.code) for item in institutions]


@router.get("/{programme_id}", response_model=ProgrammeDetail)
def get_programme(programme_id: UUID, db: DbSession, auth: CurrentAuth) -> ProgrammeDetail:
    if not programme_service.user_has(auth.user, Permission.PROGRAMMES_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    programme = programme_service.load_programme(db, programme_id)
    programme_service.ensure_visible(auth.user, programme)
    return programme_service.programme_detail(db, programme, auth.user)


@router.patch("/{programme_id}", response_model=ProgrammeDetail)
def edit_programme(
    programme_id: UUID,
    payload: ProgrammeUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeDetail:
    programme = programme_service.load_programme(db, programme_id)
    updated = programme_service.update_programme(db, request, auth.user, programme, payload)
    return programme_service.programme_detail(db, updated, auth.user)


@router.post("/{programme_id}/batches", response_model=ProgrammeBatchPublic, status_code=201)
def create_batch(
    programme_id: UUID,
    payload: ProgrammeBatchCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeBatchPublic:
    programme = programme_service.load_programme(db, programme_id)
    batch = programme_service.add_batch(db, request, auth.user, programme, payload)
    reloaded = programme_service.load_programme(db, programme_id)
    created = next(item for item in reloaded.batches if item.id == batch.id)
    return programme_service.batch_public(created)


@router.post(
    "/batches/{batch_id}/trainers",
    response_model=BatchTrainerPublic,
    status_code=201,
)
def create_trainer_assignment(
    batch_id: UUID,
    payload: TrainerAssignmentCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> BatchTrainerPublic:
    batch = db.get(ProgrammeBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    assignment = programme_service.assign_trainer(db, request, auth.user, batch, payload.trainer_id)
    programme = programme_service.load_programme(db, batch.programme_id)
    reloaded_batch = next(item for item in programme.batches if item.id == batch.id)
    return next(
        item
        for item in programme_service.batch_public(reloaded_batch).trainers
        if item.id == assignment.id
    )


def transition(
    programme_id: UUID,
    target: ProgrammeStatus,
    request: Request,
    db: Session,
    auth: AuthContext,
    reason: str | None = None,
) -> ProgrammeDetail:
    programme = programme_service.load_programme(db, programme_id)
    updated = programme_service.transition_programme(
        db, request, auth.user, programme, target, reason
    )
    return programme_service.programme_detail(db, updated, auth.user)


@router.post("/{programme_id}/submit", response_model=ProgrammeDetail)
def submit_programme(
    programme_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeDetail:
    return transition(programme_id, ProgrammeStatus.PENDING_APPROVAL, request, db, auth)


@router.post("/{programme_id}/approve", response_model=ProgrammeDetail)
def approve_programme(
    programme_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_APPROVE))],
) -> ProgrammeDetail:
    return transition(programme_id, ProgrammeStatus.APPROVED, request, db, auth)


@router.post("/{programme_id}/reject", response_model=ProgrammeDetail)
def reject_programme(
    programme_id: UUID,
    payload: ProgrammeDecision,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_APPROVE))],
) -> ProgrammeDetail:
    return transition(programme_id, ProgrammeStatus.REJECTED, request, db, auth, payload.reason)


@router.post("/{programme_id}/publish", response_model=ProgrammeDetail)
def publish_programme(
    programme_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeDetail:
    return transition(programme_id, ProgrammeStatus.PUBLISHED, request, db, auth)


@router.post("/{programme_id}/archive", response_model=ProgrammeDetail)
def archive_programme(
    programme_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROGRAMMES_MANAGE))],
) -> ProgrammeDetail:
    return transition(programme_id, ProgrammeStatus.ARCHIVED, request, db, auth)


@router.post(
    "/{programme_id}/applications",
    response_model=ProgrammeApplicationPublic,
    status_code=201,
)
def apply_to_programme(
    programme_id: UUID,
    payload: ProgrammeApplicationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.APPLICATIONS_APPLY))],
) -> ProgrammeApplicationPublic:
    programme = programme_service.load_programme(db, programme_id)
    application = programme_service.create_application(db, request, auth.user, programme, payload)
    return programme_service.application_public(application)


@router.post(
    "/{programme_id}/nominations",
    response_model=ProgrammeNominationPublic,
    status_code=201,
)
def nominate_candidate(
    programme_id: UUID,
    payload: ProgrammeNominationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.NOMINATIONS_CREATE))],
) -> ProgrammeNominationPublic:
    programme = programme_service.load_programme(db, programme_id)
    nomination = programme_service.create_nomination(db, request, auth.user, programme, payload)
    return programme_service.nomination_public(nomination)


@router.post(
    "/{programme_id}/nominations/bulk",
    response_model=BulkNominationResult,
    status_code=201,
)
async def bulk_nominate_candidates(
    programme_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.NOMINATIONS_CREATE))],
    nomination_type: Annotated[EligibilityType, Form()],
    csv_file: Annotated[UploadFile, File()],
) -> BulkNominationResult:
    programme = programme_service.load_programme(db, programme_id)
    return await programme_service.create_bulk_nominations(
        db, request, auth.user, programme, nomination_type, csv_file
    )
