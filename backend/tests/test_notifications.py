from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Institution, InstitutionType, RoleCode, User
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


def test_institute_admin_sends_scoped_notifications(
    client: TestClient, db_session: Session
) -> None:
    institute = create_institution(db_session, "ICM-NOTIFY", InstitutionType.ICM)
    outside = create_institution(db_session, "ICM-OUTSIDE", InstitutionType.ICM)
    admin = create_test_user(
        db_session,
        email="notify.admin@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    trainee = create_test_user(
        db_session,
        email="notify.trainee@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institute,
    )
    trainer = create_test_user(
        db_session,
        email="notify.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=institute,
    )
    outside_trainee = create_test_user(
        db_session,
        email="notify.outside@example.com",
        role_code=RoleCode.TRAINEE,
        institution=outside,
    )
    admin_headers = login(client, admin)

    sent = client.post(
        "/api/v1/notifications",
        headers=admin_headers,
        json={
            "target_type": "trainees",
            "target_ids": [str(trainee.id)],
            "title": "Class timing updated",
            "description": "Tomorrow's class begins at 10:00 AM.",
        },
    )
    assert sent.status_code == 201
    assert sent.json()["sent_count"] == 1

    trainee_headers = login(client, trainee)
    inbox = client.get("/api/v1/notifications", headers=trainee_headers)
    assert inbox.status_code == 200
    assert inbox.json()["unread_count"] == 1
    assert inbox.json()["items"][0]["title"] == "Class timing updated"

    marked = client.patch(
        f"/api/v1/notifications/{sent.json()['id']}/read", headers=trainee_headers
    )
    assert marked.status_code == 200
    assert marked.json()["unread"] is False
    assert client.get("/api/v1/notifications", headers=trainee_headers).json()[
        "unread_count"
    ] == 0

    trainer_send = client.post(
        "/api/v1/notifications",
        headers=admin_headers,
        json={
            "target_type": "trainers",
            "target_ids": [str(trainer.id)],
            "title": "Faculty meeting",
            "description": "Please attend the faculty meeting at 4:00 PM.",
        },
    )
    assert trainer_send.status_code == 201
    assert client.get(
        "/api/v1/notifications", headers=login(client, trainer)
    ).json()["items"][0]["title"] == "Faculty meeting"

    outside_send = client.post(
        "/api/v1/notifications",
        headers=admin_headers,
        json={
            "target_type": "trainees",
            "target_ids": [str(outside_trainee.id)],
            "title": "Not allowed",
            "description": "This message must not cross institution scope.",
        },
    )
    assert outside_send.status_code == 403

    unauthorized = client.post(
        "/api/v1/notifications",
        headers=trainee_headers,
        json={
            "target_type": "trainees",
            "target_ids": [str(trainee.id)],
            "title": "Not allowed",
            "description": "Trainees cannot send administrative notifications.",
        },
    )
    assert unauthorized.status_code == 403


def test_super_admin_sends_notifications_to_institution_administrators(
    client: TestClient, db_session: Session
) -> None:
    ncct = create_institution(db_session, "NCCT-NOTIFY", InstitutionType.NCCT)
    institute = create_institution(
        db_session, "RICM-NOTIFY", InstitutionType.RICM, parent=ncct
    )
    super_admin = create_test_user(
        db_session,
        email="notify.super@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=ncct,
    )
    institute_admin = create_test_user(
        db_session,
        email="notify.institute@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institute,
    )
    trainer = create_test_user(
        db_session,
        email="notify.institute.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=institute,
    )

    sent = client.post(
        "/api/v1/notifications",
        headers=login(client, super_admin),
        json={
            "target_type": "institutions",
            "target_ids": [str(institute.id)],
            "title": "Monthly report deadline",
            "description": "Submit the institution report by Friday.",
        },
    )
    assert sent.status_code == 201
    assert sent.json()["sent_count"] == 1

    admin_inbox = client.get(
        "/api/v1/notifications", headers=login(client, institute_admin)
    )
    assert admin_inbox.json()["items"][0]["title"] == "Monthly report deadline"
    trainer_inbox = client.get("/api/v1/notifications", headers=login(client, trainer))
    assert trainer_inbox.json()["items"] == []
