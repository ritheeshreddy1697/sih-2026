from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    BatchTrainerAssignment,
    ConsentRecord,
    EligibilityType,
    EnrollmentStatus,
    Institution,
    InstitutionType,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    RoleCode,
    User,
)
from tests.conftest import create_test_user


def create_institution(
    db: Session,
    code: str,
    institution_type: InstitutionType,
    parent: Institution | None = None,
) -> Institution:
    institution = Institution(
        code=code,
        name=f"{code} Demonstration Institution",
        institution_type=institution_type,
        parent=parent,
        is_demo=True,
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


def test_trainee_can_manage_complete_private_profile(
    client: TestClient, db_session: Session
) -> None:
    institution = create_institution(db_session, "PACS-SELF", InstitutionType.PACS)
    trainee = create_test_user(
        db_session,
        email="profile.trainee@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    headers = login(client, trainee)

    initial = client.get("/api/v1/profiles/me", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["user_id"] == str(trainee.id)
    assert initial.json()["completion_percent"] == 10

    personal = client.patch(
        "/api/v1/profiles/me",
        headers=headers,
        json={
            "full_name": "Asha Test",
            "phone": "9000000001",
            "date_of_birth": "1997-04-15",
            "address_line": "Demonstration address",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001",
            "preferred_language": "Marathi",
            "preferred_location": "Pune",
            "career_interests": "Cooperative finance",
            "skills": ["Bookkeeping", "Member services", "Bookkeeping"],
        },
    )
    assert personal.status_code == 200
    assert personal.json()["skills"] == ["Bookkeeping", "Member services"]

    education = client.post(
        "/api/v1/profiles/me/education",
        headers=headers,
        json={
            "qualification": "B.Com",
            "institution_name": "Demonstration College",
            "completion_year": 2019,
            "is_highest_qualification": True,
        },
    )
    assert education.status_code == 201
    membership = client.post(
        "/api/v1/profiles/me/memberships",
        headers=headers,
        json={
            "institution_name": "PACS Demonstration Society",
            "membership_type": "Member",
            "joined_on": date(2021, 1, 1).isoformat(),
        },
    )
    assert membership.status_code == 201

    invalid_document = client.post(
        "/api/v1/profiles/me/documents",
        headers=headers,
        data={"document_type": "membership"},
        files={"document": ("record.txt", b"invalid", "text/plain")},
    )
    assert invalid_document.status_code == 422
    document = client.post(
        "/api/v1/profiles/me/documents",
        headers=headers,
        data={"document_type": "membership"},
        files={"document": ("membership.pdf", b"%PDF-test", "application/pdf")},
    )
    assert document.status_code == 201
    assert document.json()["completion_percent"] == 100
    assert document.json()["documents"][0]["validation_status"] == "pending"

    consents = client.put(
        "/api/v1/profiles/me/consents",
        headers=headers,
        json={
            "placement_visibility_consent": True,
            "communication_consent": False,
            "data_sharing_consent": True,
        },
    )
    assert consents.status_code == 200
    assert consents.json()["consent_preferences"]["data_sharing_consent"] is True
    assert db_session.scalar(
        select(ConsentRecord).where(
            ConsentRecord.user_id == trainee.id,
            ConsentRecord.consent_type == "data_sharing_consent",
        )
    )
    events = set(
        db_session.scalars(select(AuditLog.event_type).where(AuditLog.user_id == trainee.id)).all()
    )
    assert {
        "profile.personal_updated",
        "profile.education_added",
        "profile.membership_added",
        "profile.document_uploaded",
        "profile.consents_updated",
    }.issubset(events)


def test_administrator_scope_search_pagination_and_document_validation(
    client: TestClient, db_session: Session
) -> None:
    ncct = create_institution(db_session, "NCCT-PROFILE", InstitutionType.NCCT)
    institute = create_institution(db_session, "ICM-PROFILE", InstitutionType.ICM, parent=ncct)
    child = create_institution(db_session, "PACS-CHILD", InstitutionType.PACS, parent=institute)
    outside = create_institution(db_session, "PACS-OUT", InstitutionType.PACS, parent=ncct)
    admin = create_test_user(
        db_session,
        email="profile.admin@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    first = create_test_user(
        db_session,
        email="asha.profile@example.com",
        role_code=RoleCode.TRAINEE,
        institution=child,
    )
    second = create_test_user(
        db_session,
        email="beena.profile@example.com",
        role_code=RoleCode.TRAINEE,
        institution=child,
    )
    outside_trainee = create_test_user(
        db_session,
        email="outside.profile@example.com",
        role_code=RoleCode.TRAINEE,
        institution=outside,
    )
    trainer = create_test_user(
        db_session,
        email="meera.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=institute,
    )
    trainer.profile.full_name = "Meera Trainer"
    outside_trainer = create_test_user(
        db_session,
        email="outside.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=outside,
    )
    db_session.commit()
    first_headers = login(client, first)
    client.patch(
        "/api/v1/profiles/me",
        headers=first_headers,
        json={"full_name": "Asha Search", "state": "Maharashtra", "skills": ["Audit"]},
    )
    upload = client.post(
        "/api/v1/profiles/me/documents",
        headers=first_headers,
        data={"document_type": "identity"},
        files={"document": ("identity.png", b"\x89PNG\r\n\x1a\nDemo", "image/png")},
    )
    document_id = upload.json()["documents"][0]["id"]
    admin_headers = login(client, admin)

    page = client.get(
        "/api/v1/profiles/trainees",
        params={"q": "profile", "page": 1, "page_size": 1},
        headers=admin_headers,
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["pages"] == 2
    filtered = client.get(
        "/api/v1/profiles/trainees",
        params={"skill": "Audit", "state": "Maharashtra"},
        headers=admin_headers,
    )
    assert [item["email"] for item in filtered.json()["items"]] == [first.email]
    trainee_by_id = client.get(
        "/api/v1/profiles/trainees",
        params={"q": str(first.id)},
        headers=admin_headers,
    )
    assert [item["user_id"] for item in trainee_by_id.json()["items"]] == [str(first.id)]

    trainers_by_name = client.get(
        "/api/v1/profiles/trainers",
        params={"q": "Meera"},
        headers=admin_headers,
    )
    assert trainers_by_name.status_code == 200
    assert [item["user_id"] for item in trainers_by_name.json()["items"]] == [str(trainer.id)]
    trainers_by_id = client.get(
        "/api/v1/profiles/trainers",
        params={"q": str(trainer.id)},
        headers=admin_headers,
    )
    assert [item["user_id"] for item in trainers_by_id.json()["items"]] == [str(trainer.id)]
    outside_trainer_search = client.get(
        "/api/v1/profiles/trainers",
        params={"q": str(outside_trainer.id)},
        headers=admin_headers,
    )
    assert outside_trainer_search.json()["items"] == []

    detail = client.get(f"/api/v1/profiles/trainees/{first.id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["email"] == first.email
    forbidden_scope = client.get(
        f"/api/v1/profiles/trainees/{outside_trainee.id}", headers=admin_headers
    )
    assert forbidden_scope.status_code == 404

    validated = client.patch(
        f"/api/v1/profiles/documents/{document_id}/validation",
        headers=admin_headers,
        json={"status": "verified", "notes": "Checked for this test."},
    )
    assert validated.status_code == 200
    assert validated.json()["validation_status"] == "verified"

    download = client.get(f"/api/v1/profiles/documents/{document_id}", headers=admin_headers)
    assert download.status_code == 200
    assert download.content == b"\x89PNG\r\n\x1a\nDemo"
    administrative_events = set(
        db_session.scalars(select(AuditLog.event_type).where(AuditLog.user_id == admin.id)).all()
    )
    assert {
        "profile.administrator_viewed",
        "profile.document_validated",
        "profile.document_downloaded",
    }.issubset(administrative_events)

    trainee_forbidden = client.get("/api/v1/profiles/trainees", headers=first_headers)
    assert trainee_forbidden.status_code == 403
    assert second.id != outside_trainee.id


def test_trainer_can_list_only_trainees_in_assigned_batches(
    client: TestClient, db_session: Session
) -> None:
    institution = create_institution(db_session, "ICM-TRAINER", InstitutionType.ICM)
    admin = create_test_user(
        db_session,
        email="assignment.admin@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    trainer = create_test_user(
        db_session,
        email="assignment.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    assigned = create_test_user(
        db_session,
        email="assigned.trainee@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    assigned.profile.full_name = "Assigned Asha"
    unassigned = create_test_user(
        db_session,
        email="unassigned.trainee@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    now = datetime.now(UTC)
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title="Assigned Trainer Programme",
        code="ASSIGNED-TRAINER",
        summary="Programme used to verify trainer-scoped trainee access.",
        description="Trainer assignment test programme.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Open for testing.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=20,
        location="Training centre",
        language="English",
        duration_days=5,
        application_deadline=now + timedelta(days=10),
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=25),
        published_at=now,
    )
    batch = ProgrammeBatch(
        programme=programme,
        name="Assigned batch",
        code="BATCH-1",
        capacity=20,
        start_date=programme.start_date,
        end_date=programme.end_date,
        location="Training centre",
    )
    db_session.add_all([programme, batch])
    db_session.flush()
    db_session.add_all(
        [
            BatchTrainerAssignment(
                batch_id=batch.id,
                trainer_id=trainer.id,
                assigned_by_id=admin.id,
            ),
            ProgrammeEnrollment(
                trainee_id=assigned.id,
                programme_id=programme.id,
                batch_id=batch.id,
                status=EnrollmentStatus.ENROLLED,
            ),
        ]
    )
    db_session.commit()
    headers = login(client, trainer)

    directory = client.get("/api/v1/profiles/trainees", headers=headers)
    assert directory.status_code == 200
    assert [item["user_id"] for item in directory.json()["items"]] == [str(assigned.id)]

    by_name = client.get(
        "/api/v1/profiles/trainees", params={"q": "Assigned Asha"}, headers=headers
    )
    assert [item["user_id"] for item in by_name.json()["items"]] == [str(assigned.id)]
    by_id = client.get(
        "/api/v1/profiles/trainees", params={"q": str(assigned.id)}, headers=headers
    )
    assert [item["user_id"] for item in by_id.json()["items"]] == [str(assigned.id)]
    unassigned_search = client.get(
        "/api/v1/profiles/trainees", params={"q": str(unassigned.id)}, headers=headers
    )
    assert unassigned_search.json()["items"] == []

    private_profile = client.get(
        f"/api/v1/profiles/trainees/{assigned.id}", headers=headers
    )
    assert private_profile.status_code == 403


def test_ncct_can_manage_hierarchy_and_institute_admin_is_scoped(
    client: TestClient, db_session: Session
) -> None:
    ncct = create_institution(db_session, "NCCT-HIER", InstitutionType.NCCT)
    institute = create_institution(db_session, "RICM-HIER", InstitutionType.RICM, parent=ncct)
    other = create_institution(db_session, "ICM-OTHER", InstitutionType.ICM, parent=ncct)
    ncct_admin = create_test_user(
        db_session,
        email="ncct.hierarchy@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=ncct,
    )
    institute_admin = create_test_user(
        db_session,
        email="ricm.hierarchy@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )

    created = client.post(
        "/api/v1/profiles/institutions",
        headers=login(client, ncct_admin),
        json={
            "name": "Demonstration Dairy Cooperative",
            "code": "DAIRY-NEW-DEMO",
            "institution_type": "dairy_cooperative",
            "parent_id": str(institute.id),
            "state": "Karnataka",
        },
    )
    assert created.status_code == 201
    assert created.json()["parent"]["id"] == str(institute.id)
    assert created.json()["is_demo"] is False

    scoped = client.get(
        "/api/v1/profiles/institutions",
        headers=login(client, institute_admin),
    )
    assert scoped.status_code == 200
    ids = {item["id"] for item in scoped.json()["items"]}
    assert str(institute.id) in ids
    assert created.json()["id"] in ids
    assert str(other.id) not in ids

    forbidden_create = client.post(
        "/api/v1/profiles/institutions",
        headers=login(client, institute_admin),
        json={
            "name": "Unauthorized Cooperative",
            "code": "UNAUTHORIZED-COOP",
            "institution_type": "pacs",
            "parent_id": str(institute.id),
        },
    )
    assert forbidden_create.status_code == 403

    outside_update = client.patch(
        f"/api/v1/profiles/institutions/{other.id}",
        headers=login(client, institute_admin),
        json={"name": "Not allowed"},
    )
    assert outside_update.status_code == 403
