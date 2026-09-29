from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.permissions import Permission, has_permission
from app.core.uploads import DOCUMENT_TYPES, read_validated_upload
from app.models import (
    ApplicationDocument,
    ApplicationStatus,
    AuditLog,
    BatchTrainerAssignment,
    DocumentType,
    EligibilityType,
    Institution,
    InstitutionType,
    NominationSource,
    Programme,
    ProgrammeApplication,
    ProgrammeBatch,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeNomination,
    ProgrammeStatus,
    Role,
    RoleCode,
    User,
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
    ProgrammeDetail,
    ProgrammeNominationCreate,
    ProgrammeNominationPublic,
    ProgrammePublic,
    ProgrammeUpdate,
    ReviewUpdate,
    TrainerBrief,
)
from app.services.auth import get_client_details, normalize_email

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_BULK_ROWS = 500
ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}
REVIEW_STATUSES = {
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WAITLISTED,
}
NOMINATION_TYPES = {
    EligibilityType.PACS,
    EligibilityType.SHG,
    EligibilityType.COOPERATIVE_INSTITUTION,
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def role_codes(user: User) -> set[RoleCode]:
    return {role.code for role in user.roles}


def user_has(user: User, permission: Permission) -> bool:
    return has_permission(role_codes(user), permission)


def add_programme_audit(
    db: Session,
    request: Request,
    user: User,
    event_type: str,
    details: dict[str, Any],
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id,
            event_type=event_type,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    )


def programme_load_options() -> tuple[Any, ...]:
    return (
        joinedload(Programme.institution),
        selectinload(Programme.batches)
        .selectinload(ProgrammeBatch.trainer_assignments)
        .joinedload(BatchTrainerAssignment.trainer)
        .joinedload(User.profile),
    )


def load_programme(db: Session, programme_id: UUID) -> Programme:
    programme = db.scalar(
        select(Programme)
        .where(Programme.id == programme_id)
        .options(*programme_load_options())
        .execution_options(populate_existing=True)
    )
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    return programme


def ensure_visible(user: User, programme: Programme) -> None:
    if user_has(user, Permission.PLATFORM_MANAGE):
        return
    if user_has(user, Permission.PROGRAMMES_MANAGE):
        if user.institution_id == programme.institution_id:
            return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    if programme.status != ProgrammeStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    eligible_types = set(programme.eligible_applicant_types)
    if user_has(user, Permission.APPLICATIONS_APPLY):
        if EligibilityType.INDIVIDUAL.value not in eligible_types:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    elif user_has(user, Permission.NOMINATIONS_CREATE):
        if eligible_types.isdisjoint({item.value for item in NOMINATION_TYPES}):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")


def ensure_manager(user: User, programme: Programme) -> None:
    if user_has(user, Permission.PLATFORM_MANAGE):
        return
    if not user_has(user, Permission.PROGRAMMES_MANAGE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if user.institution_id != programme.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can manage only your institution's programmes",
        )


def ensure_reviewer(user: User, programme: Programme) -> None:
    if user_has(user, Permission.PLATFORM_MANAGE):
        return
    if not user_has(user, Permission.APPLICATIONS_REVIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if user.institution_id != programme.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can review only your institution's programme submissions",
        )


def approved_count(db: Session, programme_id: UUID) -> int:
    applications = db.scalar(
        select(func.count(ProgrammeApplication.id)).where(
            ProgrammeApplication.programme_id == programme_id,
            ProgrammeApplication.status == ApplicationStatus.APPROVED,
        )
    )
    nominations = db.scalar(
        select(func.count(ProgrammeNomination.id)).where(
            ProgrammeNomination.programme_id == programme_id,
            ProgrammeNomination.status == ApplicationStatus.APPROVED,
        )
    )
    return int(applications or 0) + int(nominations or 0)


def document_public(document: ApplicationDocument) -> DocumentPublic:
    return DocumentPublic(
        id=document.id,
        document_type=document.document_type,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        uploaded_at=document.uploaded_at,
    )


def batch_public(batch: ProgrammeBatch) -> ProgrammeBatchPublic:
    trainers = []
    for assignment in sorted(batch.trainer_assignments, key=lambda item: item.assigned_at):
        trainer = assignment.trainer
        trainers.append(
            BatchTrainerPublic(
                id=assignment.id,
                trainer=TrainerBrief(
                    id=trainer.id,
                    full_name=trainer.profile.full_name if trainer.profile else trainer.email,
                    email=trainer.email,
                ),
                assigned_at=assignment.assigned_at,
            )
        )
    return ProgrammeBatchPublic(
        id=batch.id,
        name=batch.name,
        code=batch.code,
        capacity=batch.capacity,
        start_date=batch.start_date,
        end_date=batch.end_date,
        location=batch.location,
        trainers=trainers,
    )


def programme_public(db: Session, programme: Programme, user: User) -> ProgrammePublic:
    filled = approved_count(db, programme.id)
    existing = db.scalar(
        select(ProgrammeApplication.id).where(
            ProgrammeApplication.programme_id == programme.id,
            ProgrammeApplication.trainee_id == user.id,
        )
    )
    eligible = EligibilityType.INDIVIDUAL.value in programme.eligible_applicant_types
    deadline_open = as_utc(programme.application_deadline) >= utc_now()
    return ProgrammePublic(
        id=programme.id,
        institution=InstitutionBrief(
            id=programme.institution.id,
            name=programme.institution.name,
            code=programme.institution.code,
        ),
        title=programme.title,
        code=programme.code,
        summary=programme.summary,
        mode=programme.mode,
        status=programme.status,
        eligible_applicant_types=[
            EligibilityType(value) for value in programme.eligible_applicant_types
        ],
        capacity=programme.capacity,
        available_capacity=max(programme.capacity - filled, 0),
        location=programme.location,
        language=programme.language,
        duration_days=programme.duration_days,
        application_deadline=programme.application_deadline,
        start_date=programme.start_date,
        end_date=programme.end_date,
        can_apply=(
            user_has(user, Permission.APPLICATIONS_APPLY)
            and programme.status == ProgrammeStatus.PUBLISHED
            and eligible
            and deadline_open
            and filled < programme.capacity
            and existing is None
        ),
        has_applied=existing is not None,
    )


def programme_detail(db: Session, programme: Programme, user: User) -> ProgrammeDetail:
    base = programme_public(db, programme, user)
    application_total = db.scalar(
        select(func.count(ProgrammeApplication.id)).where(
            ProgrammeApplication.programme_id == programme.id
        )
    )
    nomination_total = db.scalar(
        select(func.count(ProgrammeNomination.id)).where(
            ProgrammeNomination.programme_id == programme.id
        )
    )
    return ProgrammeDetail(
        **base.model_dump(),
        description=programme.description,
        eligibility_criteria=programme.eligibility_criteria,
        rejection_reason=programme.rejection_reason,
        batches=[
            batch_public(batch)
            for batch in sorted(programme.batches, key=lambda item: item.start_date)
        ],
        application_count=int(application_total or 0),
        nomination_count=int(nomination_total or 0),
        approved_count=approved_count(db, programme.id),
    )


def list_programmes(
    db: Session,
    user: User,
    *,
    query_text: str | None = None,
    programme_status: ProgrammeStatus | None = None,
    mode: ProgrammeMode | None = None,
    language: str | None = None,
    institution_id: UUID | None = None,
) -> list[ProgrammePublic]:
    statement = select(Programme).options(*programme_load_options()).order_by(Programme.start_date)
    if user_has(user, Permission.PLATFORM_MANAGE):
        if programme_status:
            statement = statement.where(Programme.status == programme_status)
    elif user_has(user, Permission.PROGRAMMES_MANAGE):
        statement = statement.where(Programme.institution_id == user.institution_id)
        if programme_status:
            statement = statement.where(Programme.status == programme_status)
    else:
        statement = statement.where(Programme.status == ProgrammeStatus.PUBLISHED)

    if query_text:
        pattern = f"%{query_text.strip()}%"
        statement = statement.where(
            or_(Programme.title.ilike(pattern), Programme.code.ilike(pattern))
        )
    if mode:
        statement = statement.where(Programme.mode == mode)
    if language:
        statement = statement.where(Programme.language.ilike(language.strip()))
    if institution_id:
        statement = statement.where(Programme.institution_id == institution_id)

    programmes = list(db.scalars(statement).unique().all())
    if user_has(user, Permission.APPLICATIONS_APPLY) and not user_has(
        user, Permission.PROGRAMMES_MANAGE
    ):
        programmes = [
            item
            for item in programmes
            if EligibilityType.INDIVIDUAL.value in item.eligible_applicant_types
        ]
    elif user_has(user, Permission.NOMINATIONS_CREATE):
        nomination_values = {item.value for item in NOMINATION_TYPES}
        programmes = [
            item
            for item in programmes
            if not set(item.eligible_applicant_types).isdisjoint(nomination_values)
        ]
    return [programme_public(db, programme, user) for programme in programmes]


def validate_programme_values(values: dict[str, Any]) -> None:
    if values["end_date"] < values["start_date"]:
        raise HTTPException(status_code=422, detail="End date must be on or after start date")
    if as_utc(values["application_deadline"]).date() >= values["start_date"]:
        raise HTTPException(
            status_code=422, detail="Application deadline must be before start date"
        )
    if values["mode"] in {ProgrammeMode.OFFLINE, ProgrammeMode.HYBRID} and not values.get(
        "location"
    ):
        raise HTTPException(status_code=422, detail="Location is required for this delivery mode")
    if not values["eligible_applicant_types"]:
        raise HTTPException(status_code=422, detail="Select at least one eligible applicant type")


def create_programme(
    db: Session, request: Request, user: User, payload: ProgrammeCreate
) -> Programme:
    institution_id = user.institution_id
    if user_has(user, Permission.PLATFORM_MANAGE) and payload.institution_id:
        institution_id = payload.institution_id
    if institution_id is None:
        raise HTTPException(status_code=422, detail="A training institution is required")
    institution = db.get(Institution, institution_id)
    if institution is None or institution.institution_type not in {
        InstitutionType.TRAINING_INSTITUTE,
        InstitutionType.VAMNICOM,
        InstitutionType.RICM,
        InstitutionType.ICM,
    }:
        raise HTTPException(
            status_code=422, detail="Programme owner must be a training institution"
        )
    if db.scalar(select(Programme.id).where(Programme.code == payload.code)):
        raise HTTPException(status_code=409, detail="Programme code already exists")

    values = payload.model_dump(exclude={"institution_id"})
    values["eligible_applicant_types"] = [item.value for item in payload.eligible_applicant_types]
    validate_programme_values(values)
    programme = Programme(
        **values,
        institution_id=institution_id,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(programme)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.created",
        {"programme_id": str(programme.id), "code": programme.code},
    )
    db.commit()
    return load_programme(db, programme.id)


def update_programme(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    payload: ProgrammeUpdate,
) -> Programme:
    ensure_manager(user, programme)
    if programme.status not in {ProgrammeStatus.DRAFT, ProgrammeStatus.REJECTED}:
        raise HTTPException(
            status_code=409, detail="Only draft or rejected programmes can be edited"
        )
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes and changes["code"] != programme.code:
        if db.scalar(select(Programme.id).where(Programme.code == changes["code"])):
            raise HTTPException(status_code=409, detail="Programme code already exists")
    if "eligible_applicant_types" in changes:
        changes["eligible_applicant_types"] = [
            item.value for item in changes["eligible_applicant_types"]
        ]
    merged = {
        "end_date": changes.get("end_date", programme.end_date),
        "start_date": changes.get("start_date", programme.start_date),
        "application_deadline": changes.get("application_deadline", programme.application_deadline),
        "mode": changes.get("mode", programme.mode),
        "location": changes.get("location", programme.location),
        "eligible_applicant_types": changes.get(
            "eligible_applicant_types", programme.eligible_applicant_types
        ),
    }
    validate_programme_values(merged)
    for field, value in changes.items():
        setattr(programme, field, value)
    programme.updated_by_id = user.id
    programme.rejection_reason = None
    add_programme_audit(
        db,
        request,
        user,
        "programme.updated",
        {"programme_id": str(programme.id), "fields": sorted(changes)},
    )
    db.commit()
    return load_programme(db, programme.id)


def add_batch(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    payload: ProgrammeBatchCreate,
) -> ProgrammeBatch:
    ensure_manager(user, programme)
    if programme.status not in {ProgrammeStatus.DRAFT, ProgrammeStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Batches can be added only before approval")
    if payload.start_date < programme.start_date or payload.end_date > programme.end_date:
        raise HTTPException(status_code=422, detail="Batch dates must fall within programme dates")
    used_capacity = sum(batch.capacity for batch in programme.batches)
    if used_capacity + payload.capacity > programme.capacity:
        raise HTTPException(status_code=409, detail="Batch capacity exceeds programme capacity")
    if any(batch.code.casefold() == payload.code.casefold() for batch in programme.batches):
        raise HTTPException(status_code=409, detail="Batch code already exists in this programme")
    batch = ProgrammeBatch(
        programme_id=programme.id,
        name=payload.name,
        code=payload.code.upper(),
        capacity=payload.capacity,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location=payload.location,
    )
    db.add(batch)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.batch_created",
        {"programme_id": str(programme.id), "batch_id": str(batch.id)},
    )
    db.commit()
    db.refresh(batch)
    return batch


def assign_trainer(
    db: Session,
    request: Request,
    user: User,
    batch: ProgrammeBatch,
    trainer_id: UUID,
) -> BatchTrainerAssignment:
    programme = load_programme(db, batch.programme_id)
    ensure_manager(user, programme)
    trainer = db.scalar(
        select(User)
        .where(User.id == trainer_id)
        .options(selectinload(User.roles), joinedload(User.profile))
    )
    if trainer is None or RoleCode.TRAINER not in role_codes(trainer):
        raise HTTPException(status_code=422, detail="Selected user is not a trainer")
    if trainer.institution_id != programme.institution_id:
        raise HTTPException(
            status_code=422, detail="Trainer must belong to the programme institution"
        )
    existing = db.scalar(
        select(BatchTrainerAssignment).where(
            BatchTrainerAssignment.batch_id == batch.id,
            BatchTrainerAssignment.trainer_id == trainer.id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Trainer is already assigned to this batch")
    assignment = BatchTrainerAssignment(
        batch_id=batch.id,
        trainer_id=trainer.id,
        assigned_by_id=user.id,
    )
    db.add(assignment)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.trainer_assigned",
        {
            "programme_id": str(programme.id),
            "batch_id": str(batch.id),
            "trainer_id": str(trainer.id),
        },
    )
    db.commit()
    return assignment


def transition_programme(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    target: ProgrammeStatus,
    reason: str | None = None,
) -> Programme:
    now = utc_now()
    if target == ProgrammeStatus.PENDING_APPROVAL:
        ensure_manager(user, programme)
        if programme.status not in {ProgrammeStatus.DRAFT, ProgrammeStatus.REJECTED}:
            raise HTTPException(
                status_code=409, detail="Programme cannot be submitted from this state"
            )
        if not programme.batches:
            raise HTTPException(status_code=409, detail="Add at least one batch before submission")
    elif target in {ProgrammeStatus.APPROVED, ProgrammeStatus.REJECTED}:
        if not user_has(user, Permission.PROGRAMMES_APPROVE):
            raise HTTPException(status_code=403, detail="Only NCCT can approve programmes")
        if programme.status != ProgrammeStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=409, detail="Only pending programmes can be reviewed")
        if target == ProgrammeStatus.REJECTED and not reason:
            raise HTTPException(status_code=422, detail="A rejection reason is required")
        programme.approved_by_id = user.id
        programme.approved_at = now if target == ProgrammeStatus.APPROVED else None
        programme.rejection_reason = reason if target == ProgrammeStatus.REJECTED else None
    elif target == ProgrammeStatus.PUBLISHED:
        ensure_manager(user, programme)
        if programme.status != ProgrammeStatus.APPROVED:
            raise HTTPException(status_code=409, detail="Only approved programmes can be published")
        if as_utc(programme.application_deadline) < now:
            raise HTTPException(status_code=409, detail="Application deadline has already passed")
        programme.published_at = now
    elif target == ProgrammeStatus.ARCHIVED:
        ensure_manager(user, programme)
        if programme.status == ProgrammeStatus.ARCHIVED:
            raise HTTPException(status_code=409, detail="Programme is already archived")
        programme.archived_at = now
    else:
        raise HTTPException(status_code=422, detail="Unsupported programme transition")

    previous = programme.status
    programme.status = target
    programme.updated_by_id = user.id
    add_programme_audit(
        db,
        request,
        user,
        f"programme.{target.value}",
        {"programme_id": str(programme.id), "from": previous.value, "reason": reason},
    )
    db.commit()
    return load_programme(db, programme.id)


def application_public(application: ProgrammeApplication) -> ProgrammeApplicationPublic:
    trainee = application.trainee
    return ProgrammeApplicationPublic(
        id=application.id,
        programme_id=application.programme_id,
        programme_title=application.programme.title,
        programme_code=application.programme.code,
        trainee_id=trainee.id,
        trainee_name=trainee.profile.full_name if trainee.profile else trainee.email,
        trainee_email=trainee.email,
        status=application.status,
        statement=application.statement,
        review_notes=application.review_notes,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        documents=[document_public(item) for item in application.documents],
    )


def application_options() -> tuple[Any, ...]:
    return (
        joinedload(ProgrammeApplication.programme).joinedload(Programme.institution),
        joinedload(ProgrammeApplication.trainee).joinedload(User.profile),
        selectinload(ProgrammeApplication.documents),
    )


def create_application(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    payload: ProgrammeApplicationCreate,
) -> ProgrammeApplication:
    if programme.status != ProgrammeStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Programme is not open for applications")
    if EligibilityType.INDIVIDUAL.value not in programme.eligible_applicant_types:
        raise HTTPException(status_code=403, detail="This programme does not accept individuals")
    if as_utc(programme.application_deadline) < utc_now():
        raise HTTPException(status_code=409, detail="Application deadline has passed")
    if approved_count(db, programme.id) >= programme.capacity:
        raise HTTPException(status_code=409, detail="Programme capacity has been reached")
    if db.scalar(
        select(ProgrammeApplication.id).where(
            ProgrammeApplication.programme_id == programme.id,
            ProgrammeApplication.trainee_id == user.id,
        )
    ):
        raise HTTPException(status_code=409, detail="You have already applied to this programme")
    if db.scalar(
        select(ProgrammeNomination.id).where(
            ProgrammeNomination.programme_id == programme.id,
            ProgrammeNomination.candidate_email == normalize_email(user.email),
        )
    ):
        raise HTTPException(status_code=409, detail="You are already nominated for this programme")
    application = ProgrammeApplication(
        programme_id=programme.id,
        trainee_id=user.id,
        statement=payload.statement,
    )
    db.add(application)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.application_submitted",
        {"programme_id": str(programme.id), "application_id": str(application.id)},
    )
    db.commit()
    return load_application(db, application.id)


def load_application(db: Session, application_id: UUID) -> ProgrammeApplication:
    application = db.scalar(
        select(ProgrammeApplication)
        .where(ProgrammeApplication.id == application_id)
        .options(*application_options())
        .execution_options(populate_existing=True)
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def list_applications(
    db: Session, user: User, programme_id: UUID | None = None
) -> list[ProgrammeApplicationPublic]:
    statement = (
        select(ProgrammeApplication)
        .options(*application_options())
        .order_by(ProgrammeApplication.submitted_at.desc())
    )
    if user_has(user, Permission.APPLICATIONS_REVIEW):
        if programme_id:
            programme = load_programme(db, programme_id)
            ensure_reviewer(user, programme)
            statement = statement.where(ProgrammeApplication.programme_id == programme_id)
        elif not user_has(user, Permission.PLATFORM_MANAGE):
            statement = statement.join(Programme).where(
                Programme.institution_id == user.institution_id
            )
    else:
        statement = statement.where(ProgrammeApplication.trainee_id == user.id)
    return [application_public(item) for item in db.scalars(statement).unique().all()]


def review_application(
    db: Session,
    request: Request,
    user: User,
    application: ProgrammeApplication,
    payload: ReviewUpdate,
) -> ProgrammeApplication:
    ensure_reviewer(user, application.programme)
    if payload.status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported review status")
    if (
        payload.status == ApplicationStatus.APPROVED
        and application.status != ApplicationStatus.APPROVED
    ):
        locked_programme = db.scalar(
            select(Programme).where(Programme.id == application.programme_id).with_for_update()
        )
        if locked_programme is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        if approved_count(db, application.programme_id) >= locked_programme.capacity:
            raise HTTPException(status_code=409, detail="Programme capacity has been reached")
    application.status = payload.status
    application.review_notes = payload.review_notes
    application.reviewer_id = user.id
    application.reviewed_at = utc_now()
    if payload.status == ApplicationStatus.APPROVED:
        enrollment = db.scalar(
            select(ProgrammeEnrollment).where(
                ProgrammeEnrollment.trainee_id == application.trainee_id,
                ProgrammeEnrollment.programme_id == application.programme_id,
            )
        )
        if enrollment is None:
            first_batch_id = db.scalar(
                select(ProgrammeBatch.id)
                .where(ProgrammeBatch.programme_id == application.programme_id)
                .order_by(ProgrammeBatch.start_date, ProgrammeBatch.created_at)
                .limit(1)
            )
            db.add(
                ProgrammeEnrollment(
                    trainee_id=application.trainee_id,
                    programme_id=application.programme_id,
                    batch_id=first_batch_id,
                )
            )
    add_programme_audit(
        db,
        request,
        user,
        "programme.application_reviewed",
        {
            "programme_id": str(application.programme_id),
            "application_id": str(application.id),
            "status": payload.status.value,
        },
    )
    db.commit()
    return load_application(db, application.id)


def nomination_public(nomination: ProgrammeNomination) -> ProgrammeNominationPublic:
    institution = nomination.nominating_institution
    return ProgrammeNominationPublic(
        id=nomination.id,
        programme_id=nomination.programme_id,
        programme_title=nomination.programme.title,
        programme_code=nomination.programme.code,
        nominating_institution=InstitutionBrief(
            id=institution.id,
            name=institution.name,
            code=institution.code,
        ),
        nomination_type=nomination.nomination_type,
        source=nomination.source,
        candidate_full_name=nomination.candidate_full_name,
        candidate_email=nomination.candidate_email,
        candidate_phone=nomination.candidate_phone,
        member_identifier=nomination.member_identifier,
        status=nomination.status,
        review_notes=nomination.review_notes,
        submitted_at=nomination.submitted_at,
        reviewed_at=nomination.reviewed_at,
        documents=[document_public(item) for item in nomination.documents],
    )


def nomination_options() -> tuple[Any, ...]:
    return (
        joinedload(ProgrammeNomination.programme).joinedload(Programme.institution),
        joinedload(ProgrammeNomination.nominating_institution),
        selectinload(ProgrammeNomination.documents),
    )


def load_nomination(db: Session, nomination_id: UUID) -> ProgrammeNomination:
    nomination = db.scalar(
        select(ProgrammeNomination)
        .where(ProgrammeNomination.id == nomination_id)
        .options(*nomination_options())
        .execution_options(populate_existing=True)
    )
    if nomination is None:
        raise HTTPException(status_code=404, detail="Nomination not found")
    return nomination


def validate_nomination(
    db: Session, user: User, programme: Programme, payload: ProgrammeNominationCreate
) -> None:
    if user.institution_id is None:
        raise HTTPException(status_code=422, detail="A nominating institution is required")
    if payload.nomination_type not in NOMINATION_TYPES:
        raise HTTPException(status_code=422, detail="Select PACS, SHG or cooperative institution")
    if payload.nomination_type.value not in programme.eligible_applicant_types:
        raise HTTPException(status_code=403, detail="This nomination type is not eligible")
    if programme.status != ProgrammeStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Programme is not open for nominations")
    if as_utc(programme.application_deadline) < utc_now():
        raise HTTPException(status_code=409, detail="Nomination deadline has passed")
    email = normalize_email(str(payload.candidate_email))
    if db.scalar(
        select(ProgrammeNomination.id).where(
            ProgrammeNomination.programme_id == programme.id,
            ProgrammeNomination.candidate_email == email,
        )
    ):
        raise HTTPException(status_code=409, detail=f"{email} is already nominated")
    candidate = db.scalar(select(User).where(User.email == email))
    if candidate and db.scalar(
        select(ProgrammeApplication.id).where(
            ProgrammeApplication.programme_id == programme.id,
            ProgrammeApplication.trainee_id == candidate.id,
        )
    ):
        raise HTTPException(status_code=409, detail=f"{email} has already applied")


def create_nomination_record(
    db: Session,
    user: User,
    programme: Programme,
    payload: ProgrammeNominationCreate,
    source: NominationSource,
) -> ProgrammeNomination:
    return ProgrammeNomination(
        programme_id=programme.id,
        nominating_institution_id=user.institution_id,
        created_by_id=user.id,
        nomination_type=payload.nomination_type,
        source=source,
        candidate_full_name=payload.candidate_full_name.strip(),
        candidate_email=normalize_email(str(payload.candidate_email)),
        candidate_phone=payload.candidate_phone,
        member_identifier=payload.member_identifier,
    )


def create_nomination(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    payload: ProgrammeNominationCreate,
) -> ProgrammeNomination:
    validate_nomination(db, user, programme, payload)
    nomination = create_nomination_record(db, user, programme, payload, NominationSource.INDIVIDUAL)
    db.add(nomination)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.nomination_submitted",
        {"programme_id": str(programme.id), "nomination_id": str(nomination.id)},
    )
    db.commit()
    return load_nomination(db, nomination.id)


async def create_bulk_nominations(
    db: Session,
    request: Request,
    user: User,
    programme: Programme,
    nomination_type: EligibilityType,
    upload: UploadFile,
) -> BulkNominationResult:
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_CSV_TYPES or not (upload.filename or "").lower().endswith(
        ".csv"
    ):
        raise HTTPException(status_code=422, detail="Upload a UTF-8 CSV file")
    content = await upload.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV file must be 2 MB or smaller")
    if b"\x00" in content:
        raise HTTPException(status_code=422, detail="CSV file contains invalid binary data")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV file must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(decoded))
    required = {"full_name", "email"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=422,
            detail="CSV headers must include full_name and email",
        )
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV file has no nomination rows")
    if len(rows) > MAX_BULK_ROWS:
        raise HTTPException(status_code=422, detail="CSV file cannot contain more than 500 rows")

    payloads: list[ProgrammeNominationCreate] = []
    seen: set[str] = set()
    errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        try:
            payload = ProgrammeNominationCreate(
                nomination_type=nomination_type,
                candidate_full_name=(row.get("full_name") or "").strip(),
                candidate_email=(row.get("email") or "").strip(),
                candidate_phone=(row.get("phone") or "").strip() or None,
                member_identifier=(row.get("member_identifier") or "").strip() or None,
            )
            email = normalize_email(str(payload.candidate_email))
            if email in seen:
                errors.append(f"Row {index}: duplicate email in file")
                continue
            seen.add(email)
            validate_nomination(db, user, programme, payload)
            payloads.append(payload)
        except (ValidationError, HTTPException) as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else "invalid nomination data"
            errors.append(f"Row {index}: {detail}")
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    nominations = [
        create_nomination_record(db, user, programme, payload, NominationSource.BULK_CSV)
        for payload in payloads
    ]
    db.add_all(nominations)
    db.flush()
    ids = [item.id for item in nominations]
    add_programme_audit(
        db,
        request,
        user,
        "programme.bulk_nominations_submitted",
        {"programme_id": str(programme.id), "count": len(nominations)},
    )
    db.commit()
    loaded = [load_nomination(db, nomination_id) for nomination_id in ids]
    return BulkNominationResult(
        created=len(loaded), nominations=[nomination_public(item) for item in loaded]
    )


def list_nominations(
    db: Session, user: User, programme_id: UUID | None = None
) -> list[ProgrammeNominationPublic]:
    statement = (
        select(ProgrammeNomination)
        .options(*nomination_options())
        .order_by(ProgrammeNomination.submitted_at.desc())
    )
    if user_has(user, Permission.APPLICATIONS_REVIEW):
        if programme_id:
            programme = load_programme(db, programme_id)
            ensure_reviewer(user, programme)
            statement = statement.where(ProgrammeNomination.programme_id == programme_id)
        elif not user_has(user, Permission.PLATFORM_MANAGE):
            statement = statement.join(Programme).where(
                Programme.institution_id == user.institution_id
            )
    else:
        statement = statement.where(ProgrammeNomination.created_by_id == user.id)
    return [nomination_public(item) for item in db.scalars(statement).unique().all()]


def review_nomination(
    db: Session,
    request: Request,
    user: User,
    nomination: ProgrammeNomination,
    payload: ReviewUpdate,
) -> ProgrammeNomination:
    ensure_reviewer(user, nomination.programme)
    if payload.status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported review status")
    if (
        payload.status == ApplicationStatus.APPROVED
        and nomination.status != ApplicationStatus.APPROVED
    ):
        locked_programme = db.scalar(
            select(Programme).where(Programme.id == nomination.programme_id).with_for_update()
        )
        if locked_programme is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        if approved_count(db, nomination.programme_id) >= locked_programme.capacity:
            raise HTTPException(status_code=409, detail="Programme capacity has been reached")
    nomination.status = payload.status
    nomination.review_notes = payload.review_notes
    nomination.reviewer_id = user.id
    nomination.reviewed_at = utc_now()
    add_programme_audit(
        db,
        request,
        user,
        "programme.nomination_reviewed",
        {
            "programme_id": str(nomination.programme_id),
            "nomination_id": str(nomination.id),
            "status": payload.status.value,
        },
    )
    db.commit()
    return load_nomination(db, nomination.id)


async def store_document(
    db: Session,
    request: Request,
    user: User,
    upload: UploadFile,
    document_type: DocumentType,
    *,
    application: ProgrammeApplication | None = None,
    nomination: ProgrammeNomination | None = None,
) -> ApplicationDocument:
    content, content_type, filename = await read_validated_upload(
        upload,
        allowed_types=DOCUMENT_TYPES,
        maximum_bytes=MAX_DOCUMENT_BYTES,
        kind="document",
    )

    if application:
        if application.trainee_id != user.id:
            ensure_reviewer(user, application.programme)
    elif nomination:
        if nomination.created_by_id != user.id:
            ensure_reviewer(user, nomination.programme)
    else:
        raise HTTPException(status_code=422, detail="Document owner is required")

    document = ApplicationDocument(
        application_id=application.id if application else None,
        nomination_id=nomination.id if nomination else None,
        uploaded_by_id=user.id,
        document_type=document_type,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        content=content,
    )
    db.add(document)
    db.flush()
    add_programme_audit(
        db,
        request,
        user,
        "programme.document_uploaded",
        {
            "document_id": str(document.id),
            "application_id": str(application.id) if application else None,
            "nomination_id": str(nomination.id) if nomination else None,
        },
    )
    db.commit()
    db.refresh(document)
    return document


def load_document_for_user(db: Session, user: User, document_id: UUID) -> ApplicationDocument:
    document = db.scalar(
        select(ApplicationDocument)
        .where(ApplicationDocument.id == document_id)
        .options(
            joinedload(ApplicationDocument.application).joinedload(ProgrammeApplication.programme),
            joinedload(ApplicationDocument.nomination).joinedload(ProgrammeNomination.programme),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.application:
        if document.application.trainee_id != user.id:
            ensure_reviewer(user, document.application.programme)
    elif document.nomination and document.nomination.created_by_id != user.id:
        ensure_reviewer(user, document.nomination.programme)
    return document


def list_trainers(db: Session, user: User) -> list[TrainerBrief]:
    if user.institution_id is None:
        return []
    trainers = db.scalars(
        select(User)
        .where(User.institution_id == user.institution_id)
        .join(User.roles)
        .where(Role.code == RoleCode.TRAINER)
        .options(joinedload(User.profile))
        .order_by(User.email)
    ).unique()
    return [
        TrainerBrief(
            id=trainer.id,
            full_name=trainer.profile.full_name if trainer.profile else trainer.email,
            email=trainer.email,
        )
        for trainer in trainers
    ]
