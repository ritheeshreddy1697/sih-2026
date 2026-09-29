from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.biometric_crypto import decrypt_embedding, encrypt_embedding
from app.core.config import settings
from app.core.permissions import Permission
from app.models import (
    AccountStatus,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    BiometricChallenge,
    BiometricChallengePurpose,
    BiometricChallengeType,
    BiometricEnrollment,
    BiometricVerification,
    BiometricVerificationStatus,
    ConsentRecord,
    CorrectionStatus,
    EnrollmentStatus,
    KioskDevice,
    Programme,
    ProgrammeEnrollment,
    RoleCode,
    User,
)
from app.schemas.attendance import (
    BiometricChallengePublic,
    BiometricEnrollmentPublic,
    BiometricReviewRequest,
    BiometricVerificationPublic,
    KioskBiometricChallengeCreate,
)
from app.services import attendance as attendance_service
from app.services.auth import get_client_details
from app.services.face_verification import (
    DemoFaceVerificationProvider,
    FaceCaptureError,
    FaceVerificationProvider,
    LivenessCheckFailed,
)

BIOMETRIC_CONSENT_VERSION = "biometric-attendance-v1"
PRIVACY_NOTICE = (
    "Face verification is optional. Three camera frames are processed for a one-to-one match, "
    "discarded after processing, and never used to identify unknown people. QR attendance remains "
    "available. You may withdraw consent and delete the protected template at any time."
)
CHALLENGE_INSTRUCTION = "Look at the camera, then slowly turn your head to one side and back."


def face_provider() -> FaceVerificationProvider:
    if settings.face_verification_provider == "demo":
        return DemoFaceVerificationProvider(
            liveness_threshold=settings.biometric_liveness_threshold
        )
    raise HTTPException(
        status_code=503,
        detail="The configured production face-verification provider is unavailable",
    )


def _ensure_enabled() -> None:
    if not settings.biometric_enabled:
        raise HTTPException(status_code=503, detail="Biometric attendance is disabled")


def _provider_mode(provider: FaceVerificationProvider) -> str:
    return "demonstration" if provider.is_demo else "production"


def _identity_code(user_id: UUID) -> str:
    return f"NCCT-{str(user_id).split('-')[0].upper()}"


def _active_enrollment(db: Session, trainee_id: UUID) -> BiometricEnrollment | None:
    return db.scalar(
        select(BiometricEnrollment).where(BiometricEnrollment.trainee_id == trainee_id)
    )


def enrollment_public(db: Session, trainee: User) -> BiometricEnrollmentPublic:
    provider = face_provider() if settings.biometric_enabled else None
    enrollment = _active_enrollment(db, trainee.id)
    return BiometricEnrollmentPublic(
        enrolled=enrollment is not None,
        enrolled_at=enrollment.created_at if enrollment else None,
        provider_name=(provider.name if provider else settings.face_verification_provider),
        provider_mode=(_provider_mode(provider) if provider else "disabled"),
        is_demo=bool(provider and provider.is_demo),
        consent_version=BIOMETRIC_CONSENT_VERSION,
        privacy_notice=PRIVACY_NOTICE,
    )


def issue_enrollment_challenge(
    db: Session,
    request: Request,
    trainee: User,
) -> BiometricChallengePublic:
    _ensure_enabled()
    if RoleCode.TRAINEE not in attendance_service.role_codes(trainee):
        raise HTTPException(status_code=403, detail="A trainee account is required")
    provider = face_provider()
    now = attendance_service.utc_now()
    challenge = BiometricChallenge(
        purpose=BiometricChallengePurpose.ENROLLMENT,
        challenge_type=BiometricChallengeType.TURN_HEAD,
        trainee_id=trainee.id,
        expires_at=now + timedelta(seconds=settings.biometric_challenge_expire_seconds),
    )
    db.add(challenge)
    attendance_service.add_audit(
        db,
        request,
        "biometric.enrollment_challenge_issued",
        user=trainee,
        details={"provider": provider.name, "demo_mode": provider.is_demo},
    )
    db.commit()
    return BiometricChallengePublic(
        id=challenge.id,
        challenge_type=challenge.challenge_type,
        instruction=CHALLENGE_INSTRUCTION,
        expires_at=challenge.expires_at,
        trainee_name=attendance_service.display_name(trainee),
        provider_mode=_provider_mode(provider),
        is_demo=provider.is_demo,
    )


def _load_challenge(
    db: Session,
    challenge_id: UUID,
    purpose: BiometricChallengePurpose,
    *,
    allow_used: bool = False,
    for_update: bool = False,
) -> BiometricChallenge:
    statement = (
        select(BiometricChallenge)
        .where(
            BiometricChallenge.id == challenge_id,
            BiometricChallenge.purpose == purpose,
        )
        .options(joinedload(BiometricChallenge.trainee).joinedload(User.profile))
    )
    if for_update:
        statement = statement.with_for_update(of=BiometricChallenge)
    challenge = db.scalar(statement)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Biometric challenge not found")
    if challenge.used_at is not None and not allow_used:
        raise HTTPException(status_code=409, detail="Biometric challenge was already used")
    if attendance_service.utc_now() > attendance_service.as_utc(challenge.expires_at):
        raise HTTPException(status_code=410, detail="Biometric challenge expired")
    return challenge


def enroll(
    db: Session,
    request: Request,
    trainee: User,
    *,
    challenge_id: UUID,
    consent_granted: bool,
    frames: list[bytes],
) -> BiometricEnrollmentPublic:
    _ensure_enabled()
    if not consent_granted:
        raise HTTPException(
            status_code=422,
            detail="Explicit biometric enrolment consent is required",
        )
    challenge = _load_challenge(
        db,
        challenge_id,
        BiometricChallengePurpose.ENROLLMENT,
        for_update=True,
    )
    if challenge.trainee_id != trainee.id:
        raise HTTPException(status_code=403, detail="This challenge belongs to another trainee")

    provider = face_provider()
    challenge.used_at = attendance_service.utc_now()
    try:
        analysis = provider.analyze(frames, challenge.challenge_type)
    except FaceCaptureError as exc:
        attendance_service.add_audit(
            db,
            request,
            "biometric.enrollment_rejected",
            user=trainee,
            success=False,
            details={"reason": exc.code, "provider": provider.name},
        )
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ip_address = get_client_details(request)[0]
    consent = ConsentRecord(
        user_id=trainee.id,
        consent_type="biometric_attendance_face_verification",
        version=BIOMETRIC_CONSENT_VERSION,
        granted=True,
        ip_address=ip_address,
    )
    db.add(consent)
    db.flush()
    protected = encrypt_embedding(
        analysis.embedding,
        trainee_id=trainee.id,
        provider_name=provider.name,
        model_version=provider.model_version,
    )
    enrollment = _active_enrollment(db, trainee.id)
    if enrollment is None:
        enrollment = BiometricEnrollment(trainee_id=trainee.id)
        db.add(enrollment)
    enrollment.consent_record_id = consent.id
    enrollment.encrypted_embedding = protected.ciphertext
    enrollment.encryption_nonce = protected.nonce
    enrollment.encryption_key_version = protected.key_version
    enrollment.provider_name = provider.name
    enrollment.model_version = provider.model_version
    enrollment.liveness_score = analysis.liveness_score
    attendance_service.add_audit(
        db,
        request,
        "biometric.consent_granted",
        user=trainee,
        details={"consent_version": BIOMETRIC_CONSENT_VERSION},
    )
    attendance_service.add_audit(
        db,
        request,
        "biometric.enrolled",
        user=trainee,
        details={
            "provider": provider.name,
            "demo_mode": provider.is_demo,
            "liveness_passed": True,
        },
    )
    db.commit()
    return enrollment_public(db, trainee)


def _ensure_admin_scope(actor: User, institution_id: UUID) -> None:
    if attendance_service.user_has(actor, Permission.PLATFORM_MANAGE):
        return
    if (
        RoleCode.INSTITUTE_ADMIN in attendance_service.role_codes(actor)
        and actor.institution_id == institution_id
    ):
        return
    raise HTTPException(status_code=403, detail="Biometric administration is outside your scope")


def delete_enrollment(
    db: Session,
    request: Request,
    actor: User,
    trainee: User,
) -> str:
    if actor.id != trainee.id:
        if trainee.institution_id is None:
            raise HTTPException(status_code=403, detail="Trainee has no institution scope")
        _ensure_admin_scope(actor, trainee.institution_id)
    enrollment = _active_enrollment(db, trainee.id)
    if enrollment is None:
        return "No biometric template is enrolled."

    now = attendance_service.utc_now()
    db.delete(enrollment)
    db.execute(
        update(BiometricChallenge)
        .where(
            BiometricChallenge.trainee_id == trainee.id,
            BiometricChallenge.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.add(
        ConsentRecord(
            user_id=trainee.id,
            consent_type="biometric_attendance_face_verification",
            version=BIOMETRIC_CONSENT_VERSION,
            granted=False,
            recorded_at=now,
            withdrawn_at=now,
            ip_address=get_client_details(request)[0],
        )
    )
    attendance_service.add_audit(
        db,
        request,
        "biometric.consent_withdrawn",
        user=actor,
        details={"trainee_id": str(trainee.id)},
    )
    attendance_service.add_audit(
        db,
        request,
        "biometric.template_deleted",
        user=actor,
        details={"trainee_id": str(trainee.id), "self_service": actor.id == trainee.id},
    )
    db.commit()
    return "Biometric template deleted. QR attendance remains available."


def load_trainee_for_admin(db: Session, trainee_id: UUID) -> User:
    trainee = db.scalar(
        select(User)
        .where(User.id == trainee_id)
        .options(joinedload(User.profile), selectinload(User.roles))
    )
    if trainee is None or RoleCode.TRAINEE not in attendance_service.role_codes(trainee):
        raise HTTPException(status_code=404, detail="Trainee not found")
    return trainee


def issue_kiosk_challenge(
    db: Session,
    request: Request,
    device: KioskDevice,
    payload: KioskBiometricChallengeCreate,
) -> BiometricChallengePublic:
    _ensure_enabled()
    provider = face_provider()
    session_item = attendance_service.load_session(db, payload.session_id)
    now = attendance_service.utc_now()
    if device.institution_id != session_item.programme.institution_id:
        raise HTTPException(status_code=403, detail="Kiosk is not registered for this programme")
    if session_item.status != AttendanceSessionStatus.OPEN or not (
        attendance_service.as_utc(session_item.starts_at) - attendance_service.SESSION_EARLY_WINDOW
        <= now
        <= attendance_service.as_utc(session_item.ends_at)
    ):
        raise HTTPException(status_code=409, detail="Attendance session is not active")

    enrollments = list(
        db.scalars(
            select(ProgrammeEnrollment)
            .where(
                ProgrammeEnrollment.programme_id == session_item.programme_id,
                ProgrammeEnrollment.batch_id == session_item.batch_id,
                ProgrammeEnrollment.status.in_(
                    [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
                ),
            )
            .options(
                joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile),
                joinedload(ProgrammeEnrollment.trainee).selectinload(User.roles),
            )
        ).unique()
    )
    normalized_code = payload.identity_code.strip().upper()
    matches = [
        item
        for item in enrollments
        if _identity_code(item.trainee_id) == normalized_code
        and item.trainee.status == AccountStatus.ACTIVE
        and RoleCode.TRAINEE in attendance_service.role_codes(item.trainee)
    ]
    if len(matches) != 1 or _active_enrollment(db, matches[0].trainee_id) is None:
        attendance_service.add_audit(
            db,
            request,
            "biometric.identity_claim_rejected",
            success=False,
            details={
                "session_id": str(session_item.id),
                "device_code": device.device_code,
            },
        )
        db.commit()
        raise HTTPException(
            status_code=422,
            detail=(
                "Identity is not eligible for face verification. "
                "Use QR attendance or ask staff."
            ),
        )
    trainee = matches[0].trainee
    challenge = BiometricChallenge(
        purpose=BiometricChallengePurpose.ATTENDANCE,
        challenge_type=BiometricChallengeType.TURN_HEAD,
        trainee_id=trainee.id,
        attendance_session_id=session_item.id,
        kiosk_device_id=device.id,
        expires_at=now + timedelta(seconds=settings.biometric_challenge_expire_seconds),
    )
    db.add(challenge)
    attendance_service.add_audit(
        db,
        request,
        "biometric.verification_challenge_issued",
        details={
            "trainee_id": str(trainee.id),
            "session_id": str(session_item.id),
            "device_code": device.device_code,
        },
    )
    db.commit()
    return BiometricChallengePublic(
        id=challenge.id,
        challenge_type=challenge.challenge_type,
        instruction=CHALLENGE_INSTRUCTION,
        expires_at=challenge.expires_at,
        trainee_name=attendance_service.display_name(trainee),
        provider_mode=_provider_mode(provider),
        is_demo=provider.is_demo,
    )


def _verification_options() -> tuple[Any, ...]:
    return (
        joinedload(BiometricVerification.trainee).joinedload(User.profile),
        joinedload(BiometricVerification.attendance_session).joinedload(
            AttendanceSession.programme
        ),
        joinedload(BiometricVerification.check_in),
        joinedload(BiometricVerification.reviewed_by).joinedload(User.profile),
    )


def _verification_detail(item: BiometricVerification) -> str:
    if item.status == BiometricVerificationStatus.VERIFIED:
        return "Attendance was verified and recorded."
    if item.status == BiometricVerificationStatus.MANUAL_REVIEW:
        if item.review_status == CorrectionStatus.APPROVED:
            return "Attendance was approved after an in-person administrator review."
        if item.review_status == CorrectionStatus.REJECTED:
            return "The administrator rejected this uncertain match."
        return "The match was uncertain. Attendance was not recorded and awaits manual review."
    if item.failure_reason == "liveness_failed":
        return "Liveness could not be confirmed. Attendance was not recorded."
    return "The claimed trainee could not be verified. Attendance was not recorded."


def verification_public(item: BiometricVerification) -> BiometricVerificationPublic:
    return BiometricVerificationPublic(
        id=item.id,
        trainee_id=item.trainee_id,
        trainee_name=attendance_service.display_name(item.trainee),
        session_id=item.attendance_session_id,
        session_title=item.attendance_session.title,
        status=item.status,
        review_status=item.review_status,
        confidence=round(item.confidence, 3),
        threshold=round(item.match_threshold, 3),
        liveness_score=round(item.liveness_score, 3),
        attendance_recorded=item.check_in_id is not None,
        check_in_id=item.check_in_id,
        detail=_verification_detail(item),
        captured_at=item.captured_at,
        created_at=item.created_at,
    )


def _load_verification(
    db: Session, verification_id: UUID, *, for_update: bool = False
) -> BiometricVerification:
    statement = (
        select(BiometricVerification)
        .where(BiometricVerification.id == verification_id)
        .options(*_verification_options())
    )
    if for_update:
        statement = statement.with_for_update(of=BiometricVerification)
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(status_code=404, detail="Biometric verification not found")
    return item


def verify_kiosk_capture(
    db: Session,
    request: Request,
    device: KioskDevice,
    *,
    challenge_id: UUID,
    idempotency_key: UUID,
    captured_at: datetime,
    frames: list[bytes],
) -> BiometricVerificationPublic:
    _ensure_enabled()
    existing = db.scalar(
        select(BiometricVerification)
        .where(BiometricVerification.idempotency_key == idempotency_key)
        .options(*_verification_options())
    )
    if existing is not None:
        return verification_public(existing)

    challenge = _load_challenge(
        db,
        challenge_id,
        BiometricChallengePurpose.ATTENDANCE,
        allow_used=True,
        for_update=True,
    )
    if challenge.used_at is not None:
        replay = db.scalar(
            select(BiometricVerification)
            .where(BiometricVerification.idempotency_key == idempotency_key)
            .options(*_verification_options())
        )
        if replay is not None:
            return verification_public(replay)
        raise HTTPException(status_code=409, detail="Biometric challenge was already used")
    if challenge.kiosk_device_id != device.id or challenge.attendance_session_id is None:
        raise HTTPException(status_code=403, detail="Challenge does not belong to this kiosk")
    session_item = attendance_service.load_session(db, challenge.attendance_session_id)
    if device.institution_id != session_item.programme.institution_id:
        raise HTTPException(status_code=403, detail="Kiosk is not registered for this programme")
    captured = attendance_service.as_utc(captured_at)
    if session_item.status != AttendanceSessionStatus.OPEN or not (
        attendance_service.as_utc(session_item.starts_at) - attendance_service.SESSION_EARLY_WINDOW
        <= captured
        <= attendance_service.as_utc(session_item.ends_at)
    ):
        raise HTTPException(status_code=409, detail="Capture is outside the active session window")

    programme_enrollment = db.scalar(
        select(ProgrammeEnrollment).where(
            ProgrammeEnrollment.trainee_id == challenge.trainee_id,
            ProgrammeEnrollment.programme_id == session_item.programme_id,
            ProgrammeEnrollment.batch_id == session_item.batch_id,
            ProgrammeEnrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]),
        ).with_for_update()
    )
    biometric_enrollment = _active_enrollment(db, challenge.trainee_id)
    if programme_enrollment is None or biometric_enrollment is None:
        raise HTTPException(
            status_code=422, detail="Trainee is no longer eligible for verification"
        )

    provider = face_provider()
    challenge.used_at = attendance_service.utc_now()
    try:
        analysis = provider.analyze(frames, challenge.challenge_type)
    except FaceCaptureError as exc:
        liveness = exc.score if isinstance(exc, LivenessCheckFailed) else 0.0
        verification = BiometricVerification(
            challenge=challenge,
            biometric_enrollment=biometric_enrollment,
            trainee=challenge.trainee,
            programme_enrollment=programme_enrollment,
            attendance_session=session_item,
            kiosk_device=device,
            idempotency_key=idempotency_key,
            provider_name=provider.name,
            model_version=provider.model_version,
            confidence=0.0,
            liveness_score=liveness,
            match_threshold=settings.biometric_match_threshold,
            status=BiometricVerificationStatus.REJECTED,
            failure_reason=exc.code,
            captured_at=captured,
        )
        db.add(verification)
        attendance_service.add_audit(
            db,
            request,
            "biometric.verification_rejected",
            success=False,
            details={
                "trainee_id": str(challenge.trainee_id),
                "session_id": str(session_item.id),
                "reason": exc.code,
                "device_code": device.device_code,
            },
        )
        db.commit()
        return verification_public(verification)

    if (
        biometric_enrollment.provider_name != provider.name
        or biometric_enrollment.model_version != provider.model_version
    ):
        attendance_service.add_audit(
            db,
            request,
            "biometric.template_incompatible",
            success=False,
            details={"trainee_id": str(challenge.trainee_id)},
        )
        db.commit()
        raise HTTPException(status_code=409, detail="Face re-enrolment is required")
    try:
        enrolled_embedding = decrypt_embedding(
            biometric_enrollment.encrypted_embedding,
            biometric_enrollment.encryption_nonce,
            trainee_id=challenge.trainee_id,
            provider_name=provider.name,
            model_version=provider.model_version,
            key_version=biometric_enrollment.encryption_key_version,
        )
    except RuntimeError as exc:
        attendance_service.add_audit(
            db,
            request,
            "biometric.template_decryption_failed",
            success=False,
            details={"trainee_id": str(challenge.trainee_id)},
        )
        db.commit()
        raise HTTPException(
            status_code=503, detail="Face verification is temporarily unavailable"
        ) from exc

    confidence = provider.compare(enrolled_embedding, analysis.embedding)
    if confidence >= settings.biometric_match_threshold:
        status = BiometricVerificationStatus.VERIFIED
        review_status = None
        failure_reason = None
    elif confidence >= settings.biometric_manual_review_threshold:
        status = BiometricVerificationStatus.MANUAL_REVIEW
        review_status = CorrectionStatus.PENDING
        failure_reason = "uncertain_match"
    else:
        status = BiometricVerificationStatus.REJECTED
        review_status = None
        failure_reason = "face_mismatch"

    check_in = None
    if status == BiometricVerificationStatus.VERIFIED:
        check_in = db.scalar(
            select(AttendanceCheckIn).where(
                AttendanceCheckIn.attendance_session_id == session_item.id,
                AttendanceCheckIn.enrollment_id == programme_enrollment.id,
            )
        )
        if check_in is None:
            check_in = AttendanceCheckIn(
                attendance_session_id=session_item.id,
                enrollment_id=programme_enrollment.id,
                kiosk_device_id=device.id,
                idempotency_key=idempotency_key,
                source=AttendanceSource.BIOMETRIC,
                captured_at=captured,
            )
            db.add(check_in)
            db.flush()
    verification = BiometricVerification(
        challenge=challenge,
        biometric_enrollment=biometric_enrollment,
        trainee=challenge.trainee,
        programme_enrollment=programme_enrollment,
        attendance_session=session_item,
        kiosk_device=device,
        check_in=check_in,
        idempotency_key=idempotency_key,
        provider_name=provider.name,
        model_version=provider.model_version,
        confidence=confidence,
        liveness_score=analysis.liveness_score,
        match_threshold=settings.biometric_match_threshold,
        status=status,
        failure_reason=failure_reason,
        review_status=review_status,
        captured_at=captured,
    )
    db.add(verification)
    attendance_service.add_audit(
        db,
        request,
        f"biometric.verification_{status.value}",
        success=status != BiometricVerificationStatus.REJECTED,
        details={
            "trainee_id": str(challenge.trainee_id),
            "session_id": str(session_item.id),
            "device_code": device.device_code,
            "confidence": round(confidence, 3),
            "threshold": settings.biometric_match_threshold,
            "attendance_recorded": check_in is not None,
        },
    )
    db.commit()
    return verification_public(verification)


def list_manual_reviews(db: Session, actor: User) -> list[BiometricVerificationPublic]:
    statement = (
        select(BiometricVerification)
        .where(BiometricVerification.status == BiometricVerificationStatus.MANUAL_REVIEW)
        .options(*_verification_options())
        .order_by(BiometricVerification.created_at.desc())
    )
    if not attendance_service.user_has(actor, Permission.PLATFORM_MANAGE):
        if RoleCode.INSTITUTE_ADMIN not in attendance_service.role_codes(actor):
            raise HTTPException(status_code=403, detail="Biometric review is not permitted")
        statement = statement.join(BiometricVerification.attendance_session).join(
            AttendanceSession.programme
        ).where(Programme.institution_id == actor.institution_id)
    return [verification_public(item) for item in db.scalars(statement).unique()]


def review_verification(
    db: Session,
    request: Request,
    actor: User,
    verification_id: UUID,
    payload: BiometricReviewRequest,
) -> BiometricVerificationPublic:
    item = _load_verification(db, verification_id, for_update=True)
    _ensure_admin_scope(actor, item.attendance_session.programme.institution_id)
    if actor.id == item.trainee_id:
        raise HTTPException(status_code=403, detail="You cannot review your own verification")
    if (
        item.status != BiometricVerificationStatus.MANUAL_REVIEW
        or item.review_status != CorrectionStatus.PENDING
    ):
        raise HTTPException(status_code=409, detail="Verification is not awaiting review")

    if payload.decision == CorrectionStatus.APPROVED:
        check_in = db.scalar(
            select(AttendanceCheckIn).where(
                AttendanceCheckIn.attendance_session_id == item.attendance_session_id,
                AttendanceCheckIn.enrollment_id == item.programme_enrollment_id,
            )
        )
        if check_in is None:
            check_in = AttendanceCheckIn(
                attendance_session_id=item.attendance_session_id,
                enrollment_id=item.programme_enrollment_id,
                kiosk_device_id=item.kiosk_device_id,
                created_by_id=actor.id,
                idempotency_key=uuid4(),
                source=AttendanceSource.BIOMETRIC_MANUAL,
                captured_at=item.captured_at,
            )
            db.add(check_in)
            db.flush()
        item.check_in = check_in
    item.review_status = payload.decision
    item.review_notes = payload.review_notes.strip()
    item.reviewed_by_id = actor.id
    item.reviewed_at = attendance_service.utc_now()
    attendance_service.add_audit(
        db,
        request,
        f"biometric.manual_review_{payload.decision.value}",
        user=actor,
        details={
            "verification_id": str(item.id),
            "trainee_id": str(item.trainee_id),
            "session_id": str(item.attendance_session_id),
            "attendance_recorded": item.check_in is not None,
        },
    )
    db.commit()
    return verification_public(_load_verification(db, item.id))
