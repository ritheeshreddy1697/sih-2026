from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.permissions import Permission, has_permission
from app.core.uploads import DOCUMENT_TYPES, read_validated_upload
from app.models import (
    AuditLog,
    BatchTrainerAssignment,
    ConsentRecord,
    CooperativeMembership,
    DocumentValidationStatus,
    EducationRecord,
    EmploymentRecord,
    Institution,
    InstitutionType,
    ProfileDocumentType,
    ProgrammeEnrollment,
    Role,
    RoleCode,
    TraineeDocument,
    TraineeProfile,
    User,
    UserProfile,
    user_roles,
)
from app.schemas.profile import (
    AssessmentPublic,
    AttendancePublic,
    AuditEventPublic,
    CertificatePublic,
    ConsentPreferences,
    EducationCreate,
    EducationPublic,
    EmploymentCreate,
    EmploymentPublic,
    EnrollmentPublic,
    InstitutionCreate,
    InstitutionListResponse,
    InstitutionPublic,
    InstitutionSummary,
    InstitutionUpdate,
    MembershipCreate,
    MembershipPublic,
    PersonalProfileUpdate,
    ProfileCompletion,
    ProfileDocumentPublic,
    TraineeListItem,
    TraineeListResponse,
    TraineeProfileDetail,
    TrainerListItem,
    TrainerListResponse,
)
from app.services.auth import get_client_details

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
CONSENT_VERSION = "profile-v1"


def utc_now() -> datetime:
    return datetime.now(UTC)


def user_has(user: User, permission: Permission) -> bool:
    return has_permission({role.code for role in user.roles}, permission)


def add_profile_audit(
    db: Session,
    request: Request,
    actor: User,
    event_type: str,
    target_user_id: UUID | None = None,
    **details: Any,
) -> None:
    ip_address, user_agent = get_client_details(request)
    if target_user_id:
        details["target_user_id"] = str(target_user_id)
    db.add(
        AuditLog(
            user_id=actor.id,
            event_type=event_type,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    )


def scoped_institution_ids(db: Session, user: User) -> set[UUID] | None:
    if user_has(user, Permission.PLATFORM_MANAGE):
        return None
    if user.institution_id is None:
        return set()
    institutions = list(db.execute(select(Institution.id, Institution.parent_id)).all())
    allowed = {user.institution_id}
    changed = True
    while changed:
        changed = False
        for institution_id, parent_id in institutions:
            if parent_id in allowed and institution_id not in allowed:
                allowed.add(institution_id)
                changed = True
    return allowed


def ensure_institution_scope(db: Session, user: User, institution_id: UUID | None) -> None:
    allowed = scoped_institution_ids(db, user)
    if allowed is not None and (institution_id is None or institution_id not in allowed):
        raise HTTPException(
            status_code=403, detail="Institution is outside your administrative scope"
        )


def ensure_trainee(user: User) -> None:
    if RoleCode.TRAINEE not in {role.code for role in user.roles}:
        raise HTTPException(status_code=404, detail="Trainee profile not found")


def ensure_trainee_access(db: Session, actor: User, trainee: User) -> None:
    ensure_trainee(trainee)
    if actor.id == trainee.id and user_has(actor, Permission.PROFILE_SELF_MANAGE):
        return
    if not user_has(actor, Permission.PROFILE_ADMIN_VIEW):
        raise HTTPException(status_code=403, detail="You cannot access this trainee profile")
    allowed = scoped_institution_ids(db, actor)
    if allowed is not None and trainee.institution_id not in allowed:
        raise HTTPException(status_code=404, detail="Trainee profile not found")


def profile_options() -> tuple[Any, ...]:
    return (
        joinedload(TraineeProfile.user).joinedload(User.profile),
        joinedload(TraineeProfile.user).joinedload(User.institution),
        selectinload(TraineeProfile.education),
        selectinload(TraineeProfile.employment),
        selectinload(TraineeProfile.memberships),
        selectinload(TraineeProfile.documents)
        .joinedload(TraineeDocument.validated_by)
        .joinedload(User.profile),
    )


def load_profile(db: Session, user_id: UUID, *, create: bool = False) -> TraineeProfile:
    profile = db.scalar(
        select(TraineeProfile)
        .where(TraineeProfile.user_id == user_id)
        .options(*profile_options())
        .execution_options(populate_existing=True)
    )
    if profile is None and create:
        profile = TraineeProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        return load_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Trainee profile not found")
    return profile


def completion_for(profile: TraineeProfile) -> ProfileCompletion:
    account = profile.user.profile
    checks = {
        "Personal information": bool(account and account.full_name and profile.date_of_birth),
        "Contact information": bool(account and account.phone and profile.address_line),
        "Location": bool(profile.city and profile.state and profile.postal_code),
        "Language and location preferences": bool(
            profile.preferred_language and profile.preferred_location
        ),
        "Skills": bool(profile.skills),
        "Career interests": bool(profile.career_interests),
        "Education": bool(profile.education),
        "Employment or cooperative membership": bool(profile.employment or profile.memberships),
        "Documents": bool(profile.documents),
        "Consent preferences": True,
    }
    completed = [name for name, value in checks.items() if value]
    missing = [name for name, value in checks.items() if not value]
    return ProfileCompletion(
        percent=round(len(completed) / len(checks) * 100),
        completed_sections=completed,
        missing_sections=missing,
    )


def refresh_completion(db: Session, profile: TraineeProfile) -> None:
    db.flush()
    loaded = load_profile(db, profile.user_id)
    loaded.completion_percent = completion_for(loaded).percent
    db.flush()


def institution_summary(institution: Institution | None) -> InstitutionSummary | None:
    if institution is None:
        return None
    return InstitutionSummary(
        id=institution.id,
        name=institution.name,
        code=institution.code,
        institution_type=institution.institution_type,
    )


def institution_public(institution: Institution) -> InstitutionPublic:
    return InstitutionPublic(
        **institution_summary(institution).model_dump(),  # type: ignore[union-attr]
        parent=institution_summary(institution.parent),
        state=institution.state,
        district=institution.district,
        address=institution.address,
        contact_email=institution.contact_email,
        contact_phone=institution.contact_phone,
        website=institution.website,
        registration_number=institution.registration_number,
        profile_summary=institution.profile_summary,
        is_active=institution.is_active,
        is_demo=institution.is_demo,
        child_count=len(institution.children),
        children=[
            institution_summary(child)
            for child in sorted(institution.children, key=lambda item: item.name)
        ],
    )


def list_institutions(
    db: Session,
    user: User,
    *,
    query_text: str | None,
    institution_type: InstitutionType | None,
    state_name: str | None,
    active_only: bool,
    page: int,
    page_size: int,
) -> InstitutionListResponse:
    conditions: list[Any] = []
    allowed = scoped_institution_ids(db, user)
    if allowed is not None:
        conditions.append(Institution.id.in_(allowed))
    if query_text:
        pattern = f"%{query_text.strip()}%"
        conditions.append(or_(Institution.name.ilike(pattern), Institution.code.ilike(pattern)))
    if institution_type:
        conditions.append(Institution.institution_type == institution_type)
    if state_name:
        conditions.append(Institution.state.ilike(state_name.strip()))
    if active_only:
        conditions.append(Institution.is_active.is_(True))
    total = int(db.scalar(select(func.count(Institution.id)).where(*conditions)) or 0)
    rows = db.scalars(
        select(Institution)
        .where(*conditions)
        .options(joinedload(Institution.parent), selectinload(Institution.children))
        .order_by(Institution.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return InstitutionListResponse(
        items=[institution_public(item) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def validate_parent(
    db: Session,
    actor: User,
    institution_type: InstitutionType,
    parent_id: UUID | None,
    current_id: UUID | None = None,
) -> Institution | None:
    if institution_type == InstitutionType.NCCT and parent_id is not None:
        raise HTTPException(status_code=422, detail="NCCT must be a root institution")
    if institution_type != InstitutionType.NCCT and parent_id is None:
        raise HTTPException(status_code=422, detail="Select a parent institution")
    if parent_id is None:
        return None
    if parent_id == current_id:
        raise HTTPException(status_code=422, detail="An institution cannot be its own parent")
    parent = db.get(Institution, parent_id)
    if parent is None:
        raise HTTPException(status_code=422, detail="Parent institution not found")
    ensure_institution_scope(db, actor, parent.id)
    cursor = parent
    while cursor.parent_id:
        if cursor.parent_id == current_id:
            raise HTTPException(
                status_code=422, detail="Institution hierarchy cannot contain a cycle"
            )
        next_parent = db.get(Institution, cursor.parent_id)
        if next_parent is None:
            break
        cursor = next_parent
    return parent


def create_institution(
    db: Session, request: Request, actor: User, payload: InstitutionCreate
) -> Institution:
    if not user_has(actor, Permission.PLATFORM_MANAGE):
        raise HTTPException(status_code=403, detail="Only NCCT can create institutions")
    if db.scalar(select(Institution.id).where(Institution.code == payload.code)):
        raise HTTPException(status_code=409, detail="Institution code already exists")
    validate_parent(db, actor, payload.institution_type, payload.parent_id)
    institution = Institution(**payload.model_dump(), is_demo=False)
    db.add(institution)
    db.flush()
    add_profile_audit(
        db,
        request,
        actor,
        "profile.institution_created",
        institution_id=str(institution.id),
        code=institution.code,
    )
    db.commit()
    return get_institution(db, actor, institution.id)


def get_institution(db: Session, actor: User, institution_id: UUID) -> Institution:
    ensure_institution_scope(db, actor, institution_id)
    institution = db.scalar(
        select(Institution)
        .where(Institution.id == institution_id)
        .options(joinedload(Institution.parent), selectinload(Institution.children))
        .execution_options(populate_existing=True)
    )
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


def update_institution(
    db: Session,
    request: Request,
    actor: User,
    institution: Institution,
    payload: InstitutionUpdate,
) -> Institution:
    changes = payload.model_dump(exclude_unset=True)
    institution_type = changes.get("institution_type", institution.institution_type)
    parent_id = changes.get("parent_id", institution.parent_id)
    validate_parent(db, actor, institution_type, parent_id, institution.id)
    code = changes.get("code")
    if (
        code
        and code != institution.code
        and db.scalar(select(Institution.id).where(Institution.code == code))
    ):
        raise HTTPException(status_code=409, detail="Institution code already exists")
    for key, value in changes.items():
        setattr(institution, key, value)
    add_profile_audit(
        db,
        request,
        actor,
        "profile.institution_updated",
        institution_id=str(institution.id),
        fields=sorted(changes),
    )
    db.commit()
    return get_institution(db, actor, institution.id)


def document_public(document: TraineeDocument) -> ProfileDocumentPublic:
    validator = document.validated_by
    return ProfileDocumentPublic(
        id=document.id,
        document_type=document.document_type,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        validation_status=document.validation_status,
        validation_notes=document.validation_notes,
        validated_by_name=(
            validator.profile.full_name if validator and validator.profile else None
        ),
        validated_at=document.validated_at,
        uploaded_at=document.uploaded_at,
    )


def enrollment_public(enrollment: ProgrammeEnrollment) -> EnrollmentPublic:
    return EnrollmentPublic(
        id=enrollment.id,
        programme_id=enrollment.programme_id,
        programme_title=enrollment.programme.title,
        programme_code=enrollment.programme.code,
        batch_name=enrollment.batch.name if enrollment.batch else None,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
        completed_at=enrollment.completed_at,
        attendance=[AttendancePublic.model_validate(item) for item in enrollment.attendance],
        assessments=[AssessmentPublic.model_validate(item) for item in enrollment.assessments],
        certificates=[CertificatePublic.model_validate(item) for item in enrollment.certificates],
    )


def audit_history(db: Session, trainee: User) -> list[AuditEventPublic]:
    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.event_type.like("profile.%"))
            .order_by(AuditLog.created_at.desc())
            .limit(250)
        ).all()
    )
    target = str(trainee.id)
    visible = [
        item
        for item in logs
        if item.user_id == trainee.id or str(item.details.get("target_user_id", "")) == target
    ][:50]
    actor_ids = {item.user_id for item in visible if item.user_id}
    actors = {
        user.id: user
        for user in db.scalars(
            select(User).where(User.id.in_(actor_ids)).options(joinedload(User.profile))
        ).all()
    }
    events = []
    for item in visible:
        actor = actors.get(item.user_id) if item.user_id else None
        actor_name = actor.profile.full_name if actor and actor.profile else "System"
        events.append(
            AuditEventPublic(
                id=item.id,
                event_type=item.event_type,
                success=item.success,
                actor_name=actor_name,
                details=item.details,
                created_at=item.created_at,
            )
        )
    return events


def profile_detail(db: Session, profile: TraineeProfile) -> TraineeProfileDetail:
    user = profile.user
    account = user.profile
    enrollments = db.scalars(
        select(ProgrammeEnrollment)
        .where(ProgrammeEnrollment.trainee_id == user.id)
        .options(
            joinedload(ProgrammeEnrollment.programme),
            joinedload(ProgrammeEnrollment.batch),
            selectinload(ProgrammeEnrollment.attendance),
            selectinload(ProgrammeEnrollment.assessments),
            selectinload(ProgrammeEnrollment.certificates),
        )
        .order_by(ProgrammeEnrollment.enrolled_at.desc())
    ).unique()
    completion = completion_for(profile)
    return TraineeProfileDetail(
        user_id=user.id,
        full_name=account.full_name if account else user.email,
        email=user.email,
        phone=account.phone if account else None,
        designation=account.designation if account else None,
        institution=institution_summary(user.institution),
        account_status=user.status,
        preferred_language=profile.preferred_language,
        preferred_location=profile.preferred_location,
        state=profile.state,
        skills=profile.skills,
        completion_percent=completion.percent,
        pending_documents=sum(
            item.validation_status == DocumentValidationStatus.PENDING for item in profile.documents
        ),
        is_demo=profile.is_demo,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        alternate_email=profile.alternate_email,
        address_line=profile.address_line,
        city=profile.city,
        postal_code=profile.postal_code,
        career_interests=profile.career_interests,
        completion=completion,
        education=[EducationPublic.model_validate(item) for item in profile.education],
        employment=[EmploymentPublic.model_validate(item) for item in profile.employment],
        memberships=[MembershipPublic.model_validate(item) for item in profile.memberships],
        documents=[document_public(item) for item in profile.documents],
        enrollments=[enrollment_public(item) for item in enrollments],
        consent_preferences=ConsentPreferences(
            placement_visibility_consent=profile.placement_visibility_consent,
            communication_consent=profile.communication_consent,
            data_sharing_consent=profile.data_sharing_consent,
        ),
        audit_history=audit_history(db, user),
    )


def list_trainees(
    db: Session,
    actor: User,
    *,
    query_text: str | None,
    institution_id: UUID | None,
    state_name: str | None,
    language: str | None,
    skill: str | None,
    minimum_completion: int | None,
    page: int,
    page_size: int,
) -> TraineeListResponse:
    conditions: list[Any] = [Role.code == RoleCode.TRAINEE]
    has_private_access = user_has(actor, Permission.PROFILE_ADMIN_VIEW)
    if has_private_access:
        allowed = scoped_institution_ids(db, actor)
        if allowed is not None:
            conditions.append(User.institution_id.in_(allowed))
    else:
        allowed = None
        conditions.append(
            User.id.in_(
                select(ProgrammeEnrollment.trainee_id)
                .join(
                    BatchTrainerAssignment,
                    BatchTrainerAssignment.batch_id == ProgrammeEnrollment.batch_id,
                )
                .where(BatchTrainerAssignment.trainer_id == actor.id)
            )
        )
    if institution_id:
        if has_private_access and allowed is not None and institution_id not in allowed:
            raise HTTPException(status_code=403, detail="Institution is outside your scope")
        conditions.append(User.institution_id == institution_id)
    if query_text:
        conditions.append(user_search_condition(query_text))
    if state_name:
        conditions.append(TraineeProfile.state.ilike(state_name.strip()))
    if language:
        conditions.append(TraineeProfile.preferred_language.ilike(language.strip()))
    if skill:
        conditions.append(cast(TraineeProfile.skills, String).ilike(f"%{skill.strip()}%"))
    if minimum_completion is not None:
        conditions.append(TraineeProfile.completion_percent >= minimum_completion)

    joins = (
        select(User)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(TraineeProfile, TraineeProfile.user_id == User.id)
    )
    total_statement = (
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(TraineeProfile, TraineeProfile.user_id == User.id)
        .where(*conditions)
    )
    total = int(db.scalar(total_statement) or 0)
    users = list(
        db.scalars(
            joins.where(*conditions)
            .options(
                joinedload(User.profile),
                joinedload(User.institution),
                joinedload(User.trainee_profile).selectinload(TraineeProfile.documents),
            )
            .order_by(UserProfile.full_name, User.email)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    items = []
    for user in users:
        profile = user.trainee_profile
        items.append(
            TraineeListItem(
                user_id=user.id,
                full_name=user.profile.full_name if user.profile else user.email,
                email=user.email,
                phone=user.profile.phone if user.profile else None,
                institution=institution_summary(user.institution),
                account_status=user.status,
                preferred_language=profile.preferred_language if profile else None,
                preferred_location=profile.preferred_location if profile else None,
                state=profile.state if profile else None,
                skills=profile.skills if profile else [],
                completion_percent=profile.completion_percent if profile else 0,
                pending_documents=(
                    sum(
                        item.validation_status == DocumentValidationStatus.PENDING
                        for item in profile.documents
                    )
                    if profile
                    else 0
                ),
                is_demo=profile.is_demo if profile else False,
            )
        )
    return TraineeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def user_search_condition(query_text: str) -> Any:
    value = query_text.strip()
    matches: list[Any] = [
        User.email.ilike(f"%{value}%"),
        UserProfile.full_name.ilike(f"%{value}%"),
    ]
    try:
        matches.append(User.id == UUID(value))
    except ValueError:
        pass
    return or_(*matches)


def list_trainers(
    db: Session,
    actor: User,
    *,
    query_text: str | None,
    institution_id: UUID | None,
    page: int,
    page_size: int,
) -> TrainerListResponse:
    conditions: list[Any] = [Role.code == RoleCode.TRAINER]
    allowed = scoped_institution_ids(db, actor)
    if allowed is not None:
        conditions.append(User.institution_id.in_(allowed))
    if institution_id:
        if allowed is not None and institution_id not in allowed:
            raise HTTPException(status_code=403, detail="Institution is outside your scope")
        conditions.append(User.institution_id == institution_id)
    if query_text:
        conditions.append(user_search_condition(query_text))

    base = (
        select(User)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
    )
    total = int(
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(user_roles, user_roles.c.user_id == User.id)
            .join(Role, Role.id == user_roles.c.role_id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(*conditions)
        )
        or 0
    )
    users = list(
        db.scalars(
            base.where(*conditions)
            .options(joinedload(User.profile), joinedload(User.institution))
            .order_by(UserProfile.full_name, User.email)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    return TrainerListResponse(
        items=[
            TrainerListItem(
                user_id=user.id,
                full_name=user.profile.full_name if user.profile else user.email,
                email=user.email,
                phone=user.profile.phone if user.profile else None,
                designation=user.profile.designation if user.profile else None,
                institution=institution_summary(user.institution),
                account_status=user.status,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def update_personal(
    db: Session,
    request: Request,
    user: User,
    payload: PersonalProfileUpdate,
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    changes = payload.model_dump(exclude_unset=True)
    account_fields = {"full_name", "phone", "designation"}
    account = profile.user.profile
    if account is None:
        account = UserProfile(user_id=user.id, full_name=changes.pop("full_name", user.email))
        db.add(account)
    for field in account_fields.intersection(changes):
        setattr(account, field, changes.pop(field))
    for field, value in changes.items():
        setattr(profile, field, value)
    refresh_completion(db, profile)
    add_profile_audit(
        db,
        request,
        user,
        "profile.personal_updated",
        target_user_id=user.id,
        fields=sorted(payload.model_fields_set),
    )
    db.commit()
    return load_profile(db, user.id)


def add_education(
    db: Session, request: Request, user: User, payload: EducationCreate
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    record = EducationRecord(profile_id=profile.id, **payload.model_dump())
    if record.is_highest_qualification:
        for item in profile.education:
            item.is_highest_qualification = False
    db.add(record)
    refresh_completion(db, profile)
    add_profile_audit(db, request, user, "profile.education_added", user.id)
    db.commit()
    return load_profile(db, user.id)


def add_employment(
    db: Session, request: Request, user: User, payload: EmploymentCreate
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    db.add(EmploymentRecord(profile_id=profile.id, **payload.model_dump()))
    refresh_completion(db, profile)
    add_profile_audit(db, request, user, "profile.employment_added", user.id)
    db.commit()
    return load_profile(db, user.id)


def add_membership(
    db: Session, request: Request, user: User, payload: MembershipCreate
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    db.add(CooperativeMembership(profile_id=profile.id, **payload.model_dump()))
    refresh_completion(db, profile)
    add_profile_audit(db, request, user, "profile.membership_added", user.id)
    db.commit()
    return load_profile(db, user.id)


def delete_record(
    db: Session,
    request: Request,
    user: User,
    model: type[EducationRecord] | type[EmploymentRecord] | type[CooperativeMembership],
    record_id: UUID,
    event_type: str,
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    record: Any = db.get(model, record_id)
    if record is None or record.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Profile record not found")
    db.delete(record)
    refresh_completion(db, profile)
    add_profile_audit(db, request, user, event_type, user.id, record_id=str(record_id))
    db.commit()
    return load_profile(db, user.id)


async def store_document(
    db: Session,
    request: Request,
    user: User,
    upload: UploadFile,
    document_type: ProfileDocumentType,
) -> TraineeProfile:
    content, content_type, filename = await read_validated_upload(
        upload,
        allowed_types=DOCUMENT_TYPES,
        maximum_bytes=MAX_DOCUMENT_BYTES,
        kind="document",
    )
    profile = load_profile(db, user.id, create=True)
    document = TraineeDocument(
        profile_id=profile.id,
        uploaded_by_id=user.id,
        document_type=document_type,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        content=content,
    )
    db.add(document)
    refresh_completion(db, profile)
    add_profile_audit(
        db,
        request,
        user,
        "profile.document_uploaded",
        user.id,
        document_id=str(document.id),
        document_type=str(document_type),
    )
    db.commit()
    return load_profile(db, user.id)


def load_document_for_user(db: Session, actor: User, document_id: UUID) -> TraineeDocument:
    document = db.scalar(
        select(TraineeDocument)
        .where(TraineeDocument.id == document_id)
        .options(joinedload(TraineeDocument.profile).joinedload(TraineeProfile.user))
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_trainee_access(db, actor, document.profile.user)
    return document


def validate_document(
    db: Session,
    request: Request,
    actor: User,
    document: TraineeDocument,
    validation_status: DocumentValidationStatus,
    notes: str | None,
) -> TraineeDocument:
    document.validation_status = validation_status
    document.validation_notes = notes
    document.validated_by_id = actor.id
    document.validated_at = utc_now()
    add_profile_audit(
        db,
        request,
        actor,
        "profile.document_validated",
        document.profile.user_id,
        document_id=str(document.id),
        status=validation_status.value,
    )
    db.commit()
    return load_document_for_user(db, actor, document.id)


def update_consents(
    db: Session,
    request: Request,
    user: User,
    payload: ConsentPreferences,
) -> TraineeProfile:
    profile = load_profile(db, user.id, create=True)
    now = utc_now()
    for field, granted in payload.model_dump().items():
        if getattr(profile, field) == granted:
            continue
        setattr(profile, field, granted)
        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type=field,
                version=CONSENT_VERSION,
                granted=granted,
                recorded_at=now,
                withdrawn_at=None if granted else now,
                ip_address=get_client_details(request)[0],
            )
        )
    add_profile_audit(db, request, user, "profile.consents_updated", user.id)
    db.commit()
    return load_profile(db, user.id)
