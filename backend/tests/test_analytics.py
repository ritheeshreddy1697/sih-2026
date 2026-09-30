from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    ApplicationStatus,
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentType,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
    CertificatePolicy,
    Course,
    CourseModule,
    CourseSection,
    CourseStatus,
    DigitalCertificate,
    EligibilityType,
    EmployerProfile,
    EmployerVerificationStatus,
    EmploymentType,
    EnrollmentStatus,
    Institution,
    InstitutionType,
    JobApplication,
    JobApplicationStatus,
    JobPosting,
    JobStatus,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonProgress,
    LessonType,
    Programme,
    ProgrammeApplication,
    ProgrammeBatch,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    QuestionBank,
    RoleCode,
    TraineeProfile,
    User,
    WorkplaceMode,
)
from tests.conftest import create_test_user


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_analytics_scenario(db: Session) -> dict[str, Any]:
    now = datetime.now(UTC)
    institute = Institution(
        name="Analytics Demonstration ICM",
        code="ICM-ANALYTICS-DEMO",
        institution_type=InstitutionType.ICM,
        state="Telangana",
        is_demo=True,
    )
    other_institute = Institution(
        name="Outside Analytics RICM",
        code="RICM-ANALYTICS-OUTSIDE",
        institution_type=InstitutionType.RICM,
        state="Maharashtra",
    )
    employer_institution = Institution(
        name="Analytics Demonstration Employer",
        code="EMP-ANALYTICS-DEMO",
        institution_type=InstitutionType.EMPLOYER,
        is_demo=True,
    )
    db.add_all([institute, other_institute, employer_institution])
    db.commit()
    child_institute = Institution(
        name="Child Analytics Training Centre",
        code="ICM-ANALYTICS-CHILD",
        institution_type=InstitutionType.TRAINING_INSTITUTE,
        parent_id=institute.id,
        state="Telangana",
    )
    db.add(child_institute)
    db.commit()

    admin = create_test_user(
        db,
        email="analytics.admin@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    other_admin = create_test_user(
        db,
        email="analytics.other@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=other_institute,
    )
    employer = create_test_user(
        db,
        email="analytics.employer@example.com",
        role_code=RoleCode.EMPLOYER_RECRUITER,
        institution=employer_institution,
    )
    trainee_one = create_test_user(
        db,
        email="analytics.trainee.one@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institute,
    )
    trainee_two = create_test_user(
        db,
        email="analytics.trainee.two@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institute,
    )
    db.add_all(
        [
            TraineeProfile(
                user_id=trainee_one.id,
                state="Telangana",
                gender="Woman",
                is_demo=True,
            ),
            TraineeProfile(
                user_id=trainee_two.id,
                state="Andhra Pradesh",
                gender="Man",
                is_demo=True,
            ),
        ]
    )
    programme = Programme(
        institution_id=institute.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title="Analytics Demonstration Programme",
        code="ANALYTICS-DEMO-2026",
        summary="Fictional analytics calculation programme.",
        description="Persisted records used to verify reporting metrics.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Demonstration trainees only.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=20,
        location="Hyderabad",
        language="English",
        duration_days=2,
        application_deadline=now + timedelta(days=1),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 2),
        published_at=now,
    )
    outside_programme = Programme(
        institution_id=other_institute.id,
        created_by_id=other_admin.id,
        updated_by_id=other_admin.id,
        title="Outside Analytics Programme",
        code="ANALYTICS-OUTSIDE-2026",
        summary="Outside scope.",
        description="This programme must not appear in institute analytics.",
        mode=ProgrammeMode.ONLINE,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Demonstration only.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=20,
        language="English",
        duration_days=1,
        application_deadline=now + timedelta(days=1),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        published_at=now,
    )
    child_programme = Programme(
        institution_id=child_institute.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title="Child Institute Analytics Programme",
        code="ANALYTICS-CHILD-2026",
        summary="Child institution data that must remain outside the administrator's analytics.",
        description="Verifies that institute analytics do not include descendant institutions.",
        mode=ProgrammeMode.ONLINE,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Demonstration only.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=20,
        language="English",
        duration_days=1,
        application_deadline=now + timedelta(days=1),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        published_at=now,
    )
    batch = ProgrammeBatch(
        programme=programme,
        name="Analytics batch",
        code="ANALYTICS-B1",
        capacity=20,
        start_date=programme.start_date,
        end_date=programme.end_date,
        location="Room A",
    )
    applications = [
        ProgrammeApplication(
            programme=programme,
            trainee=trainee,
            status=ApplicationStatus.APPROVED,
            reviewer_id=admin.id,
            submitted_at=now - timedelta(days=20),
            reviewed_at=now - timedelta(days=18),
        )
        for trainee in (trainee_one, trainee_two)
    ]
    enrollments = [
        ProgrammeEnrollment(
            trainee=trainee_one,
            programme=programme,
            batch=batch,
            status=EnrollmentStatus.COMPLETED,
            completed_at=now,
        ),
        ProgrammeEnrollment(
            trainee=trainee_two,
            programme=programme,
            batch=batch,
            status=EnrollmentStatus.WITHDRAWN,
        ),
    ]
    course = Course(
        programme=programme,
        created_by=admin,
        title="Analytics learning course",
        summary="Published course used for completion calculations.",
        status=CourseStatus.PUBLISHED,
    )
    section = CourseSection(course=course, title="Section", position=1)
    module = CourseModule(section=section, title="Module", position=1)
    lessons = [
        Lesson(
            module=module,
            title=f"Required lesson {position}",
            lesson_type=LessonType.TEXT,
            position=position,
            is_required=True,
        )
        for position in (1, 2)
    ]
    bank = QuestionBank(course=course, title="Analytics bank")
    pre_assessment = LearnerAssessment(
        course=course,
        question_bank=bank,
        title="Pre-training assessment",
        assessment_type=AssessmentType.PRE_TRAINING,
        attempt_limit=1,
        passing_score_percent=0,
        is_published=True,
    )
    post_assessment = LearnerAssessment(
        course=course,
        question_bank=bank,
        title="Post-training assessment",
        assessment_type=AssessmentType.POST_TRAINING,
        attempt_limit=1,
        passing_score_percent=60,
        is_published=True,
    )
    attendance_session = AttendanceSession(
        programme=programme,
        batch=batch,
        created_by=admin,
        title="Analytics attendance session",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
        status=AttendanceSessionStatus.CLOSED,
    )
    db.add_all(
        [
            programme,
            outside_programme,
            child_programme,
            *applications,
            *enrollments,
            course,
            attendance_session,
        ]
    )
    db.flush()
    db.add_all(
        [
            LessonProgress(
                enrollment_id=enrollments[0].id,
                lesson_id=lesson.id,
                status=LearningProgressStatus.COMPLETED,
                completed_at=now,
            )
            for lesson in lessons
        ]
        + [
            AssessmentAttempt(
                assessment=pre_assessment,
                enrollment=enrollments[0],
                attempt_number=1,
                status=AssessmentAttemptStatus.SUBMITTED,
                score_percent=40,
                points_earned=4,
                points_available=10,
                submitted_at=now,
            ),
            AssessmentAttempt(
                assessment=post_assessment,
                enrollment=enrollments[0],
                attempt_number=1,
                status=AssessmentAttemptStatus.SUBMITTED,
                score_percent=70,
                points_earned=7,
                points_available=10,
                submitted_at=now,
            ),
            AttendanceCheckIn(
                attendance_session=attendance_session,
                enrollment=enrollments[0],
                created_by=admin,
                idempotency_key=uuid4(),
                status=AttendanceStatus.PRESENT,
                source=AttendanceSource.MANUAL,
                captured_at=now,
            ),
        ]
    )
    policy = CertificatePolicy(
        programme=programme,
        configured_by=admin,
        certificate_title="Analytics Demonstration Certificate",
        minimum_course_completion_percent=100,
        minimum_attendance_percent=50,
        minimum_assessment_score_percent=60,
    )
    employer_profile = EmployerProfile(
        institution=employer_institution,
        registered_by=employer,
        verified_by=admin,
        industry="Cooperative services",
        description="Fictional employer for analytics tests.",
        headquarters="Hyderabad",
        verification_status=EmployerVerificationStatus.VERIFIED,
        verified_at=now,
    )
    db.add_all([policy, employer_profile])
    db.flush()
    certificate = DigitalCertificate(
        enrollment=enrollments[0],
        policy=policy,
        issued_by=admin,
        certificate_number="NCCT-ANALYTICS-0001",
        verification_token=f"analytics-{uuid4().hex}",
        title=policy.certificate_title,
        course_completion_percent=100,
        attendance_percent=100,
        assessment_score_percent=70,
        pdf_content=b"%PDF-analytics%",
        issued_at=now,
    )
    job = JobPosting(
        employer=employer_profile,
        created_by=employer,
        updated_by=employer,
        title="Cooperative Data Associate",
        description="Fictional role for analytics tests.",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
        workplace_mode=WorkplaceMode.HYBRID,
        required_skills=["Data handling"],
        preferred_skills=[],
        minimum_experience_years=0,
        vacancies=1,
        status=JobStatus.PUBLISHED,
        published_at=now,
    )
    db.add_all([certificate, job])
    db.flush()
    db.add(
        JobApplication(
            job=job,
            trainee=trainee_one,
            reviewed_by=employer,
            status=JobApplicationStatus.HIRED,
            interview_at=now,
            status_updated_at=now,
        )
    )
    db.commit()
    db.expire_all()
    return {
        "admin": admin,
        "trainee": trainee_one,
        "institute": institute,
        "programme": programme,
        "child_programme": child_programme,
        "outside_programme": outside_programme,
    }


def metric_values(body: dict[str, Any]) -> dict[str, float]:
    return {item["key"]: item["value"] for item in body["metrics"]}


def test_analytics_metrics_are_calculated_from_persisted_records(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_analytics_scenario(db_session)
    response = client.get(
        "/api/v1/analytics/dashboard?start_date=2026-09-01&end_date=2026-09-30",
        headers=login(client, scenario["admin"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    values = metric_values(body)
    assert values == {
        "registrations": 2,
        "approved_participants": 2,
        "attendance_percentage": 50,
        "course_completion_rate": 50,
        "assessment_improvement": 30,
        "dropout_rate": 50,
        "certificates_issued": 1,
        "job_applications": 1,
        "interviews": 1,
        "placements": 1,
    }
    assert body["contains_demo_data"] is True
    assert body["scope_label"] == "Analytics Demonstration ICM"
    assert len(body["programme_performance"]) == 1
    assert body["programme_performance"][0]["id"] == str(scenario["programme"].id)
    assert {row["state"] for row in body["geographic_distribution"]} == {
        "Telangana",
        "Andhra Pradesh",
    }


def test_analytics_filters_scope_drilldown_export_and_permission(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_analytics_scenario(db_session)
    headers = login(client, scenario["admin"])

    options = client.get("/api/v1/analytics/options", headers=headers)
    assert options.status_code == 200
    assert [item["id"] for item in options.json()["institutions"]] == [
        str(scenario["institute"].id)
    ]
    assert [item["id"] for item in options.json()["programmes"]] == [
        str(scenario["programme"].id)
    ]

    filtered = client.get(
        "/api/v1/analytics/dashboard?state=Telangana&gender=Woman",
        headers=headers,
    )
    assert filtered.status_code == 200
    values = metric_values(filtered.json())
    assert values["registrations"] == 1
    assert values["attendance_percentage"] == 100
    assert values["dropout_rate"] == 0

    drilldown = client.get(
        "/api/v1/analytics/drilldown/assessment_improvement",
        headers=headers,
    )
    assert drilldown.status_code == 200
    assert drilldown.json()["rows"][0]["improvement"] == 30

    export = client.get("/api/v1/analytics/export?view=programme", headers=headers)
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "Analytics Demonstration Programme" in export.text

    outside = client.get(
        "/api/v1/analytics/dashboard",
        headers=headers,
        params={"institution_id": str(scenario["outside_programme"].institution_id)},
    )
    assert outside.status_code == 403

    child = client.get(
        "/api/v1/analytics/dashboard",
        headers=headers,
        params={"institution_id": str(scenario["child_programme"].institution_id)},
    )
    assert child.status_code == 403

    denied = client.get(
        "/api/v1/analytics/dashboard",
        headers=login(client, scenario["trainee"]),
    )
    assert denied.status_code == 403
