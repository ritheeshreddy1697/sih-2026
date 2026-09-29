from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import Permission, has_permission
from app.models import (
    AccountStatus,
    Institution,
    Notification,
    NotificationReceipt,
    Role,
    RoleCode,
    User,
)
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPublic,
    NotificationSendRequest,
    NotificationSendResponse,
)
from app.services import profiles as profile_service


def user_has(user: User, permission: Permission) -> bool:
    return has_permission({role.code for role in user.roles}, permission)


def notification_public(receipt: NotificationReceipt) -> NotificationPublic:
    notification = receipt.notification
    sender = notification.sender
    return NotificationPublic(
        id=notification.id,
        title=notification.title,
        description=notification.description,
        sender_name=sender.profile.full_name if sender.profile else sender.email,
        created_at=notification.created_at,
        unread=receipt.read_at is None,
    )


def list_notifications(db: Session, user: User) -> NotificationListResponse:
    receipts = list(
        db.scalars(
            select(NotificationReceipt)
            .where(NotificationReceipt.recipient_id == user.id)
            .join(Notification, Notification.id == NotificationReceipt.notification_id)
            .options(
                joinedload(NotificationReceipt.notification)
                .joinedload(Notification.sender)
                .joinedload(User.profile)
            )
            .order_by(Notification.created_at.desc())
            .limit(50)
        ).unique()
    )
    unread_count = int(
        db.scalar(
            select(func.count(NotificationReceipt.id)).where(
                NotificationReceipt.recipient_id == user.id,
                NotificationReceipt.read_at.is_(None),
            )
        )
        or 0
    )
    return NotificationListResponse(
        items=[notification_public(receipt) for receipt in receipts],
        unread_count=unread_count,
    )


def mark_read(db: Session, user: User, notification_id: UUID) -> NotificationPublic:
    receipt = db.scalar(
        select(NotificationReceipt)
        .where(
            NotificationReceipt.notification_id == notification_id,
            NotificationReceipt.recipient_id == user.id,
        )
        .options(
            joinedload(NotificationReceipt.notification)
            .joinedload(Notification.sender)
            .joinedload(User.profile)
        )
    )
    if receipt is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if receipt.read_at is None:
        receipt.read_at = datetime.now(UTC)
        db.commit()
    return notification_public(receipt)


def send_notification(
    db: Session,
    request: Request,
    sender: User,
    payload: NotificationSendRequest,
) -> NotificationSendResponse:
    target_ids = set(payload.target_ids)
    title = payload.title.strip()
    description = payload.description.strip()
    if len(title) < 3 or len(description) < 3:
        raise HTTPException(status_code=422, detail="Title and message cannot be blank")

    if user_has(sender, Permission.PLATFORM_MANAGE):
        if payload.target_type != "institutions":
            raise HTTPException(
                status_code=403,
                detail="NCCT administrators send notifications to institutions",
            )
        institutions = set(
            db.scalars(
                select(Institution.id).where(
                    Institution.id.in_(target_ids), Institution.is_active.is_(True)
                )
            )
        )
        if institutions != target_ids:
            raise HTTPException(status_code=403, detail="One or more institutions are unavailable")
        recipients = list(
            db.scalars(
                select(User)
                .join(User.roles)
                .where(
                    User.institution_id.in_(target_ids),
                    User.status == AccountStatus.ACTIVE,
                    Role.code == RoleCode.INSTITUTE_ADMIN,
                )
            ).unique()
        )
    else:
        target_role = {
            "trainees": RoleCode.TRAINEE,
            "trainers": RoleCode.TRAINER,
        }.get(payload.target_type)
        if target_role is None:
            raise HTTPException(
                status_code=403,
                detail="Institute administrators send notifications to trainers or trainees",
            )
        allowed_institutions = profile_service.scoped_institution_ids(db, sender) or set()
        recipients = list(
            db.scalars(
                select(User)
                .join(User.roles)
                .where(
                    User.id.in_(target_ids),
                    User.institution_id.in_(allowed_institutions),
                    User.status == AccountStatus.ACTIVE,
                    Role.code == target_role,
                )
            ).unique()
        )
        if {recipient.id for recipient in recipients} != target_ids:
            raise HTTPException(
                status_code=403,
                detail="One or more recipients are outside your institution scope",
            )

    if not recipients:
        raise HTTPException(status_code=422, detail="No active recipients were found")

    notification = Notification(sender_id=sender.id, title=title, description=description)
    db.add(notification)
    db.flush()
    db.add_all(
        NotificationReceipt(notification_id=notification.id, recipient_id=recipient.id)
        for recipient in recipients
    )
    profile_service.add_profile_audit(
        db,
        request,
        sender,
        "notification.sent",
        target_type=payload.target_type,
        target_count=len(target_ids),
        recipient_count=len(recipients),
    )
    db.commit()
    return NotificationSendResponse(id=notification.id, sent_count=len(recipients))
