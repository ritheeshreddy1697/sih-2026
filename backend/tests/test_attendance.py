from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_scoped_token
from app.models import (
    AttendanceCheckIn,
    AttendanceSource,
    AttendanceStatus,
    BatchTrainerAssignment,
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


def build_attendance_scenario(db: Session, suffix: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    institution = Institution(
        code=f"ICM-ATT-{suffix}",
        name=f"ICM Attendance Demonstration {suffix}",
        institution_type=InstitutionType.ICM,
        is_demo=True,
    )
    db.add(institution)
    db.commit()
    admin = create_test_user(
        db,
        email=f"attendance.admin.{suffix.lower()}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    trainer = create_test_user(
        db,
        email=f"attendance.trainer.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    other_trainer = create_test_user(
        db,
        email=f"attendance.other.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    trainee = create_test_user(
        db,
        email=f"attendance.trainee.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    outsider = create_test_user(
        db,
        email=f"attendance.outsider.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    db.add_all(
        [
            TraineeProfile(user_id=trainee.id, is_demo=True),
            TraineeProfile(user_id=outsider.id, is_demo=True),
        ]
    )
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title=f"Attendance programme {suffix}",
        code=f"ATT-{suffix}",
        summary="A demonstration programme for attendance tests.",
        description="Validates secure online and offline attendance workflows.",
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
        name="Morning batch",
        code="MORNING",
        capacity=30,
        start_date=now.date(),
        end_date=(now + timedelta(days=1)).date(),
        location="Room 1",
    )
    db.add(programme)
    db.flush()
    db.add(
        BatchTrainerAssignment(
            batch=batch,
            trainer_id=trainer.id,
            assigned_by_id=admin.id,
        )
    )
    enrollment = ProgrammeEnrollment(
        trainee_id=trainee.id,
        programme=programme,
        batch=batch,
        status=EnrollmentStatus.ENROLLED,
    )
    db.add(enrollment)
    db.commit()
    return {
        "admin": admin,
        "trainer": trainer,
        "other_trainer": other_trainer,
        "trainee": trainee,
        "outsider": outsider,
        "programme": programme,
        "batch": batch,
        "enrollment": enrollment,
        "now": now,
    }


def create_session(
    client: TestClient, scenario: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    headers = login(client, scenario["trainer"])
    response = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={
            "programme_id": str(scenario["programme"].id),
            "batch_id": str(scenario["batch"].id),
            "title": "Opening workshop attendance",
            "starts_at": (scenario["now"] - timedelta(minutes=5)).isoformat(),
            "ends_at": (scenario["now"] + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json(), headers


def register_device(
    client: TestClient, scenario: dict[str, Any], headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, str]]:
    response = client.post(
        "/api/v1/attendance/devices",
        headers=headers,
        json={"name": "Test laptop kiosk"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body, {"X-Kiosk-Token": body["device_token"]}


def test_trainer_scope_and_rotating_session_pairing(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_attendance_scenario(db_session, "SCOPE")
    session, trainer_headers = create_session(client, scenario)

    forbidden = client.post(
        "/api/v1/attendance/sessions",
        headers=login(client, scenario["other_trainer"]),
        json={
            "programme_id": str(scenario["programme"].id),
            "batch_id": str(scenario["batch"].id),
            "title": "Unassigned session",
            "starts_at": scenario["now"].isoformat(),
            "ends_at": (scenario["now"] + timedelta(hours=1)).isoformat(),
        },
    )
    assert forbidden.status_code == 403

    _, kiosk_headers = register_device(client, scenario, trainer_headers)
    qr_response = client.get(
        f"/api/v1/attendance/sessions/{session['id']}/qr", headers=trainer_headers
    )
    assert qr_response.status_code == 200
    assert qr_response.json()["refresh_after_seconds"] < 45

    paired = client.post(
        "/api/v1/attendance/kiosk/pair",
        headers=kiosk_headers,
        json={"session_qr": qr_response.json()["payload"]},
    )
    assert paired.status_code == 200
    assert paired.json()["session_id"] == session["id"]
    expired_qr = create_scoped_token(
        UUID(session["id"]),
        "attendance_session",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    expired = client.post(
        "/api/v1/attendance/kiosk/pair",
        headers=kiosk_headers,
        json={"session_qr": f"NCCT-SESSION:{expired_qr}"},
    )
    assert expired.status_code == 422
    assert client.post(
        "/api/v1/attendance/kiosk/pair",
        headers={"X-Kiosk-Token": "invalid"},
        json={"session_qr": qr_response.json()["payload"]},
    ).status_code == 401


def test_offline_queue_sync_is_idempotent_and_validates_enrolment(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_attendance_scenario(db_session, "SYNC")
    session, trainer_headers = create_session(client, scenario)
    device, kiosk_headers = register_device(client, scenario, trainer_headers)
    trainee_identity = client.get(
        "/api/v1/attendance/identity/me", headers=login(client, scenario["trainee"])
    )
    assert trainee_identity.status_code == 200
    idempotency_key = "a0d37c27-9b7a-47df-a8c6-12b485e21538"
    queued_event = {
        "idempotency_key": idempotency_key,
        "session_id": session["id"],
        "trainee_qr": trainee_identity.json()["qr_payload"],
        "captured_at": scenario["now"].isoformat(),
    }

    first = client.post(
        "/api/v1/attendance/kiosk/check-ins/sync",
        headers=kiosk_headers,
        json={"items": [queued_event]},
    )
    assert first.status_code == 200
    assert first.json()["accepted"] == 1
    assert first.json()["items"][0]["result"] == "created"

    replay = client.post(
        "/api/v1/attendance/kiosk/check-ins/sync",
        headers=kiosk_headers,
        json={"items": [queued_event]},
    )
    assert replay.status_code == 200
    assert replay.json()["accepted"] == 0
    assert replay.json()["duplicates"] == 1
    assert replay.json()["items"][0]["result"] == "duplicate"

    second_scan = client.post(
        "/api/v1/attendance/kiosk/check-ins/sync",
        headers=kiosk_headers,
        json={
            "items": [
                {
                    **queued_event,
                    "idempotency_key": "e7105115-8272-4ae1-a9fa-7c13cf2a7f05",
                }
            ]
        },
    )
    assert second_scan.status_code == 200
    assert second_scan.json()["items"][0]["result"] == "already_checked_in"

    count = db_session.scalar(select(func.count(AttendanceCheckIn.id)))
    assert count == 1
    check_in = db_session.scalar(select(AttendanceCheckIn))
    assert check_in is not None
    assert check_in.kiosk_device_id == UUID(device["id"])
    assert check_in.source == AttendanceSource.KIOSK
    assert check_in.captured_at is not None

    outsider_identity = client.get(
        "/api/v1/attendance/identity/me", headers=login(client, scenario["outsider"])
    )
    rejected = client.post(
        "/api/v1/attendance/kiosk/check-ins/sync",
        headers=kiosk_headers,
        json={
            "items": [
                {
                    **queued_event,
                    "idempotency_key": "33c20ee0-a409-4ba5-966d-06ca18c1a557",
                    "trainee_qr": outsider_identity.json()["qr_payload"],
                }
            ]
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["rejected"] == 1
    assert "not enrolled" in rejected.json()["items"][0]["detail"]
    assert db_session.scalar(select(func.count(AttendanceCheckIn.id))) == 1


def test_manual_correction_requires_separate_approval_and_updates_report(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_attendance_scenario(db_session, "CORRECT")
    session, trainer_headers = create_session(client, scenario)
    correction = client.post(
        f"/api/v1/attendance/sessions/{session['id']}/corrections",
        headers=trainer_headers,
        json={
            "enrollment_id": str(scenario["enrollment"].id),
            "requested_status": "present",
            "reason": "Trainee attended but the camera was temporarily unavailable.",
        },
    )
    assert correction.status_code == 201, correction.text
    assert correction.json()["approval_status"] == "pending"

    trainer_review = client.patch(
        f"/api/v1/attendance/corrections/{correction.json()['id']}",
        headers=trainer_headers,
        json={"decision": "approved", "review_notes": "Self approval attempt"},
    )
    assert trainer_review.status_code == 403

    approved = client.patch(
        f"/api/v1/attendance/corrections/{correction.json()['id']}",
        headers=login(client, scenario["admin"]),
        json={"decision": "approved", "review_notes": "Verified against trainer register."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"

    check_in = db_session.scalar(select(AttendanceCheckIn))
    assert check_in is not None
    assert check_in.status == AttendanceStatus.PRESENT
    assert check_in.source == AttendanceSource.MANUAL

    report = client.get(
        f"/api/v1/attendance/sessions/{session['id']}/report", headers=trainer_headers
    )
    assert report.status_code == 200
    assert report.json()["present_count"] == 1
    assert report.json()["attendance_percent"] == 100.0
    assert report.json()["rows"][0]["source"] == "manual"
