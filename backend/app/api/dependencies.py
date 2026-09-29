from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import Permission, has_permission
from app.core.security import TokenValidationError, decode_token
from app.db.session import get_db
from app.models import AccountStatus, AuditLog, RoleCode, User, UserSession
from app.services.auth import get_client_details

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    session: UserSession


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials, "access")
    except TokenValidationError as exc:
        raise _unauthorized("Invalid or expired access token") from exc

    user_session = db.scalar(
        select(UserSession)
        .where(UserSession.id == payload.session_id, UserSession.user_id == payload.subject)
        .options(
            joinedload(UserSession.user).joinedload(User.profile),
            joinedload(UserSession.user).joinedload(User.institution),
            joinedload(UserSession.user).selectinload(User.roles),
        )
    )
    now = datetime.now(UTC)
    if (
        user_session is None
        or user_session.revoked_at is not None
        or _as_utc(user_session.expires_at) <= now
    ):
        raise _unauthorized("Session is no longer active")

    if user_session.user.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    return AuthContext(user=user_session.user, session=user_session)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def require_roles(*allowed_roles: RoleCode) -> Callable[..., AuthContext]:
    def check_roles(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        auth: Annotated[AuthContext, Depends(get_current_auth)],
    ) -> AuthContext:
        user_roles = {role.code for role in auth.user.roles}
        if user_roles.isdisjoint(allowed_roles):
            _audit_denial(
                db,
                request,
                auth.user,
                "roles",
                ",".join(role.value for role in allowed_roles),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not allow this action",
            )
        return auth

    return check_roles


def require_permission(permission: Permission) -> Callable[..., AuthContext]:
    def check_permission(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        auth: Annotated[AuthContext, Depends(get_current_auth)],
    ) -> AuthContext:
        user_roles = {role.code for role in auth.user.roles}
        if not has_permission(user_roles, permission):
            _audit_denial(db, request, auth.user, "permission", permission.value)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permission",
            )
        return auth

    return check_permission


def _audit_denial(
    db: Session, request: Request, user: User, requirement_type: str, requirement: str
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id,
            event_type="authorization.denied",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "requirement_type": requirement_type,
                "requirement": requirement,
                "method": request.method,
                "path": request.url.path,
            },
        )
    )
    db.commit()
