from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    EligibilityType,
    Institution,
    InstitutionType,
    Programme,
    ProgrammeMode,
    ProgrammeNomination,
    ProgrammeStatus,
    RoleCode,
    User,
)
from tests.conftest import create_test_user


def create_institution(db: Session, code: str, institution_type: InstitutionType) -> Institution:
    institution = Institution(
        code=code,
        name=f"{code} Institution",
        institution_type=institution_type,
    )
    db.add(institution)
    db.commit()
    return institution


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def programme_payload(institution_id: str | None = None, *, capacity: int = 2) -> dict[str, Any]:
    now = datetime.now(UTC)
    start = (now + timedelta(days=20)).date()
    payload: dict[str, Any] = {
        "title": "Cooperative Credit Operations",
        "code": f"CCO-{int(now.timestamp())}",
        "summary": "Practical credit operations for cooperative-sector professionals.",
        "description": (
            "A detailed programme covering appraisal, monitoring and responsible "
            "cooperative credit."
        ),
        "mode": "hybrid",
        "eligibility_criteria": (
            "Open to individual learners and nominees from cooperative institutions."
        ),
        "eligible_applicant_types": [
            "individual",
            "pacs",
            "shg",
            "cooperative_institution",
        ],
        "capacity": capacity,
        "location": "Training Centre, Pune",
        "language": "English and Hindi",
        "duration_days": 5,
        "application_deadline": (now + timedelta(days=10)).isoformat(),
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=4)).isoformat(),
    }
    if institution_id:
        payload["institution_id"] = institution_id
    return payload


def create_published_programme(
    db: Session,
    admin: User,
    institution: Institution,
    *,
    code: str,
    capacity: int = 2,
    eligible: list[str] | None = None,
) -> Programme:
    now = datetime.now(UTC)
    start = (now + timedelta(days=20)).date()
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title=f"Programme {code}",
        code=code,
        summary="A practical cooperative training programme for eligible participants.",
        description=(
            "Detailed learning content for cooperative-sector participants and institutions."
        ),
        mode=ProgrammeMode.ONLINE,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Eligible applicant categories listed for this programme.",
        eligible_applicant_types=eligible or [EligibilityType.INDIVIDUAL.value],
        capacity=capacity,
        location=None,
        language="English",
        duration_days=3,
        application_deadline=now + timedelta(days=10),
        start_date=start,
        end_date=start + timedelta(days=2),
        published_at=now,
    )
    db.add(programme)
    db.commit()
    return programme


def test_complete_programme_lifecycle_application_and_document(
    client: TestClient, db_session: Session
) -> None:
    institute = create_institution(db_session, "TRAIN-ONE", InstitutionType.TRAINING_INSTITUTE)
    ncct = create_institution(db_session, "NCCT-ONE", InstitutionType.NCCT)
    admin = create_test_user(
        db_session,
        email="admin@training.example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    trainer = create_test_user(
        db_session,
        email="trainer@training.example.com",
        role_code=RoleCode.TRAINER,
        institution=institute,
    )
    super_admin = create_test_user(
        db_session,
        email="ncct@training.example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=ncct,
    )
    trainee = create_test_user(
        db_session,
        email="trainee@training.example.com",
        role_code=RoleCode.TRAINEE,
    )
    admin_headers = login(client, admin)

    created = client.post(
        "/api/v1/programmes",
        json=programme_payload(),
        headers=admin_headers,
    )
    assert created.status_code == 201
    programme_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    batch = client.post(
        f"/api/v1/programmes/{programme_id}/batches",
        json={
            "name": "First cohort",
            "code": "BATCH-01",
            "capacity": 2,
            "start_date": created.json()["start_date"],
            "end_date": created.json()["end_date"],
            "location": "Training Centre, Pune",
        },
        headers=admin_headers,
    )
    assert batch.status_code == 201
    assignment = client.post(
        f"/api/v1/programmes/batches/{batch.json()['id']}/trainers",
        json={"trainer_id": str(trainer.id)},
        headers=admin_headers,
    )
    assert assignment.status_code == 201
    assert assignment.json()["trainer"]["email"] == trainer.email

    submitted = client.post(f"/api/v1/programmes/{programme_id}/submit", headers=admin_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_approval"

    super_admin_headers = login(client, super_admin)
    rejected = client.post(
        f"/api/v1/programmes/{programme_id}/reject",
        json={"reason": "Clarify the participant outcomes."},
        headers=super_admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    edited = client.patch(
        f"/api/v1/programmes/{programme_id}",
        json={
            "summary": (
                "Practical credit operations with clear workplace outcomes for participants."
            )
        },
        headers=admin_headers,
    )
    assert edited.status_code == 200
    resubmitted = client.post(f"/api/v1/programmes/{programme_id}/submit", headers=admin_headers)
    assert resubmitted.status_code == 200
    approved = client.post(
        f"/api/v1/programmes/{programme_id}/approve",
        headers=super_admin_headers,
    )
    assert approved.status_code == 200
    published = client.post(f"/api/v1/programmes/{programme_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    trainee_headers = login(client, trainee)
    catalogue = client.get("/api/v1/programmes", headers=trainee_headers)
    assert catalogue.status_code == 200
    assert [item["id"] for item in catalogue.json()["items"]] == [programme_id]

    application = client.post(
        f"/api/v1/programmes/{programme_id}/applications",
        json={"statement": "I support a district cooperative and want to improve credit review."},
        headers=trainee_headers,
    )
    assert application.status_code == 201
    duplicate = client.post(
        f"/api/v1/programmes/{programme_id}/applications",
        json={},
        headers=trainee_headers,
    )
    assert duplicate.status_code == 409

    document = client.post(
        f"/api/v1/programmes/applications/{application.json()['id']}/documents",
        data={"document_type": "eligibility"},
        files={"document": ("proof.pdf", b"%PDF-test-content", "application/pdf")},
        headers=trainee_headers,
    )
    assert document.status_code == 201
    assert document.json()["filename"] == "proof.pdf"

    reviewed = client.patch(
        f"/api/v1/programmes/applications/{application.json()['id']}",
        json={"status": "approved", "review_notes": "Eligibility verified."},
        headers=admin_headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"
    tracked = client.get("/api/v1/programmes/applications", headers=trainee_headers)
    assert tracked.json()[0]["status"] == "approved"
    assert tracked.json()[0]["documents"][0]["filename"] == "proof.pdf"

    archived = client.post(f"/api/v1/programmes/{programme_id}/archive", headers=admin_headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    events = set(db_session.scalars(select(AuditLog.event_type)).all())
    assert {
        "programme.created",
        "programme.updated",
        "programme.pending_approval",
        "programme.rejected",
        "programme.approved",
        "programme.published",
        "programme.archived",
        "programme.application_submitted",
        "programme.document_uploaded",
        "programme.application_reviewed",
    }.issubset(events)


def test_capacity_visibility_and_institution_authorization(
    client: TestClient, db_session: Session
) -> None:
    owner_institute = create_institution(db_session, "OWNER", InstitutionType.TRAINING_INSTITUTE)
    other_institute = create_institution(db_session, "OTHER", InstitutionType.TRAINING_INSTITUTE)
    owner = create_test_user(
        db_session,
        email="owner@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=owner_institute,
    )
    other_admin = create_test_user(
        db_session,
        email="other@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=other_institute,
    )
    first = create_test_user(db_session, email="first@example.com", role_code=RoleCode.TRAINEE)
    second = create_test_user(db_session, email="second@example.com", role_code=RoleCode.TRAINEE)
    programme = create_published_programme(
        db_session, owner, owner_institute, code="CAPACITY-ONE", capacity=1
    )
    hidden = create_published_programme(
        db_session,
        owner,
        owner_institute,
        code="NOMINATION-ONLY",
        eligible=[EligibilityType.PACS.value],
    )

    catalogue = client.get("/api/v1/programmes", headers=login(client, first))
    ids = {item["id"] for item in catalogue.json()["items"]}
    assert str(programme.id) in ids
    assert str(hidden.id) not in ids

    forbidden = client.patch(
        f"/api/v1/programmes/{programme.id}",
        json={"title": "Unauthorised change"},
        headers=login(client, other_admin),
    )
    assert forbidden.status_code == 403

    first_application = client.post(
        f"/api/v1/programmes/{programme.id}/applications",
        json={},
        headers=login(client, first),
    )
    second_application = client.post(
        f"/api/v1/programmes/{programme.id}/applications",
        json={},
        headers=login(client, second),
    )
    assert first_application.status_code == second_application.status_code == 201
    owner_headers = login(client, owner)
    first_review = client.patch(
        f"/api/v1/programmes/applications/{first_application.json()['id']}",
        json={"status": "approved"},
        headers=owner_headers,
    )
    second_review = client.patch(
        f"/api/v1/programmes/applications/{second_application.json()['id']}",
        json={"status": "approved"},
        headers=owner_headers,
    )
    assert first_review.status_code == 200
    assert second_review.status_code == 409
    waitlisted = client.patch(
        f"/api/v1/programmes/applications/{second_application.json()['id']}",
        json={"status": "waitlisted"},
        headers=owner_headers,
    )
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"


def test_individual_and_validated_bulk_nominations(client: TestClient, db_session: Session) -> None:
    institute = create_institution(db_session, "DELIVERY", InstitutionType.TRAINING_INSTITUTE)
    nominating = create_institution(db_session, "NOMINATOR", InstitutionType.NOMINATING_INSTITUTION)
    admin = create_test_user(
        db_session,
        email="delivery@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    nominator = create_test_user(
        db_session,
        email="nominator@example.com",
        role_code=RoleCode.NOMINATING_INSTITUTION,
        institution=nominating,
    )
    programme = create_published_programme(
        db_session,
        admin,
        institute,
        code="NOMINATIONS",
        capacity=10,
        eligible=[
            EligibilityType.PACS.value,
            EligibilityType.SHG.value,
            EligibilityType.COOPERATIVE_INSTITUTION.value,
        ],
    )
    headers = login(client, nominator)

    individual = client.post(
        f"/api/v1/programmes/{programme.id}/nominations",
        json={
            "nomination_type": "pacs",
            "candidate_full_name": "Asha Patil",
            "candidate_email": "asha@example.com",
            "member_identifier": "PACS-101",
        },
        headers=headers,
    )
    assert individual.status_code == 201
    assert individual.json()["source"] == "individual"

    csv_content = (
        "full_name,email,phone,member_identifier\n"
        "Neha Rao,neha@example.com,9000000001,SHG-1\n"
        "Meera Shah,meera@example.com,9000000002,SHG-2\n"
    )
    bulk = client.post(
        f"/api/v1/programmes/{programme.id}/nominations/bulk",
        data={"nomination_type": "shg"},
        files={"csv_file": ("nominees.csv", csv_content, "text/csv")},
        headers=headers,
    )
    assert bulk.status_code == 201
    assert bulk.json()["created"] == 2

    invalid_csv = "full_name,email\nOne,duplicate@example.com\nTwo,duplicate@example.com\n"
    invalid = client.post(
        f"/api/v1/programmes/{programme.id}/nominations/bulk",
        data={"nomination_type": "shg"},
        files={"csv_file": ("invalid.csv", invalid_csv, "text/csv")},
        headers=headers,
    )
    assert invalid.status_code == 422
    total = db_session.scalar(select(func.count(ProgrammeNomination.id)))
    assert total == 3
