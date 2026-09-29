from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import qrcode
from fastapi import HTTPException, Request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.permissions import Permission, has_permission
from app.models import (
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentType,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceStatus,
    AuditLog,
    CertificatePolicy,
    CertificateState,
    Course,
    CourseModule,
    CourseSection,
    DigitalCertificate,
    EnrollmentStatus,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonProgress,
    Programme,
    ProgrammeEnrollment,
    RoleCode,
    TraineeProfile,
    User,
    VerifiedEmploymentSkill,
)
from app.schemas.certificate import (
    CertificateAuditEvent,
    CertificateCandidatePublic,
    CertificateMetrics,
    CertificatePolicyPublic,
    CertificatePolicyUpdate,
    CertificateRecordPublic,
    CertificateVerificationPublic,
    EligibilityMetrics,
    SkillWalletPublic,
)
from app.services.auth import get_client_details


@dataclass(frozen=True)
class EligibilityResult:
    metrics: EligibilityMetrics
    eligible: bool
    reasons: list[str]


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def display_name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def role_codes(user: User) -> set[RoleCode]:
    return {role.code for role in user.roles}


def verification_url(token: str) -> str:
    return f"{settings.frontend_public_url.rstrip('/')}/verify/certificate/{token}"


def add_audit(
    db: Session,
    request: Request,
    event_type: str,
    *,
    user: User,
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


def ensure_programme_manager(user: User, programme: Programme) -> None:
    roles = role_codes(user)
    if has_permission(roles, Permission.PLATFORM_MANAGE):
        return
    if RoleCode.INSTITUTE_ADMIN in roles and user.institution_id == programme.institution_id:
        return
    raise HTTPException(
        status_code=403,
        detail="You can manage certificates only for your institution's programmes",
    )


def enrollment_options() -> tuple[Any, ...]:
    return (
        joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile),
        joinedload(ProgrammeEnrollment.programme).joinedload(Programme.institution),
        joinedload(ProgrammeEnrollment.batch),
    )


def load_enrollment(db: Session, enrollment_id: UUID) -> ProgrammeEnrollment:
    enrollment = db.scalar(
        select(ProgrammeEnrollment)
        .where(ProgrammeEnrollment.id == enrollment_id)
        .options(*enrollment_options())
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Programme enrollment not found")
    return enrollment


def load_policy(db: Session, programme_id: UUID) -> CertificatePolicy | None:
    return db.scalar(
        select(CertificatePolicy)
        .where(CertificatePolicy.programme_id == programme_id)
        .options(joinedload(CertificatePolicy.configured_by).joinedload(User.profile))
    )


def policy_public(policy: CertificatePolicy) -> CertificatePolicyPublic:
    return CertificatePolicyPublic(
        id=policy.id,
        programme_id=policy.programme_id,
        configured_by_name=display_name(policy.configured_by),
        certificate_title=policy.certificate_title,
        minimum_course_completion_percent=policy.minimum_course_completion_percent,
        minimum_attendance_percent=policy.minimum_attendance_percent,
        minimum_assessment_score_percent=policy.minimum_assessment_score_percent,
        validity_days=policy.validity_days,
        is_active=policy.is_active,
        updated_at=policy.updated_at,
    )


def get_policy(db: Session, user: User, programme_id: UUID) -> CertificatePolicyPublic | None:
    programme = db.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    ensure_programme_manager(user, programme)
    policy = load_policy(db, programme_id)
    return policy_public(policy) if policy else None


def upsert_policy(
    db: Session,
    request: Request,
    user: User,
    programme_id: UUID,
    payload: CertificatePolicyUpdate,
) -> CertificatePolicyPublic:
    programme = db.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    ensure_programme_manager(user, programme)
    policy = load_policy(db, programme_id)
    created = policy is None
    if policy is None:
        policy = CertificatePolicy(programme_id=programme.id, configured_by_id=user.id)
        db.add(policy)
    for field, value in payload.model_dump().items():
        setattr(policy, field, value)
    policy.configured_by_id = user.id
    add_audit(
        db,
        request,
        "certificate.policy_created" if created else "certificate.policy_updated",
        user=user,
        details={
            "programme_id": str(programme.id),
            "minimum_course_completion_percent": payload.minimum_course_completion_percent,
            "minimum_attendance_percent": payload.minimum_attendance_percent,
            "minimum_assessment_score_percent": payload.minimum_assessment_score_percent,
            "validity_days": payload.validity_days,
            "is_active": payload.is_active,
        },
    )
    db.commit()
    refreshed = load_policy(db, programme_id)
    assert refreshed is not None
    return policy_public(refreshed)


def calculate_eligibility(
    db: Session,
    enrollment: ProgrammeEnrollment,
    policy: CertificatePolicy,
) -> EligibilityResult:
    course = db.scalar(select(Course).where(Course.programme_id == enrollment.programme_id))
    required_lessons = 0
    completed_lessons = 0
    assessment_score = 0.0
    if course is not None:
        lesson_ids = list(
            db.scalars(
                select(Lesson.id)
                .join(CourseModule, CourseModule.id == Lesson.module_id)
                .join(CourseSection, CourseSection.id == CourseModule.section_id)
                .where(CourseSection.course_id == course.id, Lesson.is_required.is_(True))
            )
        )
        required_lessons = len(lesson_ids)
        if lesson_ids:
            completed_lessons = int(
                db.scalar(
                    select(func.count(LessonProgress.id)).where(
                        LessonProgress.enrollment_id == enrollment.id,
                        LessonProgress.lesson_id.in_(lesson_ids),
                        LessonProgress.status == LearningProgressStatus.COMPLETED,
                    )
                )
                or 0
            )
        best_score = db.scalar(
            select(func.max(AssessmentAttempt.score_percent))
            .join(
                LearnerAssessment,
                LearnerAssessment.id == AssessmentAttempt.assessment_id,
            )
            .where(
                LearnerAssessment.course_id == course.id,
                LearnerAssessment.assessment_type == AssessmentType.POST_TRAINING,
                AssessmentAttempt.enrollment_id == enrollment.id,
                AssessmentAttempt.status == AssessmentAttemptStatus.SUBMITTED,
            )
        )
        assessment_score = float(best_score or 0)

    course_completion = (
        round(completed_lessons / required_lessons * 100, 2) if required_lessons else 0.0
    )
    session_ids: list[UUID] = []
    if enrollment.batch_id is not None:
        session_ids = list(
            db.scalars(
                select(AttendanceSession.id).where(
                    AttendanceSession.programme_id == enrollment.programme_id,
                    AttendanceSession.batch_id == enrollment.batch_id,
                    AttendanceSession.status != AttendanceSessionStatus.CANCELLED,
                    AttendanceSession.ends_at <= utc_now(),
                )
            )
        )
    attended_sessions = 0
    if session_ids:
        attended_sessions = int(
            db.scalar(
                select(func.count(AttendanceCheckIn.id)).where(
                    AttendanceCheckIn.enrollment_id == enrollment.id,
                    AttendanceCheckIn.attendance_session_id.in_(session_ids),
                    AttendanceCheckIn.status == AttendanceStatus.PRESENT,
                )
            )
            or 0
        )
    attendance_percent = (
        round(attended_sessions / len(session_ids) * 100, 2) if session_ids else 0.0
    )
    metrics = EligibilityMetrics(
        course_completion_percent=course_completion,
        attendance_percent=attendance_percent,
        assessment_score_percent=round(assessment_score, 2),
        required_lessons=required_lessons,
        completed_lessons=completed_lessons,
        attendance_sessions=len(session_ids),
        attended_sessions=attended_sessions,
    )
    reasons: list[str] = []
    if not policy.is_active:
        reasons.append("Certificate issuance is disabled for this programme")
    if enrollment.status == EnrollmentStatus.WITHDRAWN:
        reasons.append("The trainee has withdrawn from this programme")
    if course_completion < policy.minimum_course_completion_percent:
        reasons.append(
            f"Course completion is {course_completion:.0f}%; "
            f"{policy.minimum_course_completion_percent:.0f}% is required"
        )
    if attendance_percent < policy.minimum_attendance_percent:
        reasons.append(
            f"Attendance is {attendance_percent:.0f}%; "
            f"{policy.minimum_attendance_percent:.0f}% is required"
        )
    if assessment_score < policy.minimum_assessment_score_percent:
        reasons.append(
            f"Post-training assessment score is {assessment_score:.0f}%; "
            f"{policy.minimum_assessment_score_percent:.0f}% is required"
        )
    return EligibilityResult(metrics=metrics, eligible=not reasons, reasons=reasons)


def _pdf_font() -> str:
    fonts = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    )
    for font_path in fonts:
        if Path(font_path).is_file():
            try:
                pdfmetrics.registerFont(TTFont("CertificateSans", font_path))
            except KeyError:
                pass
            return "CertificateSans"
    return "Helvetica"


def _fit_text(value: str, limit: int = 84) -> str:
    return value if len(value) <= limit else f"{value[: limit - 3].rstrip()}..."


def generate_certificate_pdf(
    certificate: DigitalCertificate,
    enrollment: ProgrammeEnrollment,
) -> bytes:
    output = BytesIO()
    page_width, page_height = landscape(A4)
    document = canvas.Canvas(output, pagesize=(page_width, page_height))
    font = _pdf_font()
    url = verification_url(certificate.verification_token)
    qr_output = BytesIO()
    qrcode.make(url).save(qr_output)
    qr_output.seek(0)

    document.setFillColor(colors.HexColor("#F7FAF8"))
    document.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    document.setStrokeColor(colors.HexColor("#175C3A"))
    document.setLineWidth(4)
    document.rect(24, 24, page_width - 48, page_height - 48, fill=0, stroke=1)
    document.setStrokeColor(colors.HexColor("#D39B2A"))
    document.setLineWidth(1.5)
    document.rect(34, 34, page_width - 68, page_height - 68, fill=0, stroke=1)

    document.setFillColor(colors.HexColor("#175C3A"))
    document.setFont(font, 14)
    document.drawCentredString(
        page_width / 2,
        page_height - 85,
        "NCCT COOPERATIVE TRAINING PLATFORM",
    )
    document.setFillColor(colors.HexColor("#17352A"))
    document.setFont(font, 30)
    document.drawCentredString(page_width / 2, page_height - 138, _fit_text(certificate.title, 52))
    document.setFont(font, 13)
    document.drawCentredString(page_width / 2, page_height - 182, "This certificate is awarded to")
    document.setFillColor(colors.HexColor("#0F6A46"))
    document.setFont(font, 26)
    document.drawCentredString(
        page_width / 2,
        page_height - 226,
        _fit_text(display_name(enrollment.trainee), 58),
    )
    document.setFillColor(colors.HexColor("#17352A"))
    document.setFont(font, 13)
    document.drawCentredString(page_width / 2, page_height - 263, "for successfully completing")
    document.setFont(font, 20)
    document.drawCentredString(
        page_width / 2,
        page_height - 300,
        _fit_text(enrollment.programme.title, 72),
    )
    document.setFont(font, 12)
    document.drawCentredString(
        page_width / 2,
        page_height - 329,
        _fit_text(enrollment.programme.institution.name, 92),
    )

    issued = as_utc(certificate.issued_at).strftime("%d %B %Y")
    expiry = (
        as_utc(certificate.expires_at).strftime("%d %B %Y")
        if certificate.expires_at
        else "No expiry"
    )
    document.setFont(font, 10)
    document.drawString(70, 95, f"Issued: {issued}")
    document.drawString(70, 77, f"Valid until: {expiry}")
    document.drawString(70, 59, f"Certificate: {certificate.certificate_number}")
    document.drawImage(ImageReader(qr_output), page_width - 150, 52, width=82, height=82)
    document.setFont(font, 8)
    document.drawCentredString(page_width - 109, 43, "Scan to verify")
    document.save()
    return output.getvalue()


def certificate_state(certificate: DigitalCertificate) -> CertificateState:
    if certificate.revoked_at is not None:
        return CertificateState.REVOKED
    if certificate.expires_at is not None and as_utc(certificate.expires_at) <= utc_now():
        return CertificateState.EXPIRED
    return CertificateState.VALID


def load_certificate(db: Session, certificate_id: UUID) -> DigitalCertificate:
    certificate = db.scalar(
        select(DigitalCertificate)
        .where(DigitalCertificate.id == certificate_id)
        .options(
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.programme)
            .joinedload(Programme.institution),
            joinedload(DigitalCertificate.policy),
        )
    )
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return certificate


def audit_history(db: Session, certificate: DigitalCertificate) -> list[CertificateAuditEvent]:
    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.event_type.in_(("certificate.issued", "certificate.revoked")))
            .order_by(AuditLog.created_at.desc())
        )
    )
    logs = [log for log in logs if log.details.get("certificate_id") == str(certificate.id)]
    user_ids = {log.user_id for log in logs if log.user_id is not None}
    users = (
        {
            user.id: user
            for user in db.scalars(
                select(User).where(User.id.in_(user_ids)).options(joinedload(User.profile))
            )
        }
        if user_ids
        else {}
    )
    return [
        CertificateAuditEvent(
            event_type=log.event_type,
            actor_name=display_name(users[log.user_id]) if log.user_id in users else None,
            details={
                key: value
                for key, value in log.details.items()
                if key not in {"certificate_id", "enrollment_id"}
                and isinstance(value, (str, float, bool, type(None)))
            },
            created_at=log.created_at,
        )
        for log in logs
    ]


def record_public(
    db: Session,
    certificate: DigitalCertificate,
    *,
    include_audit: bool = True,
) -> CertificateRecordPublic:
    enrollment = certificate.enrollment
    state = certificate_state(certificate)
    return CertificateRecordPublic(
        id=certificate.id,
        enrollment_id=enrollment.id,
        certificate_number=certificate.certificate_number,
        title=certificate.title,
        recipient_name=display_name(enrollment.trainee),
        recipient_email=enrollment.trainee.email,
        programme_id=enrollment.programme_id,
        programme_title=enrollment.programme.title,
        programme_code=enrollment.programme.code,
        institution_name=enrollment.programme.institution.name,
        state=state,
        valid=state == CertificateState.VALID,
        metrics=CertificateMetrics(
            course_completion_percent=certificate.course_completion_percent,
            attendance_percent=certificate.attendance_percent,
            assessment_score_percent=certificate.assessment_score_percent,
        ),
        issued_at=certificate.issued_at,
        expires_at=certificate.expires_at,
        revoked_at=certificate.revoked_at,
        revocation_reason=certificate.revocation_reason,
        verification_url=verification_url(certificate.verification_token),
        audit_history=audit_history(db, certificate) if include_audit else [],
    )


def _new_certificate_number(db: Session) -> str:
    for _ in range(5):
        value = f"NCCT-{utc_now().year}-{secrets.token_hex(6).upper()}"
        if (
            db.scalar(
                select(DigitalCertificate.id).where(DigitalCertificate.certificate_number == value)
            )
            is None
        ):
            return value
    raise HTTPException(status_code=503, detail="Could not allocate a certificate number")


def _new_verification_token(db: Session) -> str:
    for _ in range(5):
        value = secrets.token_urlsafe(32)
        if (
            db.scalar(
                select(DigitalCertificate.id).where(DigitalCertificate.verification_token == value)
            )
            is None
        ):
            return value
    raise HTTPException(status_code=503, detail="Could not allocate a verification token")


def issue_certificate(
    db: Session,
    request: Request,
    user: User,
    enrollment_id: UUID,
) -> CertificateRecordPublic:
    enrollment = load_enrollment(db, enrollment_id)
    ensure_programme_manager(user, enrollment.programme)
    policy = load_policy(db, enrollment.programme_id)
    if policy is None:
        raise HTTPException(status_code=422, detail="Configure a certificate policy first")
    if (
        db.scalar(
            select(DigitalCertificate.id).where(DigitalCertificate.enrollment_id == enrollment.id)
        )
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="A certificate already exists for this enrollment",
        )
    eligibility = calculate_eligibility(db, enrollment, policy)
    if not eligibility.eligible:
        raise HTTPException(
            status_code=422,
            detail=(
                "Trainee does not meet the certificate eligibility policy: "
                + "; ".join(eligibility.reasons)
            ),
        )
    now = utc_now()
    certificate = DigitalCertificate(
        enrollment_id=enrollment.id,
        policy_id=policy.id,
        issued_by_id=user.id,
        certificate_number=_new_certificate_number(db),
        verification_token=_new_verification_token(db),
        title=policy.certificate_title,
        course_completion_percent=eligibility.metrics.course_completion_percent,
        attendance_percent=eligibility.metrics.attendance_percent,
        assessment_score_percent=eligibility.metrics.assessment_score_percent,
        pdf_content=b"pending",
        issued_at=now,
        expires_at=now + timedelta(days=policy.validity_days) if policy.validity_days else None,
    )
    certificate.enrollment = enrollment
    certificate.pdf_content = generate_certificate_pdf(certificate, enrollment)
    db.add(certificate)
    db.flush()
    trainee_profile = db.scalar(
        select(TraineeProfile).where(TraineeProfile.user_id == enrollment.trainee_id)
    )
    if trainee_profile:
        for skill in dict.fromkeys(
            value.strip() for value in trainee_profile.skills if value.strip()
        ):
            db.add(
                VerifiedEmploymentSkill(
                    trainee_id=enrollment.trainee_id,
                    certificate_id=certificate.id,
                    name=skill,
                )
            )
    add_audit(
        db,
        request,
        "certificate.issued",
        user=user,
        details={
            "certificate_id": str(certificate.id),
            "enrollment_id": str(enrollment.id),
            "certificate_number": certificate.certificate_number,
            "course_completion_percent": certificate.course_completion_percent,
            "attendance_percent": certificate.attendance_percent,
            "assessment_score_percent": certificate.assessment_score_percent,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A certificate already exists") from exc
    return record_public(db, load_certificate(db, certificate.id))


def candidate_public(
    db: Session,
    enrollment: ProgrammeEnrollment,
    policy: CertificatePolicy,
) -> CertificateCandidatePublic:
    eligibility = calculate_eligibility(db, enrollment, policy)
    certificate = db.scalar(
        select(DigitalCertificate)
        .where(DigitalCertificate.enrollment_id == enrollment.id)
        .options(
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.programme)
            .joinedload(Programme.institution),
        )
    )
    return CertificateCandidatePublic(
        enrollment_id=enrollment.id,
        trainee_name=display_name(enrollment.trainee),
        trainee_email=enrollment.trainee.email,
        enrollment_status=enrollment.status,
        metrics=eligibility.metrics,
        eligible=eligibility.eligible,
        reasons=eligibility.reasons,
        certificate=record_public(db, certificate) if certificate else None,
    )


def list_candidates(
    db: Session,
    user: User,
    programme_id: UUID,
) -> list[CertificateCandidatePublic]:
    programme = db.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    ensure_programme_manager(user, programme)
    policy = load_policy(db, programme_id)
    if policy is None:
        raise HTTPException(status_code=422, detail="Configure a certificate policy first")
    enrollments = list(
        db.scalars(
            select(ProgrammeEnrollment)
            .where(ProgrammeEnrollment.programme_id == programme_id)
            .options(*enrollment_options())
            .order_by(ProgrammeEnrollment.enrolled_at)
        )
    )
    return [candidate_public(db, enrollment, policy) for enrollment in enrollments]


def list_certificates(
    db: Session,
    user: User,
    programme_id: UUID | None,
) -> list[CertificateRecordPublic]:
    statement = (
        select(DigitalCertificate)
        .join(DigitalCertificate.enrollment)
        .join(ProgrammeEnrollment.programme)
        .options(
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.programme)
            .joinedload(Programme.institution),
        )
        .order_by(DigitalCertificate.issued_at.desc())
    )
    roles = role_codes(user)
    if not has_permission(roles, Permission.PLATFORM_MANAGE):
        if RoleCode.INSTITUTE_ADMIN not in roles or user.institution_id is None:
            raise HTTPException(
                status_code=403,
                detail="Certificate administration is not permitted",
            )
        statement = statement.where(Programme.institution_id == user.institution_id)
    if programme_id is not None:
        programme = db.get(Programme, programme_id)
        if programme is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        ensure_programme_manager(user, programme)
        statement = statement.where(Programme.id == programme_id)
    return [record_public(db, item) for item in db.scalars(statement).unique()]


def wallet(db: Session, user: User) -> SkillWalletPublic:
    certificates = list(
        db.scalars(
            select(DigitalCertificate)
            .join(DigitalCertificate.enrollment)
            .where(ProgrammeEnrollment.trainee_id == user.id)
            .options(
                joinedload(DigitalCertificate.enrollment)
                .joinedload(ProgrammeEnrollment.trainee)
                .joinedload(User.profile),
                joinedload(DigitalCertificate.enrollment)
                .joinedload(ProgrammeEnrollment.programme)
                .joinedload(Programme.institution),
            )
            .order_by(DigitalCertificate.issued_at.desc())
        ).unique()
    )
    records = [record_public(db, item) for item in certificates]
    return SkillWalletPublic(
        certificates=records,
        total=len(records),
        valid_count=sum(record.valid for record in records),
    )


def revoke_certificate(
    db: Session,
    request: Request,
    user: User,
    certificate_id: UUID,
    reason: str,
) -> CertificateRecordPublic:
    certificate = load_certificate(db, certificate_id)
    ensure_programme_manager(user, certificate.enrollment.programme)
    if certificate.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Certificate is already revoked")
    certificate.revoked_at = utc_now()
    certificate.revoked_by_id = user.id
    certificate.revocation_reason = reason.strip()
    add_audit(
        db,
        request,
        "certificate.revoked",
        user=user,
        details={
            "certificate_id": str(certificate.id),
            "enrollment_id": str(certificate.enrollment_id),
            "certificate_number": certificate.certificate_number,
            "reason": certificate.revocation_reason,
        },
    )
    db.commit()
    return record_public(db, load_certificate(db, certificate.id))


def certificate_download(db: Session, user: User, certificate_id: UUID) -> DigitalCertificate:
    certificate = load_certificate(db, certificate_id)
    roles = role_codes(user)
    is_owner = certificate.enrollment.trainee_id == user.id
    can_manage = has_permission(roles, Permission.CERTIFICATES_MANAGE)
    if not is_owner and not can_manage:
        raise HTTPException(status_code=403, detail="You cannot download this certificate")
    if can_manage and not is_owner:
        ensure_programme_manager(user, certificate.enrollment.programme)
    return certificate


def verify_certificate(db: Session, token: str) -> CertificateVerificationPublic:
    if len(token) < 32:
        raise HTTPException(status_code=404, detail="Certificate not found")
    certificate = db.scalar(
        select(DigitalCertificate)
        .where(DigitalCertificate.verification_token == token)
        .options(
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.programme)
            .joinedload(Programme.institution),
        )
    )
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    state = certificate_state(certificate)
    return CertificateVerificationPublic(
        certificate_number=certificate.certificate_number,
        title=certificate.title,
        recipient_name=display_name(certificate.enrollment.trainee),
        programme_title=certificate.enrollment.programme.title,
        institution_name=certificate.enrollment.programme.institution.name,
        state=state,
        valid=state == CertificateState.VALID,
        issued_at=certificate.issued_at,
        expires_at=certificate.expires_at,
    )
