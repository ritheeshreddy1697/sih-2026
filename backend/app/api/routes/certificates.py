from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.certificate import (
    CertificateCandidatePublic,
    CertificateIssue,
    CertificatePolicyPublic,
    CertificatePolicyUpdate,
    CertificateRecordPublic,
    CertificateRevoke,
    CertificateVerificationPublic,
    SkillWalletPublic,
)
from app.services import certificates as certificate_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/verify/{token}", response_model=CertificateVerificationPublic)
def verify_certificate(token: str, db: DbSession) -> CertificateVerificationPublic:
    return certificate_service.verify_certificate(db, token)


@router.get("/wallet/me", response_model=SkillWalletPublic)
def get_skill_wallet(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_SELF))],
) -> SkillWalletPublic:
    return certificate_service.wallet(db, auth.user)


@router.get(
    "/programmes/{programme_id}/policy",
    response_model=CertificatePolicyPublic | None,
)
def get_certificate_policy(
    programme_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
) -> CertificatePolicyPublic | None:
    return certificate_service.get_policy(db, auth.user, programme_id)


@router.put(
    "/programmes/{programme_id}/policy",
    response_model=CertificatePolicyPublic,
)
def configure_certificate_policy(
    programme_id: UUID,
    payload: CertificatePolicyUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
) -> CertificatePolicyPublic:
    return certificate_service.upsert_policy(db, request, auth.user, programme_id, payload)


@router.get("/candidates", response_model=list[CertificateCandidatePublic])
def get_certificate_candidates(
    programme_id: Annotated[UUID, Query()],
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
) -> list[CertificateCandidatePublic]:
    return certificate_service.list_candidates(db, auth.user, programme_id)


@router.post("/issue", response_model=CertificateRecordPublic, status_code=201)
def issue_certificate(
    payload: CertificateIssue,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
) -> CertificateRecordPublic:
    return certificate_service.issue_certificate(db, request, auth.user, payload.enrollment_id)


@router.get("", response_model=list[CertificateRecordPublic])
def get_certificates(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
    programme_id: UUID | None = None,
) -> list[CertificateRecordPublic]:
    return certificate_service.list_certificates(db, auth.user, programme_id)


@router.post("/{certificate_id}/revoke", response_model=CertificateRecordPublic)
def revoke_certificate(
    certificate_id: UUID,
    payload: CertificateRevoke,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CERTIFICATES_MANAGE))],
) -> CertificateRecordPublic:
    return certificate_service.revoke_certificate(
        db, request, auth.user, certificate_id, payload.reason
    )


@router.get("/{certificate_id}/download")
def download_certificate(
    certificate_id: UUID,
    db: DbSession,
    auth: Annotated[
        AuthContext,
        Depends(get_current_auth),
    ],
) -> Response:
    certificate = certificate_service.certificate_download(db, auth.user, certificate_id)
    return Response(
        content=certificate.pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f'attachment; filename="{certificate.certificate_number}.pdf"')
        },
    )
