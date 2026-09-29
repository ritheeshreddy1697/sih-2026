from datetime import timedelta
from hmac import compare_digest
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.config import settings
from app.core.permissions import Permission
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    TokenValidationError,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models import (
    AccountStatus,
    ConsentRecord,
    EmployerProfile,
    Institution,
    InstitutionType,
    PasswordResetToken,
    Role,
    RoleCode,
    User,
    UserProfile,
    UserSession,
)
from app.schemas.auth import (
    AccountDeletionComplete,
    AccountDeletionCreate,
    AccountDeletionPublic,
    AuthorizationCheckResponse,
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RegistrationRequest,
    RegistrationResponse,
    UserPublic,
)
from app.services import data_deletion
from app.services.auth import (
    AuthEvent,
    add_audit_log,
    ensure_utc,
    get_client_details,
    get_user_by_email,
    identifier_hash,
    issue_session,
    rotate_session,
    to_user_public,
    utc_now,
)

router = APIRouter()

SELF_REGISTRATION_ROLES = frozenset(
    {
        RoleCode.TRAINEE,
        RoleCode.NOMINATING_INSTITUTION,
        RoleCode.EMPLOYER_RECRUITER,
    }
)
ORGANISATION_ROLE_TYPES = {
    RoleCode.NOMINATING_INSTITUTION: InstitutionType.NOMINATING_INSTITUTION,
    RoleCode.EMPLOYER_RECRUITER: InstitutionType.EMPLOYER,
}


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegistrationRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationResponse:
    if body.role_code not in SELF_REGISTRATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This account type must be created by an administrator",
        )
    if not body.consent_accepted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Consent is required to create an account",
        )
    institution_type = ORGANISATION_ROLE_TYPES.get(body.role_code)
    if institution_type and not body.organisation_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organisation name is required for this account type",
        )

    email = str(body.email).strip().lower()
    if get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email address",
        )

    role = db.scalar(select(Role).where(Role.code == body.role_code))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable",
        )

    institution = None
    if institution_type and body.organisation_name:
        institution = Institution(
            name=body.organisation_name.strip(),
            code=f"PENDING-{uuid4().hex[:12].upper()}",
            institution_type=institution_type,
            is_active=False,
        )
        db.add(institution)

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        status=AccountStatus.PENDING_VERIFICATION,
        institution=institution,
        roles=[role],
        profile=UserProfile(full_name=body.full_name.strip(), phone=body.phone),
    )
    db.add(user)
    db.flush()
    if body.role_code == RoleCode.EMPLOYER_RECRUITER and institution is not None:
        db.add(
            EmployerProfile(
                institution_id=institution.id,
                registered_by_id=user.id,
                industry=(body.industry or "Pending profile completion").strip(),
                website=body.website,
                company_size=body.company_size,
                description=(body.company_description or "Pending profile completion").strip(),
                headquarters=(body.headquarters or "Pending profile completion").strip(),
                registration_number=body.registration_number,
            )
        )
    ip_address, _ = get_client_details(request)
    db.add(
        ConsentRecord(
            user_id=user.id,
            consent_type="privacy_and_terms",
            version="2026-09",
            granted=True,
            ip_address=ip_address,
        )
    )
    add_audit_log(
        db,
        request,
        AuthEvent.REGISTRATION_REQUESTED,
        True,
        user_id=user.id,
        details={"role": body.role_code.value},
    )
    db.commit()
    return RegistrationResponse(
        message="Registration received. An administrator will verify your account.",
        status=AccountStatus.PENDING_VERIFICATION,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    user = get_user_by_email(db, str(body.email))
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(body.password, password_hash)
    if user is None or not password_valid:
        add_audit_log(
            db,
            request,
            AuthEvent.LOGIN_FAILED,
            False,
            details={"login_identifier_hash": identifier_hash(str(body.email))},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != AccountStatus.ACTIVE:
        add_audit_log(
            db,
            request,
            AuthEvent.LOGIN_BLOCKED,
            False,
            user_id=user.id,
            details={"account_status": user.status.value},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is unavailable. Contact your administrator.",
        )

    user.last_login_at = utc_now()
    auth_response, refresh_token = issue_session(db, request, user)
    add_audit_log(db, request, AuthEvent.LOGIN_SUCCEEDED, True, user_id=user.id)
    db.commit()
    set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/refresh", response_model=AuthResponse)
def refresh_tokens(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing",
        )

    try:
        payload = decode_token(refresh_token, "refresh")
    except TokenValidationError as exc:
        add_audit_log(db, request, AuthEvent.TOKEN_REFRESH_FAILED, False)
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    user_session = db.scalar(
        select(UserSession)
        .where(UserSession.id == payload.session_id, UserSession.user_id == payload.subject)
        .options(
            joinedload(UserSession.user).joinedload(User.profile),
            joinedload(UserSession.user).joinedload(User.institution),
            joinedload(UserSession.user).selectinload(User.roles),
        )
    )
    is_valid_session = (
        user_session is not None
        and user_session.revoked_at is None
        and ensure_utc(user_session.expires_at) > utc_now()
        and compare_digest(user_session.refresh_token_hash, hash_token(refresh_token))
    )
    if not is_valid_session or user_session is None:
        add_audit_log(db, request, AuthEvent.TOKEN_REFRESH_FAILED, False)
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is no longer active",
        )

    if user_session.user.status != AccountStatus.ACTIVE:
        user_session.revoked_at = utc_now()
        add_audit_log(
            db,
            request,
            AuthEvent.TOKEN_REFRESH_FAILED,
            False,
            user_id=user_session.user_id,
            details={"account_status": user_session.user.status.value},
        )
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    access_token, new_refresh_token = rotate_session(user_session)
    add_audit_log(
        db,
        request,
        AuthEvent.TOKEN_REFRESHED,
        True,
        user_id=user_session.user_id,
    )
    auth_response = AuthResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=to_user_public(user_session.user),
    )
    db.commit()
    set_refresh_cookie(response, new_refresh_token)
    return auth_response


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    auth.session.revoked_at = utc_now()
    add_audit_log(db, request, AuthEvent.LOGOUT, True, user_id=auth.user.id)
    db.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Signed out successfully")


@router.get("/me", response_model=UserPublic)
def current_user(auth: Annotated[AuthContext, Depends(get_current_auth)]) -> UserPublic:
    return to_user_public(auth.user)


@router.get("/account-deletion", response_model=AccountDeletionPublic | None)
def get_account_deletion(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionPublic | None:
    return data_deletion.current_request(db, auth.user)


@router.post(
    "/account-deletion",
    response_model=AccountDeletionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_account_deletion(
    body: AccountDeletionCreate,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionPublic:
    return data_deletion.request_deletion(db, request, auth.user, auth.session, body)


@router.delete("/account-deletion/{request_id}", response_model=AccountDeletionPublic)
def cancel_account_deletion(
    request_id: UUID,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionPublic:
    return data_deletion.cancel_deletion(db, request, auth.user, request_id)


@router.get("/admin/account-deletions", response_model=list[AccountDeletionPublic])
def get_account_deletion_requests(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[
        AuthContext,
        Depends(require_permission(Permission.PLATFORM_MANAGE)),
    ],
    deletion_status: str | None = None,
) -> list[AccountDeletionPublic]:
    del auth
    if deletion_status not in {None, "pending", "cancelled", "completed"}:
        raise HTTPException(status_code=422, detail="Unsupported deletion request status")
    return data_deletion.list_requests(db, status_filter=deletion_status)


@router.post(
    "/admin/account-deletions/{request_id}/complete",
    response_model=AccountDeletionPublic,
)
def complete_account_deletion(
    request_id: UUID,
    body: AccountDeletionComplete,
    request: Request,
    auth: Annotated[
        AuthContext,
        Depends(require_permission(Permission.PLATFORM_MANAGE)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionPublic:
    return data_deletion.complete_deletion(
        db, request, auth.user, request_id, body.resolution_note
    )


@router.get("/admin-check", response_model=AuthorizationCheckResponse)
def admin_check(
    auth: Annotated[
        AuthContext,
        Depends(require_permission(Permission.PLATFORM_MANAGE)),
    ],
) -> AuthorizationCheckResponse:
    return AuthorizationCheckResponse(authorized=True, role=RoleCode.NCCT_SUPER_ADMIN)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetRequestResponse:
    user = get_user_by_email(db, str(body.email))
    raw_token = None
    if user is not None and user.status == AccountStatus.ACTIVE:
        raw_token = token_urlsafe(48)
        ip_address, _ = get_client_details(request)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=utc_now() + timedelta(minutes=settings.password_reset_expire_minutes),
                requested_ip=ip_address,
            )
        )

    add_audit_log(
        db,
        request,
        AuthEvent.PASSWORD_RESET_REQUESTED,
        True,
        user_id=user.id if user else None,
        details={"login_identifier_hash": identifier_hash(str(body.email))},
    )
    db.commit()
    return PasswordResetRequestResponse(
        message="If the account exists, password reset instructions have been issued.",
        reset_token=raw_token if settings.environment == "development" else None,
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    body: PasswordResetConfirm,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    reset_token = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(body.token))
        .options(
            joinedload(PasswordResetToken.user).joinedload(User.profile),
            joinedload(PasswordResetToken.user).joinedload(User.institution),
            joinedload(PasswordResetToken.user).selectinload(User.roles),
        )
    )
    if (
        reset_token is None
        or reset_token.used_at is not None
        or ensure_utc(reset_token.expires_at) <= utc_now()
    ):
        add_audit_log(db, request, AuthEvent.PASSWORD_RESET_FAILED, False)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or expired",
        )

    now = utc_now()
    reset_token.user.password_hash = hash_password(body.new_password)
    reset_token.user.password_changed_at = now
    reset_token.used_at = now
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == reset_token.user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == reset_token.user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    add_audit_log(
        db,
        request,
        AuthEvent.PASSWORD_RESET_COMPLETED,
        True,
        user_id=reset_token.user_id,
    )
    db.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Password updated. Sign in with your new password.")
