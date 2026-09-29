from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.permissions import permissions_for_roles
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models import AuditLog, User, UserSession
from app.schemas.auth import (
    AuthResponse,
    InstitutionPublic,
    ProfilePublic,
    RolePublic,
    UserPublic,
)


class AuthEvent(StrEnum):
    REGISTRATION_REQUESTED = "auth.registration.requested"
    LOGIN_SUCCEEDED = "auth.login.succeeded"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_BLOCKED = "auth.login.blocked"
    TOKEN_REFRESHED = "auth.token.refreshed"
    TOKEN_REFRESH_FAILED = "auth.token.refresh_failed"
    LOGOUT = "auth.logout"
    PASSWORD_RESET_REQUESTED = "auth.password_reset.requested"
    PASSWORD_RESET_COMPLETED = "auth.password_reset.completed"
    PASSWORD_RESET_FAILED = "auth.password_reset.failed"
    ACCOUNT_DELETION_REQUESTED = "auth.account_deletion.requested"
    ACCOUNT_DELETION_CANCELLED = "auth.account_deletion.cancelled"
    ACCOUNT_DELETION_COMPLETED = "auth.account_deletion.completed"
    ACCOUNT_DELETION_VERIFICATION_FAILED = "auth.account_deletion.verification_failed"


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def identifier_hash(value: str) -> str:
    return hash_token(normalize_email(value))[:16]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.email == normalize_email(email))
        .options(selectinload(User.roles), joinedload(User.profile), joinedload(User.institution))
    )


def get_client_details(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    return ip_address, request.headers.get("user-agent")


def add_audit_log(
    db: Session,
    request: Request,
    event: AuthEvent,
    success: bool,
    *,
    user_id: UUID | None = None,
    details: dict[str, str] | None = None,
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user_id,
            event_type=event.value,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
    )


def to_user_public(user: User) -> UserPublic:
    profile = None
    if user.profile:
        profile = ProfilePublic(
            full_name=user.profile.full_name,
            phone=user.profile.phone,
            designation=user.profile.designation,
        )

    institution = None
    if user.institution:
        institution = InstitutionPublic(
            id=user.institution.id,
            name=user.institution.name,
            code=user.institution.code,
            institution_type=user.institution.institution_type,
        )

    role_codes = {role.code for role in user.roles}
    return UserPublic(
        id=user.id,
        email=user.email,
        status=user.status,
        roles=[RolePublic(code=role.code, display_name=role.display_name) for role in user.roles],
        permissions=sorted(permissions_for_roles(role_codes), key=lambda item: item.value),
        profile=profile,
        institution=institution,
    )


def issue_session(db: Session, request: Request, user: User) -> tuple[AuthResponse, str]:
    session_id = uuid4()
    refresh_token, refresh_expires_at = create_refresh_token(user.id, session_id)
    ip_address, user_agent = get_client_details(request)
    db.add(
        UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=refresh_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    access_token, _ = create_access_token(user.id, session_id)
    response = AuthResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=to_user_public(user),
    )
    return response, refresh_token


def rotate_session(session: UserSession) -> tuple[str, str]:
    refresh_token, refresh_expires_at = create_refresh_token(session.user_id, session.id)
    access_token, _ = create_access_token(session.user_id, session.id)
    session.refresh_token_hash = hash_token(refresh_token)
    session.expires_at = refresh_expires_at
    session.last_used_at = utc_now()
    return access_token, refresh_token
