from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.permissions import Permission
from app.core.uploads import attachment_header
from app.db.session import get_db
from app.models import (
    CooperativeMembership,
    EducationRecord,
    EmploymentRecord,
    InstitutionType,
    ProfileDocumentType,
    User,
)
from app.schemas.profile import (
    ConsentPreferences,
    DocumentValidationUpdate,
    EducationCreate,
    EmploymentCreate,
    InstitutionCreate,
    InstitutionListResponse,
    InstitutionPublic,
    InstitutionUpdate,
    MembershipCreate,
    PersonalProfileUpdate,
    ProfileDocumentPublic,
    TraineeListResponse,
    TraineeProfileDetail,
    TrainerListResponse,
)
from app.services import profiles as profile_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


@router.get("/me", response_model=TraineeProfileDetail)
def get_my_profile(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile_service.ensure_trainee(auth.user)
    profile = profile_service.load_profile(db, auth.user.id, create=True)
    return profile_service.profile_detail(db, profile)


@router.patch("/me", response_model=TraineeProfileDetail)
def update_my_profile(
    payload: PersonalProfileUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.update_personal(db, request, auth.user, payload)
    return profile_service.profile_detail(db, profile)


@router.put("/me/consents", response_model=TraineeProfileDetail)
def update_my_consents(
    payload: ConsentPreferences,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.update_consents(db, request, auth.user, payload)
    return profile_service.profile_detail(db, profile)


@router.post("/me/education", response_model=TraineeProfileDetail, status_code=201)
def create_education(
    payload: EducationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.add_education(db, request, auth.user, payload)
    return profile_service.profile_detail(db, profile)


@router.delete("/me/education/{record_id}", response_model=TraineeProfileDetail)
def delete_education(
    record_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.delete_record(
        db, request, auth.user, EducationRecord, record_id, "profile.education_deleted"
    )
    return profile_service.profile_detail(db, profile)


@router.post("/me/employment", response_model=TraineeProfileDetail, status_code=201)
def create_employment(
    payload: EmploymentCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.add_employment(db, request, auth.user, payload)
    return profile_service.profile_detail(db, profile)


@router.delete("/me/employment/{record_id}", response_model=TraineeProfileDetail)
def delete_employment(
    record_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.delete_record(
        db, request, auth.user, EmploymentRecord, record_id, "profile.employment_deleted"
    )
    return profile_service.profile_detail(db, profile)


@router.post("/me/memberships", response_model=TraineeProfileDetail, status_code=201)
def create_membership(
    payload: MembershipCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.add_membership(db, request, auth.user, payload)
    return profile_service.profile_detail(db, profile)


@router.delete("/me/memberships/{record_id}", response_model=TraineeProfileDetail)
def delete_membership(
    record_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
) -> TraineeProfileDetail:
    profile = profile_service.delete_record(
        db,
        request,
        auth.user,
        CooperativeMembership,
        record_id,
        "profile.membership_deleted",
    )
    return profile_service.profile_detail(db, profile)


@router.post("/me/documents", response_model=TraineeProfileDetail, status_code=201)
async def upload_profile_document(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_SELF_MANAGE))],
    document_type: Annotated[ProfileDocumentType, Form()],
    document: Annotated[UploadFile, File()],
) -> TraineeProfileDetail:
    profile = await profile_service.store_document(db, request, auth.user, document, document_type)
    return profile_service.profile_detail(db, profile)


@router.get("/documents/{document_id}")
def download_profile_document(
    document_id: UUID, request: Request, db: DbSession, auth: CurrentAuth
) -> Response:
    document = profile_service.load_document_for_user(db, auth.user, document_id)
    profile_service.add_profile_audit(
        db,
        request,
        auth.user,
        "profile.document_downloaded",
        document.profile.user_id,
        document_id=str(document.id),
    )
    db.commit()
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={"Content-Disposition": attachment_header(document.filename)},
    )


@router.patch("/documents/{document_id}/validation", response_model=ProfileDocumentPublic)
def update_document_validation(
    document_id: UUID,
    payload: DocumentValidationUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_DOCUMENT_VALIDATE))],
) -> ProfileDocumentPublic:
    document = profile_service.load_document_for_user(db, auth.user, document_id)
    updated = profile_service.validate_document(
        db, request, auth.user, document, payload.status, payload.notes
    )
    return profile_service.document_public(updated)


@router.get("/trainees", response_model=TraineeListResponse)
def get_trainees(
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.PROFILE_TRAINEE_DIRECTORY_VIEW))
    ],
    q: Annotated[str | None, Query(max_length=120)] = None,
    institution_id: UUID | None = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    language: Annotated[str | None, Query(max_length=80)] = None,
    skill: Annotated[str | None, Query(max_length=80)] = None,
    minimum_completion: Annotated[int | None, Query(ge=0, le=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TraineeListResponse:
    return profile_service.list_trainees(
        db,
        auth.user,
        query_text=q,
        institution_id=institution_id,
        state_name=state,
        language=language,
        skill=skill,
        minimum_completion=minimum_completion,
        page=page,
        page_size=page_size,
    )


@router.get("/trainers", response_model=TrainerListResponse)
def get_trainers(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_ADMIN_VIEW))],
    q: Annotated[str | None, Query(max_length=120)] = None,
    institution_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TrainerListResponse:
    return profile_service.list_trainers(
        db,
        auth.user,
        query_text=q,
        institution_id=institution_id,
        page=page,
        page_size=page_size,
    )


@router.get("/trainees/{trainee_id}", response_model=TraineeProfileDetail)
def get_trainee_profile(
    trainee_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.PROFILE_ADMIN_VIEW))],
) -> TraineeProfileDetail:
    trainee = db.get(User, trainee_id)
    if trainee is None:
        raise HTTPException(status_code=404, detail="Trainee profile not found")
    profile_service.ensure_trainee_access(db, auth.user, trainee)
    profile_service.add_profile_audit(
        db, request, auth.user, "profile.administrator_viewed", trainee.id
    )
    db.commit()
    profile = profile_service.load_profile(db, trainee.id, create=True)
    return profile_service.profile_detail(db, profile)


@router.get("/institutions", response_model=InstitutionListResponse)
def get_institutions(
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.PROFILE_INSTITUTION_MANAGE))
    ],
    q: Annotated[str | None, Query(max_length=120)] = None,
    institution_type: InstitutionType | None = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    active_only: bool = True,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InstitutionListResponse:
    return profile_service.list_institutions(
        db,
        auth.user,
        query_text=q,
        institution_type=institution_type,
        state_name=state,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )


@router.post("/institutions", response_model=InstitutionPublic, status_code=201)
def create_institution(
    payload: InstitutionCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.PLATFORM_MANAGE))
    ],
) -> InstitutionPublic:
    institution = profile_service.create_institution(db, request, auth.user, payload)
    return profile_service.institution_public(institution)


@router.get("/institutions/{institution_id}", response_model=InstitutionPublic)
def get_institution(
    institution_id: UUID,
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.PROFILE_INSTITUTION_MANAGE))
    ],
) -> InstitutionPublic:
    return profile_service.institution_public(
        profile_service.get_institution(db, auth.user, institution_id)
    )


@router.patch("/institutions/{institution_id}", response_model=InstitutionPublic)
def update_institution(
    institution_id: UUID,
    payload: InstitutionUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.PROFILE_INSTITUTION_MANAGE))
    ],
) -> InstitutionPublic:
    institution = profile_service.get_institution(db, auth.user, institution_id)
    updated = profile_service.update_institution(db, request, auth.user, institution, payload)
    return profile_service.institution_public(updated)
