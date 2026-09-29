from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.permissions import Permission
from app.core.uploads import attachment_header
from app.db.session import get_db
from app.models import EmployerVerificationStatus
from app.schemas.auth import MessageResponse
from app.schemas.employment import (
    CandidatePublic,
    CandidateShortlistCreate,
    EmployerCompanyUpdate,
    EmployerProfilePublic,
    EmployerVerificationUpdate,
    EmployerWorkspacePublic,
    EmploymentProfilePublic,
    EmploymentProfileUpdate,
    JobApplicationCreate,
    JobApplicationPublic,
    JobApplicationStatusUpdate,
    JobCreate,
    JobPublic,
    JobUpdate,
    TraineeEmploymentWorkspacePublic,
)
from app.services import employment as employment_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/admin/employers", response_model=list[EmployerProfilePublic])
def get_employers(
    db: DbSession,
    _: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_VERIFY))],
    verification_status: EmployerVerificationStatus | None = None,
) -> list[EmployerProfilePublic]:
    return employment_service.list_employers(db, verification_status)


@router.patch(
    "/admin/employers/{profile_id}/verification",
    response_model=EmployerProfilePublic,
)
def decide_employer_verification(
    profile_id: UUID,
    payload: EmployerVerificationUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_VERIFY))],
) -> EmployerProfilePublic:
    return employment_service.verify_employer(db, request, auth.user, profile_id, payload)


@router.get("/employer/workspace", response_model=EmployerWorkspacePublic)
def get_employer_workspace(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> EmployerWorkspacePublic:
    return employment_service.employer_workspace(db, auth.user)


@router.get("/employer/profile", response_model=EmployerProfilePublic)
def get_employer_profile(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> EmployerProfilePublic:
    return employment_service.employer_public(
        employment_service.load_employer_profile(db, auth.user)
    )


@router.put("/employer/profile", response_model=EmployerProfilePublic)
def update_employer_profile(
    payload: EmployerCompanyUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> EmployerProfilePublic:
    return employment_service.update_employer_profile(db, request, auth.user, payload)


@router.post("/employer/jobs", response_model=JobPublic, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> JobPublic:
    return employment_service.create_job(db, request, auth.user, payload)


@router.put("/employer/jobs/{job_id}", response_model=JobPublic)
def update_job(
    job_id: UUID,
    payload: JobUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> JobPublic:
    return employment_service.update_job(db, request, auth.user, job_id, payload)


@router.post("/employer/jobs/{job_id}/publish", response_model=JobPublic)
def publish_job(
    job_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> JobPublic:
    return employment_service.publish_job(db, request, auth.user, job_id)


@router.post("/employer/jobs/{job_id}/close", response_model=JobPublic)
def close_job(
    job_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> JobPublic:
    return employment_service.close_job(db, request, auth.user, job_id)


@router.get("/employer/candidates", response_model=list[CandidatePublic])
def get_candidates(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
    job_id: UUID | None = None,
    skill: str | None = None,
    course_id: UUID | None = None,
    certificate_number: str | None = None,
    location: str | None = None,
) -> list[CandidatePublic]:
    return employment_service.search_candidates(
        db,
        auth.user,
        job_id=job_id,
        skill=skill,
        course_id=course_id,
        certificate_number=certificate_number,
        location=location,
    )


@router.post(
    "/employer/jobs/{job_id}/shortlist",
    response_model=CandidatePublic,
    status_code=status.HTTP_201_CREATED,
)
def shortlist_candidate(
    job_id: UUID,
    payload: CandidateShortlistCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> CandidatePublic:
    return employment_service.shortlist_candidate(db, request, auth.user, job_id, payload)


@router.get("/employer/candidates/{trainee_id}/resume")
def download_candidate_resume(
    trainee_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> Response:
    profile = employment_service.employer_resume(db, auth.user, trainee_id)
    return Response(
        content=profile.resume_content or b"",
        media_type=profile.resume_content_type or "application/octet-stream",
        headers={"Content-Disposition": attachment_header(profile.resume_filename or "resume")},
    )


@router.patch("/employer/applications/{application_id}", response_model=JobApplicationPublic)
def update_application_status(
    application_id: UUID,
    payload: JobApplicationStatusUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_MANAGE))],
) -> JobApplicationPublic:
    return employment_service.update_application_status(
        db, request, auth.user, application_id, payload
    )


@router.get("/me/workspace", response_model=TraineeEmploymentWorkspacePublic)
def get_trainee_workspace(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> TraineeEmploymentWorkspacePublic:
    return employment_service.trainee_workspace(db, auth.user)


@router.get("/me/profile", response_model=EmploymentProfilePublic)
def get_employment_profile(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> EmploymentProfilePublic:
    return employment_service.employment_profile_public(db, auth.user)


@router.put("/me/profile", response_model=EmploymentProfilePublic)
def update_employment_profile(
    payload: EmploymentProfileUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> EmploymentProfilePublic:
    return employment_service.update_employment_profile(db, request, auth.user, payload)


@router.post("/me/resume", response_model=EmploymentProfilePublic)
async def upload_resume(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
    file: Annotated[UploadFile, File()],
) -> EmploymentProfilePublic:
    return await employment_service.upload_resume(db, request, auth.user, file)


@router.get("/me/resume")
def download_own_resume(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> Response:
    profile = employment_service.trainee_resume(db, auth.user)
    return Response(
        content=profile.resume_content or b"",
        media_type=profile.resume_content_type or "application/octet-stream",
        headers={"Content-Disposition": attachment_header(profile.resume_filename or "resume")},
    )


@router.get("/jobs", response_model=list[JobPublic])
def search_jobs(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
    query: Annotated[str | None, Query(max_length=120)] = None,
    location: Annotated[str | None, Query(max_length=120)] = None,
    skill: Annotated[str | None, Query(max_length=120)] = None,
    programme_id: UUID | None = None,
) -> list[JobPublic]:
    return employment_service.list_jobs(
        db,
        auth.user,
        query=query,
        location=location,
        skill=skill,
        programme_id=programme_id,
    )


@router.get("/jobs/recommendations", response_model=list[JobPublic])
def get_recommendations(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> list[JobPublic]:
    return employment_service.recommendations(db, auth.user)


@router.post("/jobs/{job_id}/save", response_model=JobPublic)
def save_job(
    job_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> JobPublic:
    return employment_service.save_job(db, auth.user, job_id)


@router.delete("/jobs/{job_id}/save", response_model=MessageResponse)
def unsave_job(
    job_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> MessageResponse:
    employment_service.unsave_job(db, auth.user, job_id)
    return MessageResponse(message="Job removed from saved jobs")


@router.post(
    "/jobs/{job_id}/apply",
    response_model=JobApplicationPublic,
    status_code=status.HTTP_201_CREATED,
)
def apply_for_job(
    job_id: UUID,
    payload: JobApplicationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> JobApplicationPublic:
    return employment_service.apply_for_job(db, request, auth.user, job_id, payload)


@router.get("/me/applications", response_model=list[JobApplicationPublic])
def get_my_applications(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> list[JobApplicationPublic]:
    return employment_service.trainee_applications(db, auth.user)


@router.post(
    "/me/applications/{application_id}/withdraw",
    response_model=JobApplicationPublic,
)
def withdraw_application(
    application_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYMENT_SELF))],
) -> JobApplicationPublic:
    return employment_service.withdraw_application(db, request, auth.user, application_id)
