from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.permissions import Permission, has_permission
from app.core.security import (
    TokenValidationError,
    create_scoped_token,
    decode_scoped_token,
    hash_token,
)
from app.models import (
    AccountStatus,
    AttendanceCheckIn,
    AttendanceCorrection,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
    AuditLog,
    BatchTrainerAssignment,
    BiometricEnrollment,
    CorrectionStatus,
    EnrollmentStatus,
    Institution,
    KioskDevice,
    KioskDeviceStatus,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    RoleCode,
    TraineeProfile,
    User,
)
from app.schemas.attendance import (
    AttendanceCorrectionCreate,
    AttendanceCorrectionPublic,
    AttendanceCorrectionReview,
    AttendanceReportPublic,
    AttendanceReportRow,
    AttendanceSessionCreate,
    AttendanceSessionPublic,
    AttendanceSessionUpdate,
    CheckInSyncItem,
    CheckInSyncResponse,
    KioskDeviceCreate,
    KioskDevicePublic,
    KioskDeviceRegistered,
    KioskSessionPublic,
    OfflineCheckIn,
    SessionQrPublic,
    SessionTraineePublic,
    TraineeIdentityPublic,
)
from app.services.auth import get_client_details

SESSION_QR_SECONDS = 45
SESSION_EARLY_WINDOW = timedelta(minutes=15)
SESSION_LATE_WINDOW = timedelta(minutes=15)


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def role_codes(user: User) -> set[RoleCode]:
    return {role.code for role in user.roles}


def user_has(user: User, permission: Permission) -> bool:
    return has_permission(role_codes(user), permission)


def display_name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def add_audit(
    db: Session,
    request: Request,
    event_type: str,
    *,
    user: User | None = None,
    success: bool = True,
    details: dict[str, Any] | None = None,
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            event_type=event_type,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
    )


def session_options() -> tuple[Any, ...]:
    return (
        joinedload(AttendanceSession.programme).joinedload(Programme.institution),
        joinedload(AttendanceSession.batch),
        joinedload(AttendanceSession.created_by).joinedload(User.profile),
        selectinload(AttendanceSession.check_ins),
    )


def load_session(db: Session, session_id: UUID) -> AttendanceSession:
    item = db.scalar(
        select(AttendanceSession)
        .where(AttendanceSession.id == session_id)
        .options(*session_options())
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Attendance session not found")
    return item


def can_manage_batch(db: Session, user: User, programme: Programme, batch_id: UUID) -> bool:
    roles = role_codes(user)
    if user_has(user, Permission.PLATFORM_MANAGE):
        return True
    if RoleCode.INSTITUTE_ADMIN in roles:
        return user.institution_id == programme.institution_id
    if RoleCode.TRAINER in roles:
        return (
            db.scalar(
                select(BatchTrainerAssignment.id).where(
                    BatchTrainerAssignment.batch_id == batch_id,
                    BatchTrainerAssignment.trainer_id == user.id,
                )
            )
            is not None
        )
    return False


def ensure_session_manager(db: Session, user: User, item: AttendanceSession) -> None:
    if not can_manage_batch(db, user, item.programme, item.batch_id):
        raise HTTPException(
            status_code=403,
            detail="You can manage only assigned or institution-owned attendance sessions",
        )


def session_public(item: AttendanceSession) -> AttendanceSessionPublic:
    return AttendanceSessionPublic(
        id=item.id,
        programme_id=item.programme_id,
        programme_title=item.programme.title,
        programme_code=item.programme.code,
        batch_id=item.batch_id,
        batch_name=item.batch.name,
        title=item.title,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        status=item.status,
        check_in_count=len(item.check_ins),
    )


def list_sessions(db: Session, user: User) -> list[AttendanceSessionPublic]:
    statement = (
        select(AttendanceSession)
        .options(*session_options())
        .order_by(AttendanceSession.starts_at.desc())
    )
    roles = role_codes(user)
    if not user_has(user, Permission.PLATFORM_MANAGE):
        if RoleCode.INSTITUTE_ADMIN in roles:
            statement = statement.join(AttendanceSession.programme).where(
                Programme.institution_id == user.institution_id
            )
        elif RoleCode.TRAINER in roles:
            statement = statement.join(
                BatchTrainerAssignment,
                BatchTrainerAssignment.batch_id == AttendanceSession.batch_id,
            ).where(BatchTrainerAssignment.trainer_id == user.id)
        else:
            raise HTTPException(status_code=403, detail="Attendance management is not permitted")
    return [session_public(item) for item in db.scalars(statement).unique()]


def create_session(
    db: Session,
    request: Request,
    user: User,
    payload: AttendanceSessionCreate,
) -> AttendanceSession:
    programme = db.get(Programme, payload.programme_id)
    batch = db.get(ProgrammeBatch, payload.batch_id)
    if programme is None or batch is None or batch.programme_id != programme.id:
        raise HTTPException(status_code=422, detail="Batch does not belong to the programme")
    if not can_manage_batch(db, user, programme, batch.id):
        raise HTTPException(status_code=403, detail="You are not assigned to this batch")
    starts_at = as_utc(payload.starts_at)
    ends_at = as_utc(payload.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="Session end time must be after start time")
    item = AttendanceSession(
        programme_id=programme.id,
        batch_id=batch.id,
        created_by_id=user.id,
        title=payload.title.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
    )
    db.add(item)
    add_audit(
        db,
        request,
        "attendance.session_created",
        user=user,
        details={"programme_id": str(programme.id), "batch_id": str(batch.id)},
    )
    db.commit()
    return load_session(db, item.id)


def update_session(
    db: Session,
    request: Request,
    user: User,
    item: AttendanceSession,
    payload: AttendanceSessionUpdate,
) -> AttendanceSession:
    ensure_session_manager(db, user, item)
    values = payload.model_dump(exclude_unset=True)
    starts_at = as_utc(values.get("starts_at", item.starts_at))
    ends_at = as_utc(values.get("ends_at", item.ends_at))
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="Session end time must be after start time")
    if "title" in values:
        item.title = values["title"].strip()
    item.starts_at = starts_at
    item.ends_at = ends_at
    if "status" in values:
        item.status = values["status"]
    add_audit(
        db,
        request,
        "attendance.session_updated",
        user=user,
        details={"session_id": str(item.id), "fields": sorted(values)},
    )
    db.commit()
    return load_session(db, item.id)


def session_qr(db: Session, user: User, item: AttendanceSession) -> SessionQrPublic:
    ensure_session_manager(db, user, item)
    if item.status != AttendanceSessionStatus.OPEN:
        raise HTTPException(status_code=409, detail="Only open sessions can issue kiosk QR codes")
    expires_at = utc_now() + timedelta(seconds=SESSION_QR_SECONDS)
    token = create_scoped_token(
        item.id,
        "attendance_session",
        expires_at=expires_at,
        claims={"programme_id": str(item.programme_id), "batch_id": str(item.batch_id)},
    )
    return SessionQrPublic(
        payload=f"NCCT-SESSION:{token}",
        expires_at=expires_at,
        refresh_after_seconds=30,
    )


def get_or_create_trainee_profile(db: Session, user: User) -> TraineeProfile:
    profile = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == user.id))
    if profile is None:
        profile = TraineeProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


def identity_public(db: Session, user: User) -> TraineeIdentityPublic:
    if RoleCode.TRAINEE not in role_codes(user):
        raise HTTPException(status_code=403, detail="A trainee account is required")
    profile = get_or_create_trainee_profile(db, user)
    token = create_scoped_token(
        user.id,
        "trainee_identity",
        claims={"version": profile.qr_identity_version},
        deterministic=True,
    )
    db.commit()
    return TraineeIdentityPublic(
        trainee_id=user.id,
        full_name=display_name(user),
        identity_code=f"NCCT-{str(user.id).split('-')[0].upper()}",
        qr_payload=f"NCCT-TRAINEE:{token}",
    )


def session_trainees(
    db: Session, user: User, item: AttendanceSession
) -> list[SessionTraineePublic]:
    ensure_session_manager(db, user, item)
    enrollments = list(
        db.scalars(
            select(ProgrammeEnrollment)
            .where(
                ProgrammeEnrollment.programme_id == item.programme_id,
                ProgrammeEnrollment.batch_id == item.batch_id,
                ProgrammeEnrollment.status.in_(
                    [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
                ),
            )
            .options(joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile))
        ).unique()
    )
    check_ins = {check_in.enrollment_id: check_in for check_in in item.check_ins}
    result: list[SessionTraineePublic] = []
    for enrollment in enrollments:
        identity = identity_public(db, enrollment.trainee)
        check_in = check_ins.get(enrollment.id)
        result.append(
            SessionTraineePublic(
                **identity.model_dump(),
                enrollment_id=enrollment.id,
                checked_in=check_in is not None,
                attendance_status=check_in.status if check_in else None,
            )
        )
    return result


def device_public(device: KioskDevice) -> KioskDevicePublic:
    return KioskDevicePublic(
        id=device.id,
        institution_id=device.institution_id,
        institution_name=device.institution.name,
        name=device.name,
        device_code=device.device_code,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
    )


def register_device(
    db: Session,
    request: Request,
    user: User,
    payload: KioskDeviceCreate,
) -> KioskDeviceRegistered:
    institution_id = payload.institution_id or user.institution_id
    if institution_id is None:
        raise HTTPException(status_code=422, detail="A kiosk institution is required")
    if not user_has(user, Permission.PLATFORM_MANAGE) and institution_id != user.institution_id:
        raise HTTPException(
            status_code=403, detail="You can register only your institution's kiosks"
        )
    institution = db.get(Institution, institution_id)
    if institution is None or not institution.is_active:
        raise HTTPException(status_code=422, detail="Active institution not found")
    raw_token = secrets.token_urlsafe(32)
    device = KioskDevice(
        institution_id=institution.id,
        registered_by_id=user.id,
        name=payload.name.strip(),
        device_code=f"KSK-{secrets.token_hex(4).upper()}",
        token_hash=hash_token(raw_token),
    )
    db.add(device)
    add_audit(
        db,
        request,
        "attendance.kiosk_registered",
        user=user,
        details={"device_code": device.device_code, "institution_id": str(institution.id)},
    )
    db.commit()
    db.refresh(device)
    device.institution = institution
    return KioskDeviceRegistered(**device_public(device).model_dump(), device_token=raw_token)


def list_devices(db: Session, user: User) -> list[KioskDevicePublic]:
    statement = (
        select(KioskDevice)
        .options(joinedload(KioskDevice.institution))
        .order_by(KioskDevice.created_at.desc())
    )
    if not user_has(user, Permission.PLATFORM_MANAGE):
        statement = statement.where(KioskDevice.institution_id == user.institution_id)
    return [device_public(device) for device in db.scalars(statement).unique()]


def revoke_device(db: Session, request: Request, user: User, device_id: UUID) -> KioskDevicePublic:
    device = db.scalar(
        select(KioskDevice)
        .where(KioskDevice.id == device_id)
        .options(joinedload(KioskDevice.institution))
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Kiosk device not found")
    if (
        not user_has(user, Permission.PLATFORM_MANAGE)
        and device.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=403, detail="You can revoke only your institution's kiosks")
    device.status = KioskDeviceStatus.REVOKED
    device.revoked_at = utc_now()
    add_audit(
        db,
        request,
        "attendance.kiosk_revoked",
        user=user,
        details={"device_code": device.device_code},
    )
    db.commit()
    return device_public(device)


def authenticate_device(db: Session, token: str | None) -> KioskDevice:
    if not token:
        raise HTTPException(status_code=401, detail="Kiosk device token is required")
    device = db.scalar(
        select(KioskDevice)
        .where(KioskDevice.token_hash == hash_token(token))
        .options(joinedload(KioskDevice.institution))
    )
    if device is None:
        raise HTTPException(status_code=401, detail="Kiosk device token is invalid")
    if device.status != KioskDeviceStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Kiosk device has been revoked")
    return device


def pair_session(
    db: Session, request: Request, device: KioskDevice, session_qr_payload: str
) -> KioskSessionPublic:
    token = session_qr_payload.removeprefix("NCCT-SESSION:")
    try:
        payload = decode_scoped_token(token, "attendance_session", require_expiry=True)
        item = load_session(db, UUID(payload["sub"]))
    except (TokenValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Session QR is invalid or expired") from exc
    if device.institution_id != item.programme.institution_id:
        raise HTTPException(status_code=403, detail="Kiosk is not registered to this institution")
    now = utc_now()
    if item.status != AttendanceSessionStatus.OPEN:
        raise HTTPException(status_code=409, detail="Attendance session is not open")
    if now < as_utc(item.starts_at) - SESSION_EARLY_WINDOW or now > as_utc(item.ends_at):
        raise HTTPException(
            status_code=409, detail="Attendance session is outside its active window"
        )
    device.last_seen_at = now
    add_audit(
        db,
        request,
        "attendance.kiosk_paired",
        details={"device_code": device.device_code, "session_id": str(item.id)},
    )
    db.commit()
    return KioskSessionPublic(
        session_id=item.id,
        title=item.title,
        programme_title=item.programme.title,
        programme_code=item.programme.code,
        batch_name=item.batch.name,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        offline_until=as_utc(item.ends_at) + SESSION_LATE_WINDOW,
    )


def decode_trainee(db: Session, qr_payload: str) -> User:
    token = qr_payload.removeprefix("NCCT-TRAINEE:")
    try:
        payload = decode_scoped_token(token, "trainee_identity")
        trainee_id = UUID(payload["sub"])
        version = int(payload["version"])
    except (TokenValidationError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Trainee QR is invalid") from exc
    trainee = db.scalar(
        select(User)
        .where(User.id == trainee_id)
        .options(
            joinedload(User.profile),
            joinedload(User.trainee_profile),
            selectinload(User.roles),
        )
    )
    if (
        trainee is None
        or trainee.status != AccountStatus.ACTIVE
        or trainee.trainee_profile is None
        or trainee.trainee_profile.qr_identity_version != version
        or RoleCode.TRAINEE not in role_codes(trainee)
    ):
        raise HTTPException(status_code=422, detail="Trainee QR is no longer valid")
    return trainee


def sync_one(
    db: Session,
    request: Request,
    device: KioskDevice,
    payload: OfflineCheckIn,
) -> CheckInSyncItem:
    existing = db.scalar(
        select(AttendanceCheckIn)
        .where(AttendanceCheckIn.idempotency_key == payload.idempotency_key)
        .options(
            joinedload(AttendanceCheckIn.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile)
        )
    )
    if existing is not None:
        return CheckInSyncItem(
            idempotency_key=payload.idempotency_key,
            result="duplicate",
            check_in_id=existing.id,
            trainee_name=display_name(existing.enrollment.trainee),
            detail="Attendance was already synchronized",
        )
    item = load_session(db, payload.session_id)
    if device.institution_id != item.programme.institution_id:
        raise HTTPException(status_code=403, detail="Kiosk is not registered for this programme")
    if item.status == AttendanceSessionStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Attendance session was cancelled")
    captured_at = as_utc(payload.captured_at)
    if (
        captured_at < as_utc(item.starts_at) - SESSION_EARLY_WINDOW
        or captured_at > as_utc(item.ends_at) + SESSION_LATE_WINDOW
    ):
        raise HTTPException(status_code=409, detail="Scan was captured outside the session window")
    trainee = decode_trainee(db, payload.trainee_qr)
    enrollment = db.scalar(
        select(ProgrammeEnrollment).where(
            ProgrammeEnrollment.trainee_id == trainee.id,
            ProgrammeEnrollment.programme_id == item.programme_id,
            ProgrammeEnrollment.batch_id == item.batch_id,
            ProgrammeEnrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]),
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=422, detail="Trainee is not enrolled in this session batch")
    duplicate = db.scalar(
        select(AttendanceCheckIn).where(
            AttendanceCheckIn.attendance_session_id == item.id,
            AttendanceCheckIn.enrollment_id == enrollment.id,
        )
    )
    if duplicate is not None:
        return CheckInSyncItem(
            idempotency_key=payload.idempotency_key,
            result="already_checked_in",
            check_in_id=duplicate.id,
            trainee_name=display_name(trainee),
            detail="Trainee is already checked in",
        )
    check_in = AttendanceCheckIn(
        attendance_session_id=item.id,
        enrollment_id=enrollment.id,
        kiosk_device_id=device.id,
        idempotency_key=payload.idempotency_key,
        captured_at=captured_at,
    )
    db.add(check_in)
    device.last_seen_at = utc_now()
    add_audit(
        db,
        request,
        "attendance.check_in_recorded",
        details={
            "session_id": str(item.id),
            "enrollment_id": str(enrollment.id),
            "device_code": device.device_code,
            "idempotency_key": str(payload.idempotency_key),
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(AttendanceCheckIn).where(
                AttendanceCheckIn.idempotency_key == payload.idempotency_key
            )
        )
        if replay is not None:
            return CheckInSyncItem(
                idempotency_key=payload.idempotency_key,
                result="duplicate",
                check_in_id=replay.id,
                trainee_name=display_name(trainee),
                detail="Attendance was already synchronized",
            )
        already_checked_in = db.scalar(
            select(AttendanceCheckIn).where(
                AttendanceCheckIn.attendance_session_id == item.id,
                AttendanceCheckIn.enrollment_id == enrollment.id,
            )
        )
        if already_checked_in is not None:
            return CheckInSyncItem(
                idempotency_key=payload.idempotency_key,
                result="already_checked_in",
                check_in_id=already_checked_in.id,
                trainee_name=display_name(trainee),
                detail="Trainee is already checked in",
            )
        raise HTTPException(status_code=409, detail="Attendance could not be synchronized") from exc
    return CheckInSyncItem(
        idempotency_key=payload.idempotency_key,
        result="created",
        check_in_id=check_in.id,
        trainee_name=display_name(trainee),
        detail="Attendance recorded",
    )


def sync_check_ins(
    db: Session,
    request: Request,
    device: KioskDevice,
    items: list[OfflineCheckIn],
) -> CheckInSyncResponse:
    results: list[CheckInSyncItem] = []
    for item in items:
        try:
            result = sync_one(db, request, device, item)
        except HTTPException as exc:
            db.rollback()
            result = CheckInSyncItem(
                idempotency_key=item.idempotency_key,
                result="rejected",
                detail=str(exc.detail),
            )
        results.append(result)
    return CheckInSyncResponse(
        items=results,
        accepted=sum(result.result == "created" for result in results),
        duplicates=sum(result.result in {"duplicate", "already_checked_in"} for result in results),
        rejected=sum(result.result == "rejected" for result in results),
    )


def correction_public(item: AttendanceCorrection) -> AttendanceCorrectionPublic:
    return AttendanceCorrectionPublic(
        id=item.id,
        attendance_session_id=item.attendance_session_id,
        session_title=item.attendance_session.title,
        enrollment_id=item.enrollment_id,
        trainee_name=display_name(item.enrollment.trainee),
        previous_status=item.previous_status,
        requested_status=item.requested_status,
        reason=item.reason,
        approval_status=item.approval_status,
        requested_by_name=display_name(item.requested_by),
        reviewed_by_name=display_name(item.reviewed_by) if item.reviewed_by else None,
        review_notes=item.review_notes,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
    )


def correction_options() -> tuple[Any, ...]:
    return (
        joinedload(AttendanceCorrection.attendance_session).joinedload(AttendanceSession.programme),
        joinedload(AttendanceCorrection.attendance_session).joinedload(AttendanceSession.batch),
        joinedload(AttendanceCorrection.enrollment)
        .joinedload(ProgrammeEnrollment.trainee)
        .joinedload(User.profile),
        joinedload(AttendanceCorrection.requested_by).joinedload(User.profile),
        joinedload(AttendanceCorrection.reviewed_by).joinedload(User.profile),
        joinedload(AttendanceCorrection.check_in),
    )


def request_correction(
    db: Session,
    request: Request,
    user: User,
    item: AttendanceSession,
    payload: AttendanceCorrectionCreate,
) -> AttendanceCorrection:
    ensure_session_manager(db, user, item)
    enrollment = db.get(ProgrammeEnrollment, payload.enrollment_id)
    if (
        enrollment is None
        or enrollment.programme_id != item.programme_id
        or enrollment.batch_id != item.batch_id
    ):
        raise HTTPException(status_code=422, detail="Enrollment is not part of this session")
    pending = db.scalar(
        select(AttendanceCorrection.id).where(
            AttendanceCorrection.attendance_session_id == item.id,
            AttendanceCorrection.enrollment_id == enrollment.id,
            AttendanceCorrection.approval_status == CorrectionStatus.PENDING,
        )
    )
    if pending is not None:
        raise HTTPException(status_code=409, detail="A correction is already awaiting approval")
    check_in = db.scalar(
        select(AttendanceCheckIn).where(
            AttendanceCheckIn.attendance_session_id == item.id,
            AttendanceCheckIn.enrollment_id == enrollment.id,
        )
    )
    correction = AttendanceCorrection(
        attendance_session_id=item.id,
        enrollment_id=enrollment.id,
        check_in_id=check_in.id if check_in else None,
        requested_by_id=user.id,
        previous_status=check_in.status if check_in else AttendanceStatus.ABSENT,
        requested_status=payload.requested_status,
        reason=payload.reason.strip(),
    )
    db.add(correction)
    add_audit(
        db,
        request,
        "attendance.correction_requested",
        user=user,
        details={"session_id": str(item.id), "enrollment_id": str(enrollment.id)},
    )
    db.commit()
    stored = db.scalar(
        select(AttendanceCorrection)
        .where(AttendanceCorrection.id == correction.id)
        .options(*correction_options())
    )
    if stored is None:
        raise HTTPException(status_code=500, detail="Attendance correction could not be loaded")
    return stored


def list_corrections(db: Session, user: User) -> list[AttendanceCorrectionPublic]:
    statement = (
        select(AttendanceCorrection)
        .options(*correction_options())
        .order_by(AttendanceCorrection.created_at.desc())
    )
    roles = role_codes(user)
    if not user_has(user, Permission.PLATFORM_MANAGE) and RoleCode.INSTITUTE_ADMIN in roles:
        statement = (
            statement.join(AttendanceCorrection.attendance_session)
            .join(AttendanceSession.programme)
            .where(Programme.institution_id == user.institution_id)
        )
    elif not user_has(user, Permission.PLATFORM_MANAGE) and RoleCode.TRAINER in roles:
        statement = (
            statement.join(AttendanceCorrection.attendance_session)
            .join(
                BatchTrainerAssignment,
                BatchTrainerAssignment.batch_id == AttendanceSession.batch_id,
            )
            .where(BatchTrainerAssignment.trainer_id == user.id)
        )
    return [correction_public(item) for item in db.scalars(statement).unique()]


def review_correction(
    db: Session,
    request: Request,
    user: User,
    correction_id: UUID,
    payload: AttendanceCorrectionReview,
) -> AttendanceCorrection:
    item = db.scalar(
        select(AttendanceCorrection)
        .where(AttendanceCorrection.id == correction_id)
        .options(*correction_options())
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Attendance correction not found")
    if item.approval_status != CorrectionStatus.PENDING:
        raise HTTPException(status_code=409, detail="Attendance correction is already reviewed")
    if item.requested_by_id == user.id:
        raise HTTPException(status_code=409, detail="Requester cannot approve their own correction")
    if (
        not user_has(user, Permission.PLATFORM_MANAGE)
        and user.institution_id != item.attendance_session.programme.institution_id
    ):
        raise HTTPException(status_code=403, detail="Correction belongs to another institution")
    item.approval_status = payload.decision
    item.reviewed_by_id = user.id
    item.review_notes = payload.review_notes
    item.reviewed_at = utc_now()
    if payload.decision == CorrectionStatus.APPROVED:
        check_in = item.check_in
        if check_in is None:
            check_in = AttendanceCheckIn(
                attendance_session_id=item.attendance_session_id,
                enrollment_id=item.enrollment_id,
                created_by_id=user.id,
                idempotency_key=uuid4(),
                status=item.requested_status,
                source=AttendanceSource.MANUAL,
                captured_at=utc_now(),
            )
            db.add(check_in)
            db.flush()
            item.check_in_id = check_in.id
        else:
            check_in.status = item.requested_status
    add_audit(
        db,
        request,
        "attendance.correction_reviewed",
        user=user,
        details={"correction_id": str(item.id), "decision": payload.decision.value},
    )
    db.commit()
    stored = db.scalar(
        select(AttendanceCorrection)
        .where(AttendanceCorrection.id == item.id)
        .options(*correction_options())
        .execution_options(populate_existing=True)
    )
    if stored is None:
        raise HTTPException(status_code=500, detail="Attendance correction could not be loaded")
    return stored


def attendance_report(db: Session, user: User, item: AttendanceSession) -> AttendanceReportPublic:
    ensure_session_manager(db, user, item)
    enrollments = list(
        db.scalars(
            select(ProgrammeEnrollment)
            .where(
                ProgrammeEnrollment.programme_id == item.programme_id,
                ProgrammeEnrollment.batch_id == item.batch_id,
                ProgrammeEnrollment.status.in_(
                    [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
                ),
            )
            .options(joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile))
        ).unique()
    )
    check_ins = {
        check_in.enrollment_id: check_in
        for check_in in db.scalars(
            select(AttendanceCheckIn)
            .where(AttendanceCheckIn.attendance_session_id == item.id)
            .options(joinedload(AttendanceCheckIn.kiosk_device))
        ).unique()
    }
    trainee_ids = [enrollment.trainee_id for enrollment in enrollments]
    biometric_trainee_ids = (
        set(
            db.scalars(
                select(BiometricEnrollment.trainee_id).where(
                    BiometricEnrollment.trainee_id.in_(trainee_ids)
                )
            )
        )
        if trainee_ids
        else set()
    )
    rows: list[AttendanceReportRow] = []
    for enrollment in enrollments:
        check_in = check_ins.get(enrollment.id)
        rows.append(
            AttendanceReportRow(
                enrollment_id=enrollment.id,
                trainee_id=enrollment.trainee_id,
                trainee_name=display_name(enrollment.trainee),
                trainee_email=enrollment.trainee.email,
                status=check_in.status if check_in else AttendanceStatus.ABSENT,
                captured_at=check_in.captured_at if check_in else None,
                checked_in_at=check_in.checked_in_at if check_in else None,
                device_code=(
                    check_in.kiosk_device.device_code
                    if check_in and check_in.kiosk_device
                    else None
                ),
                source=check_in.source.value if check_in else None,
                biometric_enrolled=enrollment.trainee_id in biometric_trainee_ids,
            )
        )
    present_count = sum(row.status == AttendanceStatus.PRESENT for row in rows)
    absent_count = sum(row.status == AttendanceStatus.ABSENT for row in rows)
    excused_count = sum(row.status == AttendanceStatus.EXCUSED for row in rows)
    expected = len(rows)
    return AttendanceReportPublic(
        session=session_public(item),
        expected_count=expected,
        present_count=present_count,
        absent_count=absent_count,
        excused_count=excused_count,
        attendance_percent=round((present_count / expected * 100) if expected else 0, 1),
        rows=rows,
    )
