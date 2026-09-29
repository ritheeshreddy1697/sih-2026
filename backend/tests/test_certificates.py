from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentType,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
    AuditLog,
    Course,
    CourseModule,
    CourseSection,
    CourseStatus,
    DigitalCertificate,
    EligibilityType,
    EnrollmentStatus,
    Institution,
    InstitutionType,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonProgress,
    LessonType,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    QuestionBank,
    RoleCode,
    TraineeProfile,
    User,
)
from tests.conftest import create_test_user


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_certificate_scenario(db: Session, suffix: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    institution = Institution(
        code=f"ICM-CERT-{suffix}",
        name=f"ICM Certificate Demonstration {suffix}",
        institution_type=InstitutionType.ICM,
        is_demo=True,
    )
    other_institution = Institution(
        code=f"RICM-CERT-{suffix}",
        name=f"Other RICM {suffix}",
        institution_type=InstitutionType.RICM,
        is_demo=True,
    )
    db.add_all([institution, other_institution])
    db.commit()
    admin = create_test_user(
        db,
        email=f"certificate.admin.{suffix.lower()}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    other_admin = create_test_user(
        db,
        email=f"certificate.other.{suffix.lower()}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=other_institution,
    )
    trainer = create_test_user(
        db,
        email=f"certificate.trainer.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    trainee = create_test_user(
        db,
        email=f"certificate.trainee.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    db.add(TraineeProfile(user_id=trainee.id, is_demo=True))
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title=f"Certificate programme {suffix}",
        code=f"CERT-{suffix}",
        summary="A demonstration programme for certificate tests.",
        description="Validates backend-owned eligibility and certificate verification.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Open to demonstration trainees.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=30,
        location="Demonstration Centre",
        language="English",
        duration_days=2,
        application_deadline=now + timedelta(days=1),
        start_date=now.date(),
        end_date=(now + timedelta(days=1)).date(),
        published_at=now,
    )
    batch = ProgrammeBatch(
        programme=programme,
        name="Certificate batch",
        code="CERT-BATCH",
        capacity=30,
        start_date=now.date(),
        end_date=(now + timedelta(days=1)).date(),
        location="Room 2",
    )
    course = Course(
        programme=programme,
        created_by_id=admin.id,
        title="Cooperative leadership course",
        summary="Demonstration learning content.",
        status=CourseStatus.PUBLISHED,
        default_language_code="en",
    )
    section = CourseSection(course=course, title="Foundations", position=1)
    module = CourseModule(section=section, title="Core module", position=1)
    lesson = Lesson(
        module=module,
        title="Cooperative principles",
        lesson_type=LessonType.TEXT,
        position=1,
        duration_seconds=300,
        is_required=True,
    )
    bank = QuestionBank(
        course=course,
        title="Post-training bank",
        description="Certificate assessment questions.",
    )
    assessment = LearnerAssessment(
        course=course,
        question_bank=bank,
        title="Post-training assessment",
        assessment_type=AssessmentType.POST_TRAINING,
        attempt_limit=2,
        passing_score_percent=70,
        is_published=True,
    )
    enrollment = ProgrammeEnrollment(
        trainee_id=trainee.id,
        programme=programme,
        batch=batch,
        status=EnrollmentStatus.ENROLLED,
    )
    attendance_session = AttendanceSession(
        programme=programme,
        batch=batch,
        created_by_id=admin.id,
        title="Completed workshop",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
        status=AttendanceSessionStatus.CLOSED,
    )
    db.add_all([programme, course, enrollment, attendance_session])
    db.commit()
    return {
        "admin": admin,
        "other_admin": other_admin,
        "trainer": trainer,
        "trainee": trainee,
        "programme": programme,
        "enrollment": enrollment,
        "lesson": lesson,
        "assessment": assessment,
        "attendance_session": attendance_session,
        "now": now,
    }


def configure_policy(
    client: TestClient,
    scenario: dict[str, Any],
    headers: dict[str, str],
) -> None:
    response = client.put(
        f"/api/v1/certificates/programmes/{scenario['programme'].id}/policy",
        headers=headers,
        json={
            "certificate_title": "Certificate of Cooperative Leadership",
            "minimum_course_completion_percent": 100,
            "minimum_attendance_percent": 75,
            "minimum_assessment_score_percent": 70,
            "validity_days": 730,
            "is_active": True,
        },
    )
    assert response.status_code == 200, response.text


def make_eligible(db: Session, scenario: dict[str, Any]) -> None:
    db.add_all(
        [
            LessonProgress(
                enrollment_id=scenario["enrollment"].id,
                lesson_id=scenario["lesson"].id,
                status=LearningProgressStatus.COMPLETED,
                viewed_seconds=300,
                last_position_seconds=300,
                completed_at=scenario["now"],
                last_accessed_at=scenario["now"],
            ),
            AttendanceCheckIn(
                attendance_session_id=scenario["attendance_session"].id,
                enrollment_id=scenario["enrollment"].id,
                created_by_id=scenario["admin"].id,
                idempotency_key=uuid4(),
                status=AttendanceStatus.PRESENT,
                source=AttendanceSource.MANUAL,
                captured_at=scenario["now"],
                checked_in_at=scenario["now"],
            ),
            AssessmentAttempt(
                assessment_id=scenario["assessment"].id,
                enrollment_id=scenario["enrollment"].id,
                attempt_number=1,
                status=AssessmentAttemptStatus.SUBMITTED,
                question_ids=[],
                answers={},
                grading_details=[],
                points_earned=85,
                points_available=100,
                score_percent=85,
                passed=True,
                started_at=scenario["now"],
                submitted_at=scenario["now"],
            ),
        ]
    )
    db.commit()


def test_ineligible_trainee_cannot_receive_certificate(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_certificate_scenario(db_session, "INELIGIBLE")
    admin_headers = login(client, scenario["admin"])
    configure_policy(client, scenario, admin_headers)

    candidates = client.get(
        "/api/v1/certificates/candidates",
        params={"programme_id": str(scenario["programme"].id)},
        headers=admin_headers,
    )
    assert candidates.status_code == 200
    assert candidates.json()[0]["eligible"] is False
    assert len(candidates.json()[0]["reasons"]) == 3

    response = client.post(
        "/api/v1/certificates/issue",
        headers=admin_headers,
        json={"enrollment_id": str(scenario["enrollment"].id)},
    )
    assert response.status_code == 422
    assert "does not meet" in response.json()["detail"]

    browser_claims = client.post(
        "/api/v1/certificates/issue",
        headers=admin_headers,
        json={
            "enrollment_id": str(scenario["enrollment"].id),
            "assessment_score_percent": 100,
            "recipient_name": "Fabricated Name",
        },
    )
    assert browser_claims.status_code == 422


def test_issue_pdf_wallet_and_public_verification(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_certificate_scenario(db_session, "ISSUE")
    admin_headers = login(client, scenario["admin"])
    configure_policy(client, scenario, admin_headers)
    make_eligible(db_session, scenario)

    trainer_forbidden = client.post(
        "/api/v1/certificates/issue",
        headers=login(client, scenario["trainer"]),
        json={"enrollment_id": str(scenario["enrollment"].id)},
    )
    assert trainer_forbidden.status_code == 403
    other_institution_forbidden = client.get(
        "/api/v1/certificates/candidates",
        params={"programme_id": str(scenario["programme"].id)},
        headers=login(client, scenario["other_admin"]),
    )
    assert other_institution_forbidden.status_code == 403

    issued = client.post(
        "/api/v1/certificates/issue",
        headers=admin_headers,
        json={"enrollment_id": str(scenario["enrollment"].id)},
    )
    assert issued.status_code == 201, issued.text
    certificate = issued.json()
    assert certificate["state"] == "valid"
    assert certificate["metrics"]["course_completion_percent"] == 100
    assert certificate["metrics"]["attendance_percent"] == 100
    assert certificate["metrics"]["assessment_score_percent"] == 85

    download = client.get(
        f"/api/v1/certificates/{certificate['id']}/download",
        headers=login(client, scenario["trainee"]),
    )
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")

    wallet = client.get(
        "/api/v1/certificates/wallet/me",
        headers=login(client, scenario["trainee"]),
    )
    assert wallet.status_code == 200
    assert wallet.json()["valid_count"] == 1

    token = certificate["verification_url"].rsplit("/", maxsplit=1)[-1]
    verified = client.get(f"/api/v1/certificates/verify/{token}")
    assert verified.status_code == 200
    public_record = verified.json()
    assert public_record["valid"] is True
    assert public_record["recipient_name"] == "Test User"
    assert "recipient_email" not in public_record
    assert "metrics" not in public_record
    assert "revocation_reason" not in public_record

    stored_certificate = db_session.get(DigitalCertificate, UUID(certificate["id"]))
    assert stored_certificate is not None
    stored_certificate.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    expired = client.get(f"/api/v1/certificates/verify/{token}")
    assert expired.status_code == 200
    assert expired.json()["state"] == "expired"
    assert expired.json()["valid"] is False

    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "certificate.issued")
    )
    assert audit is not None
    assert audit.details["certificate_number"] == certificate["certificate_number"]


def test_revoked_certificate_appears_invalid(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_certificate_scenario(db_session, "REVOKE")
    admin_headers = login(client, scenario["admin"])
    configure_policy(client, scenario, admin_headers)
    make_eligible(db_session, scenario)
    issued = client.post(
        "/api/v1/certificates/issue",
        headers=admin_headers,
        json={"enrollment_id": str(scenario["enrollment"].id)},
    )
    assert issued.status_code == 201, issued.text
    certificate = issued.json()

    revoked = client.post(
        f"/api/v1/certificates/{certificate['id']}/revoke",
        headers=admin_headers,
        json={"reason": "Issued against an incorrect enrolment record"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["state"] == "revoked"
    assert revoked.json()["valid"] is False
    assert revoked.json()["revocation_reason"] == (
        "Issued against an incorrect enrolment record"
    )

    token = certificate["verification_url"].rsplit("/", maxsplit=1)[-1]
    verified = client.get(f"/api/v1/certificates/verify/{token}")
    assert verified.status_code == 200
    assert verified.json()["state"] == "revoked"
    assert verified.json()["valid"] is False
    assert "revocation_reason" not in verified.json()

    wallet = client.get(
        "/api/v1/certificates/wallet/me",
        headers=login(client, scenario["trainee"]),
    )
    assert wallet.json()["valid_count"] == 0
    assert wallet.json()["certificates"][0]["state"] == "revoked"
