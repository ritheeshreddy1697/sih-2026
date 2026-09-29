from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPublic,
    NotificationSendRequest,
    NotificationSendResponse,
)
from app.services import notifications as notification_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


@router.get("", response_model=NotificationListResponse)
def get_notifications(db: DbSession, auth: CurrentAuth) -> NotificationListResponse:
    return notification_service.list_notifications(db, auth.user)


@router.post("", response_model=NotificationSendResponse, status_code=201)
def send_notification(
    payload: NotificationSendRequest,
    request: Request,
    db: DbSession,
    auth: Annotated[
        AuthContext, Depends(require_permission(Permission.NOTIFICATIONS_SEND))
    ],
) -> NotificationSendResponse:
    return notification_service.send_notification(db, request, auth.user, payload)


@router.patch("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: UUID, db: DbSession, auth: CurrentAuth
) -> NotificationPublic:
    return notification_service.mark_read(db, auth.user, notification_id)
