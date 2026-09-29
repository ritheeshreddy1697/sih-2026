from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    CertificatePolicy,
    DigitalCertificate,
    EmployerProfile,
    EmployerVerificationStatus,
    EnrollmentStatus,
    Institution,
    InstitutionType,
    Programme,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    RoleCode,
    TraineeEmploymentProfile,
    TraineeProfile,
    User,
    VerifiedEmploymentSkill,
)
from tests.conftest import create_test_user


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_scenario(db: Session, suffix: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    ncct = Institution(
        code=f"NCCT-EMP-{suffix}",
        name="NCCT Employment Test",
        institution_type=InstitutionType.NCCT,
    )
    institute = Institution(
        code=f"ICM-EMP-{suffix}",
        name="ICM Employment Test",
        institution_type=InstitutionType.ICM,
    )
    company = Institution(
        code=f"EMP-{suffix}",
        name="Fictional Cooperative Services Limited",
        institution_type=InstitutionType.EMPLOYER,
    )
    other_company = Institution(
        code=f"EMP-OTHER-{suffix}",
        name="Other Fictional Employer",
        institution_type=InstitutionType.EMPLOYER,
    )
    db.add_all([ncct, institute, company, other_company])
    db.commit()
    super_admin = create_test_user(
        db,
        email=f"employment.admin.{suffix}@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=ncct,
    )
    institute_admin = create_test_user(
        db,
        email=f"employment.institute.{suffix}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    employer = create_test_user(
        db,
        email=f"employment.recruiter.{suffix}@example.com",
        role_code=RoleCode.EMPLOYER_RECRUITER,
        institution=company,
    )
    other_employer = create_test_user(
        db,
        email=f"employment.other.{suffix}@example.com",
        role_code=RoleCode.EMPLOYER_RECRUITER,
        institution=other_company,
    )
    trainee = create_test_user(
        db,
        email=f"employment.trainee.{suffix}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institute,
    )
    employer_profile = EmployerProfile(
        institution_id=company.id,
        registered_by_id=employer.id,
        verified_by_id=super_admin.id,
        industry="Cooperative technology",
        website="https://example.invalid",
        company_size="51-200",
        description="A fictional employer used only for automated employment tests.",
        headquarters="Hyderabad, Telangana",
        registration_number="DEMO-EMP-001",
        verification_status=EmployerVerificationStatus.VERIFIED,
        verified_at=now,
    )
    other_profile = EmployerProfile(
        institution_id=other_company.id,
        registered_by_id=other_employer.id,
        industry="Training",
        description="A second fictional employer used for ownership checks.",
        headquarters="Pune, Maharashtra",
        verification_status=EmployerVerificationStatus.VERIFIED,
        verified_by_id=super_admin.id,
        verified_at=now,
    )
    trainee_profile = TraineeProfile(
        user_id=trainee.id,
        city="Hyderabad",
        state="Telangana",
        preferred_location="Hyderabad",
        career_interests="digital services, cooperative operations",
        skills=["Digital member services", "Data handling"],
        placement_visibility_consent=True,
        data_sharing_consent=False,
    )
    employment_profile = TraineeEmploymentProfile(
        trainee_id=trainee.id,
        headline="Certified cooperative services associate",
        professional_summary="Trained in member service delivery and responsible data use.",
        preferred_roles=["digital services"],
        preferred_locations=["Hyderabad"],
        open_to_work=True,
        resume_filename="demo-resume.pdf",
        resume_content_type="application/pdf",
        resume_size_bytes=12,
        resume_content=b"%PDF-demo%",
        resume_uploaded_at=now,
    )
    programme = Programme(
        institution_id=institute.id,
        created_by_id=institute_admin.id,
        updated_by_id=institute_admin.id,
        title="Digital Services for Cooperatives",
        code=f"EMP-COURSE-{suffix}",
        summary="Fictional course for employment tests.",
        description="Fictional certified training for cooperative digital services.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.ARCHIVED,
        eligibility_criteria="Demonstration only",
        eligible_applicant_types=["individual"],
        capacity=20,
        location="Hyderabad",
        language="English",
        duration_days=3,
        application_deadline=now - timedelta(days=10),
        start_date=date.today() - timedelta(days=9),
        end_date=date.today() - timedelta(days=7),
        archived_at=now - timedelta(days=6),
    )
    db.add_all([employer_profile, other_profile, trainee_profile, employment_profile, programme])
    db.flush()
    enrollment = ProgrammeEnrollment(
        trainee_id=trainee.id,
        programme_id=programme.id,
        status=EnrollmentStatus.COMPLETED,
        completed_at=now - timedelta(days=5),
    )
    policy = CertificatePolicy(
        programme_id=programme.id,
        configured_by_id=institute_admin.id,
        certificate_title="Certificate in Digital Cooperative Services",
        minimum_course_completion_percent=0,
        minimum_attendance_percent=0,
        minimum_assessment_score_percent=0,
    )
    db.add_all([enrollment, policy])
    db.flush()
    certificate = DigitalCertificate(
        enrollment_id=enrollment.id,
        policy_id=policy.id,
        issued_by_id=institute_admin.id,
        certificate_number=f"NCCT-EMP-{suffix}",
        verification_token=f"employment-token-{suffix}-{uuid4().hex}",
        title=policy.certificate_title,
        course_completion_percent=100,
        attendance_percent=90,
        assessment_score_percent=84,
        pdf_content=b"%PDF-certificate%",
        issued_at=now - timedelta(days=4),
        expires_at=now + timedelta(days=365),
    )
    db.add(certificate)
    db.flush()
    db.add_all(
        [
            VerifiedEmploymentSkill(
                trainee_id=trainee.id,
                certificate_id=certificate.id,
                name="Digital member services",
            ),
            VerifiedEmploymentSkill(
                trainee_id=trainee.id,
                certificate_id=certificate.id,
                name="Data handling",
            ),
        ]
    )
    db.commit()
    return {
        "admin": super_admin,
        "employer": employer,
        "other_employer": other_employer,
        "trainee": trainee,
        "trainee_profile": trainee_profile,
        "programme": programme,
    }


def job_payload(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Digital Services Coordinator",
        "description": (
            "Support cooperative members with digital services and responsible data handling."
        ),
        "location": "Hyderabad, Telangana",
        "employment_type": "full_time",
        "workplace_mode": "hybrid",
        "required_skills": ["Digital member services", "Data handling"],
        "preferred_skills": ["Member support"],
        "minimum_experience_years": 0,
        "vacancies": 2,
        "salary_minimum": 300000,
        "salary_maximum": 450000,
        "application_deadline": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        "required_programme_ids": [str(scenario["programme"].id)],
    }


def create_and_publish_job(
    client: TestClient, scenario: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    created = client.post(
        "/api/v1/employment/employer/jobs", headers=headers, json=job_payload(scenario)
    )
    assert created.status_code == 201, created.text
    published = client.post(
        f"/api/v1/employment/employer/jobs/{created.json()['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200, published.text
    return cast(dict[str, Any], published.json())


def test_job_permissions_and_employer_ownership(client: TestClient, db_session: Session) -> None:
    scenario = build_scenario(db_session, "permissions")
    employer_headers = login(client, scenario["employer"])
    other_headers = login(client, scenario["other_employer"])
    admin_headers = login(client, scenario["admin"])
    trainee_headers = login(client, scenario["trainee"])

    created = client.post(
        "/api/v1/employment/employer/jobs",
        headers=employer_headers,
        json=job_payload(scenario),
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert (
        client.put(
            f"/api/v1/employment/employer/jobs/{job_id}",
            headers=other_headers,
            json=job_payload(scenario),
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/employment/employer/jobs",
            headers=trainee_headers,
            json=job_payload(scenario),
        ).status_code
        == 403
    )

    employers = client.get("/api/v1/employment/admin/employers", headers=admin_headers)
    assert employers.status_code == 200
    assert len(employers.json()) == 2
    assert (
        client.get("/api/v1/employment/admin/employers", headers=employer_headers).status_code
        == 403
    )


def test_employer_registration_requires_ncct_verification(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_scenario(db_session, "registration")
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Fictional Employer Applicant",
            "email": "new.employer@example.com",
            "password": "DemoEmployer!2026",
            "role_code": "employer_recruiter",
            "phone": "+91 90000 00000",
            "organisation_name": "New Demonstration Cooperative Employer",
            "industry": "Cooperative services",
            "website": "https://example.invalid/new-employer",
            "company_size": "11-50",
            "company_description": (
                "A fictional employer registration created only for automated tests."
            ),
            "headquarters": "Bhopal, Madhya Pradesh",
            "registration_number": "DEMO-REG-002",
            "consent_accepted": True,
        },
    )
    assert registration.status_code == 201, registration.text
    blocked_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new.employer@example.com",
            "password": "DemoEmployer!2026",
        },
    )
    assert blocked_login.status_code == 403

    admin_headers = login(client, scenario["admin"])
    pending = client.get(
        "/api/v1/employment/admin/employers?verification_status=pending",
        headers=admin_headers,
    )
    assert pending.status_code == 200
    profile = next(
        item for item in pending.json() if item["contact_email"] == "new.employer@example.com"
    )
    approved = client.patch(
        f"/api/v1/employment/admin/employers/{profile['id']}/verification",
        headers=admin_headers,
        json={"status": "verified", "notes": "Fictional registration reviewed."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["verification_status"] == "verified"
    active_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new.employer@example.com",
            "password": "DemoEmployer!2026",
        },
    )
    assert active_login.status_code == 200


def test_application_workflow_and_contact_consent(client: TestClient, db_session: Session) -> None:
    scenario = build_scenario(db_session, "workflow")
    employer_headers = login(client, scenario["employer"])
    trainee_headers = login(client, scenario["trainee"])
    job = create_and_publish_job(client, scenario, employer_headers)

    candidates = client.get(
        f"/api/v1/employment/employer/candidates?job_id={job['id']}",
        headers=employer_headers,
    )
    assert candidates.status_code == 200, candidates.text
    candidate = candidates.json()[0]
    assert candidate["match"]["score"] == 100
    assert candidate["contact"] is None
    assert candidate["resume_download_allowed"] is False

    application = client.post(
        f"/api/v1/employment/jobs/{job['id']}/apply",
        headers=trainee_headers,
        json={"cover_note": "I would like to support cooperative member services."},
    )
    assert application.status_code == 201, application.text
    assert len(application.json()["certificates"]) == 1
    application_id = application.json()["id"]

    workspace = client.get("/api/v1/employment/employer/workspace", headers=employer_headers)
    assert workspace.status_code == 200
    assert workspace.json()["applications"][0]["contact"] is None

    scenario["trainee_profile"].data_sharing_consent = True
    db_session.commit()
    workspace = client.get("/api/v1/employment/employer/workspace", headers=employer_headers)
    assert workspace.json()["applications"][0]["contact"]["email"] == scenario["trainee"].email
    resume = client.get(
        f"/api/v1/employment/employer/candidates/{scenario['trainee'].id}/resume",
        headers=employer_headers,
    )
    assert resume.status_code == 200
    assert resume.content == b"%PDF-demo%"

    shortlist = client.patch(
        f"/api/v1/employment/employer/applications/{application_id}",
        headers=employer_headers,
        json={"status": "shortlisted"},
    )
    assert shortlist.status_code == 200, shortlist.text
    interview = client.patch(
        f"/api/v1/employment/employer/applications/{application_id}",
        headers=employer_headers,
        json={
            "status": "interview_scheduled",
            "interview_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "interview_mode": "Video call",
            "interview_details": "Link shared after confirmation.",
        },
    )
    assert interview.status_code == 200, interview.text
    assert interview.json()["status"] == "interview_scheduled"


def test_recommendation_is_explainable_and_application_can_be_withdrawn(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_scenario(db_session, "recommendation")
    employer_headers = login(client, scenario["employer"])
    trainee_headers = login(client, scenario["trainee"])
    job = create_and_publish_job(client, scenario, employer_headers)

    recommendations = client.get("/api/v1/employment/jobs/recommendations", headers=trainee_headers)
    assert recommendations.status_code == 200
    match = recommendations.json()[0]["match"]
    assert match["score"] == 100
    assert match["reasons"]
    assert {"skill_score", "course_score", "location_score", "interest_score"}.issubset(match)

    saved = client.post(f"/api/v1/employment/jobs/{job['id']}/save", headers=trainee_headers)
    assert saved.status_code == 200
    assert saved.json()["saved"] is True
    application = client.post(
        f"/api/v1/employment/jobs/{job['id']}/apply",
        headers=trainee_headers,
        json={},
    )
    assert application.status_code == 201
    withdrawn = client.post(
        f"/api/v1/employment/me/applications/{application.json()['id']}/withdraw",
        headers=trainee_headers,
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert (
        client.post(
            f"/api/v1/employment/jobs/{job['id']}/apply",
            headers=trainee_headers,
            json={},
        ).status_code
        == 409
    )
