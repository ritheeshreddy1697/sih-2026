from __future__ import annotations

from datetime import timedelta
from secrets import token_urlsafe
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import (
    AccountDeletionRequest,
    AccountStatus,
    ApplicationDocument,
    AssignmentSubmission,
    BiometricChallenge,
    BiometricEnrollment,
    CareerConversation,
    ConsentRecord,
    CooperativeMembership,
    EducationRecord,
    EmploymentRecord,
    JobApplication,
    ParticipantLogistics,
    PasswordResetToken,
    ProgrammeApplication,
    ProgrammeEnrollment,
    ProgrammeNomination,
    TraineeDocument,
    TraineeEmploymentProfile,
    TraineeProfile,
    User,
    UserSession,
)
from app.schemas.auth import AccountDeletionCreate, AccountDeletionPublic
from app.services.auth import AuthEvent, add_audit_log, utc_now


def _public(item: AccountDeletionRequest) -> AccountDeletionPublic:
    profile = item.user.profile
    return AccountDeletionPublic(
        id=item.id,
        user_id=item.user_id,
        account_email=item.user.email,
        account_name=profile.full_name if profile else item.user.email,
        status=item.status,
        reason=item.reason,
        requested_at=item.requested_at,
        scheduled_for=item.scheduled_for,
        cancelled_at=item.cancelled_at,
        completed_at=item.completed_at,
        resolution_note=item.resolution_note,
    )


def _load(db: Session, request_id: UUID) -> AccountDeletionRequest:
    item = db.scalar(
        select(AccountDeletionRequest)
        .where(AccountDeletionRequest.id == request_id)
        .options(joinedload(AccountDeletionRequest.user).joinedload(User.profile))
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    return item


def current_request(db: Session, user: User) -> AccountDeletionPublic | None:
    item = db.scalar(
        select(AccountDeletionRequest)
        .where(AccountDeletionRequest.user_id == user.id)
        .order_by(AccountDeletionRequest.requested_at.desc())
        .options(joinedload(AccountDeletionRequest.user).joinedload(User.profile))
    )
    return _public(item) if item else None


def request_deletion(
    db: Session,
    request: Request,
    user: User,
    session: UserSession,
    payload: AccountDeletionCreate,
) -> AccountDeletionPublic:
    if not verify_password(payload.current_password, user.password_hash):
        add_audit_log(
            db,
            request,
            AuthEvent.ACCOUNT_DELETION_VERIFICATION_FAILED,
            False,
            user_id=user.id,
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    existing = db.scalar(
        select(AccountDeletionRequest).where(
            AccountDeletionRequest.user_id == user.id,
            AccountDeletionRequest.status == "pending",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="An account deletion request is already pending"
        )
    now = utc_now()
    item = AccountDeletionRequest(
        user_id=user.id,
        reason=payload.reason.strip() if payload.reason else None,
        scheduled_for=now + timedelta(days=settings.account_deletion_cooling_days),
    )
    db.add(item)
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.id != session.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    add_audit_log(db, request, AuthEvent.ACCOUNT_DELETION_REQUESTED, True, user_id=user.id)
    db.commit()
    return _public(_load(db, item.id))


def cancel_deletion(
    db: Session, request: Request, user: User, request_id: UUID
) -> AccountDeletionPublic:
    item = _load(db, request_id)
    if item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if item.status != "pending":
        raise HTTPException(
            status_code=409, detail="Only pending deletion requests can be cancelled"
        )
    item.status = "cancelled"
    item.cancelled_at = utc_now()
    add_audit_log(db, request, AuthEvent.ACCOUNT_DELETION_CANCELLED, True, user_id=user.id)
    db.commit()
    return _public(_load(db, item.id))


def list_requests(db: Session, *, status_filter: str | None) -> list[AccountDeletionPublic]:
    statement = select(AccountDeletionRequest).options(
        joinedload(AccountDeletionRequest.user).joinedload(User.profile)
    )
    if status_filter:
        statement = statement.where(AccountDeletionRequest.status == status_filter)
    items = db.scalars(statement.order_by(AccountDeletionRequest.requested_at.desc())).unique()
    return [_public(item) for item in items]


def complete_deletion(
    db: Session,
    request: Request,
    actor: User,
    request_id: UUID,
    resolution_note: str,
) -> AccountDeletionPublic:
    item = _load(db, request_id)
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Deletion request is not pending")
    user = item.user
    if user.id == actor.id:
        raise HTTPException(status_code=409, detail="Administrators cannot erase their own account")

    old_email = user.email
    trainee = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == user.id))
    if trainee is not None:
        db.execute(delete(EducationRecord).where(EducationRecord.profile_id == trainee.id))
        db.execute(delete(EmploymentRecord).where(EmploymentRecord.profile_id == trainee.id))
        db.execute(
            delete(CooperativeMembership).where(CooperativeMembership.profile_id == trainee.id)
        )
        db.execute(delete(TraineeDocument).where(TraineeDocument.profile_id == trainee.id))
        trainee.date_of_birth = None
        trainee.gender = None
        trainee.alternate_email = None
        trainee.address_line = None
        trainee.city = None
        trainee.state = None
        trainee.postal_code = None
        trainee.preferred_language = None
        trainee.preferred_location = None
        trainee.career_interests = None
        trainee.skills = []
        trainee.placement_visibility_consent = False
        trainee.communication_consent = False
        trainee.data_sharing_consent = False
        trainee.completion_percent = 0
        trainee.qr_identity_version += 1

    enrollment_ids = list(
        db.scalars(select(ProgrammeEnrollment.id).where(ProgrammeEnrollment.trainee_id == user.id))
    )
    if enrollment_ids:
        db.execute(
            delete(AssignmentSubmission).where(AssignmentSubmission.enrollment_id.in_(enrollment_ids))
        )
        db.execute(
            update(ParticipantLogistics)
            .where(ParticipantLogistics.enrollment_id.in_(enrollment_ids))
            .values(
                dietary_notes=None,
                arrival_details=None,
                departure_details=None,
                emergency_contact_name="Deleted account",
                emergency_contact_phone="Not retained",
                emergency_contact_relationship="Not retained",
            )
        )

    db.execute(delete(ApplicationDocument).where(ApplicationDocument.uploaded_by_id == user.id))
    db.execute(delete(CareerConversation).where(CareerConversation.user_id == user.id))
    db.execute(delete(BiometricEnrollment).where(BiometricEnrollment.trainee_id == user.id))
    db.execute(
        delete(BiometricChallenge).where(
            BiometricChallenge.trainee_id == user.id,
            BiometricChallenge.used_at.is_(None),
        )
    )
    db.execute(delete(ConsentRecord).where(ConsentRecord.user_id == user.id))
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.execute(
        update(ProgrammeApplication)
        .where(ProgrammeApplication.trainee_id == user.id)
        .values(statement=None)
    )
    db.execute(
        update(ProgrammeNomination)
        .where(ProgrammeNomination.candidate_email == old_email)
        .values(
            candidate_full_name="Deleted account",
            candidate_email=f"deleted-{user.id}@example.invalid",
            candidate_phone=None,
            member_identifier=None,
        )
    )
    db.execute(
        update(JobApplication)
        .where(JobApplication.trainee_id == user.id)
        .values(cover_note=None, interview_details=None)
    )
    db.execute(
        update(TraineeEmploymentProfile)
        .where(TraineeEmploymentProfile.trainee_id == user.id)
        .values(
            headline=None,
            professional_summary=None,
            preferred_roles=[],
            preferred_locations=[],
            open_to_work=False,
            resume_filename=None,
            resume_content_type=None,
            resume_size_bytes=None,
            resume_content=None,
            resume_uploaded_at=None,
        )
    )

    if user.profile:
        user.profile.full_name = "Deleted account"
        user.profile.phone = None
        user.profile.designation = None
    user.email = f"deleted-{user.id}@example.invalid"
    user.password_hash = hash_password(token_urlsafe(48))
    user.status = AccountStatus.SUSPENDED
    user.institution_id = None
    user.email_verified_at = None
    user.roles.clear()

    item.status = "completed"
    item.completed_at = utc_now()
    item.completed_by_id = actor.id
    item.resolution_note = resolution_note.strip()
    add_audit_log(
        db,
        request,
        AuthEvent.ACCOUNT_DELETION_COMPLETED,
        True,
        user_id=actor.id,
        details={"target_user_id": str(user.id), "deletion_request_id": str(item.id)},
    )
    db.commit()
    return _public(_load(db, item.id))
