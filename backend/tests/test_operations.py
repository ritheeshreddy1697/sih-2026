from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
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


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_operations_scenario(db: Session, suffix: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    institution = Institution(
        code=f"ICM-OPS-{suffix}",
        name=f"ICM Operations Demonstration {suffix}",
        institution_type=InstitutionType.ICM,
        is_demo=True,
    )
    other_institution = Institution(
        code=f"RICM-OPS-{suffix}",
        name=f"Other Operations Institute {suffix}",
        institution_type=InstitutionType.RICM,
        is_demo=True,
    )
    db.add_all([institution, other_institution])
    db.commit()
    admin = create_test_user(
        db,
        email=f"operations.admin.{suffix.lower()}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    other_admin = create_test_user(
        db,
        email=f"operations.other.{suffix.lower()}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=other_institution,
    )
    super_admin = create_test_user(
        db,
        email=f"operations.ncct.{suffix.lower()}@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=other_institution,
    )
    trainer = create_test_user(
        db,
        email=f"operations.trainer.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    other_trainer = create_test_user(
        db,
        email=f"operations.trainer2.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    trainee = create_test_user(
        db,
        email=f"operations.trainee.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    other_trainee = create_test_user(
        db,
        email=f"operations.trainee2.{suffix.lower()}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    assert trainee.profile is not None and other_trainee.profile is not None
    trainee.profile.full_name = "First Operations Trainee"
    other_trainee.profile.full_name = "Second Operations Trainee"
    db.commit()
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title=f"Operations programme {suffix}",
        code=f"OPS-{suffix}",
        summary="A fictional programme for operations testing.",
        description="Validates timetable, accommodation and participant logistics.",
        mode=ProgrammeMode.OFFLINE,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Open to demonstration trainees.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=20,
        location="Demonstration campus",
        language="English",
        duration_days=3,
        application_deadline=now + timedelta(days=1),
        start_date=(now + timedelta(days=2)).date(),
        end_date=(now + timedelta(days=4)).date(),
        published_at=now,
    )
    batch = ProgrammeBatch(
        programme=programme,
        name="Residential batch",
        code="RESIDENTIAL",
        capacity=20,
        start_date=programme.start_date,
        end_date=programme.end_date,
        location="Demonstration campus",
    )
    first_enrollment = ProgrammeEnrollment(
        trainee_id=trainee.id,
        programme=programme,
        batch=batch,
        status=EnrollmentStatus.ENROLLED,
    )
    second_enrollment = ProgrammeEnrollment(
        trainee_id=other_trainee.id,
        programme=programme,
        batch=batch,
        status=EnrollmentStatus.ENROLLED,
    )
    db.add_all([programme, first_enrollment, second_enrollment])
    db.commit()
    return {
        "institution": institution,
        "other_institution": other_institution,
        "admin": admin,
        "other_admin": other_admin,
        "super_admin": super_admin,
        "trainer": trainer,
        "other_trainer": other_trainer,
        "trainee": trainee,
        "other_trainee": other_trainee,
        "programme": programme,
        "batch": batch,
        "first_enrollment": first_enrollment,
        "second_enrollment": second_enrollment,
        "now": now,
    }


def create_rooms(
    client: TestClient, scenario: dict[str, Any], headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    venue_response = client.post(
        "/api/v1/operations/venues",
        headers=headers,
        json={
            "institution_id": str(scenario["institution"].id),
            "name": "Demonstration Learning Centre",
            "address": "1 Training Road, Demonstration City",
            "capacity": 60,
        },
    )
    assert venue_response.status_code == 201, venue_response.text
    venue = venue_response.json()
    rooms = []
    for name, code in (("Room A", "ROOM-A"), ("Room B", "ROOM-B")):
        response = client.post(
            "/api/v1/operations/classrooms",
            headers=headers,
            json={
                "venue_id": venue["id"],
                "name": name,
                "code": code,
                "capacity": 20,
                "equipment": "Projector and accessible seating",
            },
        )
        assert response.status_code == 201, response.text
        rooms.append(response.json())
    return venue, rooms[0], rooms[1]


def session_payload(
    scenario: dict[str, Any], venue_id: str, classroom_id: str, trainer_id: str
) -> dict[str, Any]:
    starts_at = scenario["now"] + timedelta(days=2, hours=2)
    return {
        "programme_id": str(scenario["programme"].id),
        "batch_id": str(scenario["batch"].id),
        "trainer_id": trainer_id,
        "venue_id": venue_id,
        "classroom_id": classroom_id,
        "title": "Cooperative operations workshop",
        "description": "Fictional scheduled learning session.",
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=2)).isoformat(),
    }


def test_institution_scope_and_trainee_self_view(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_operations_scenario(db_session, "SCOPE")
    admin_headers = login(client, scenario["admin"])
    workspace = client.get("/api/v1/operations/workspace", headers=admin_headers)
    assert workspace.status_code == 200
    assert workspace.json()["institution"]["id"] == str(scenario["institution"].id)

    outside = client.get(
        "/api/v1/operations/workspace",
        headers=login(client, scenario["other_admin"]),
        params={"institution_id": str(scenario["institution"].id)},
    )
    assert outside.status_code == 403
    platform = client.get(
        "/api/v1/operations/workspace",
        headers=login(client, scenario["super_admin"]),
        params={"institution_id": str(scenario["institution"].id)},
    )
    assert platform.status_code == 200

    trainee_headers = login(client, scenario["trainee"])
    assert client.get("/api/v1/operations/workspace", headers=trainee_headers).status_code == 403
    own = client.get("/api/v1/operations/me", headers=trainee_headers)
    assert own.status_code == 200
    assert [item["enrollment_id"] for item in own.json()["programmes"]] == [
        str(scenario["first_enrollment"].id)
    ]


def test_timetable_rejects_trainer_and_classroom_double_booking(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_operations_scenario(db_session, "SCHEDULE")
    headers = login(client, scenario["admin"])
    venue, room_a, room_b = create_rooms(client, scenario, headers)
    first_payload = session_payload(
        scenario, venue["id"], room_a["id"], str(scenario["trainer"].id)
    )
    created = client.post(
        "/api/v1/operations/timetable", headers=headers, json=first_payload
    )
    assert created.status_code == 201, created.text

    trainer_conflict = {
        **first_payload,
        "classroom_id": room_b["id"],
        "title": "Conflicting trainer workshop",
    }
    response = client.post(
        "/api/v1/operations/timetable", headers=headers, json=trainer_conflict
    )
    assert response.status_code == 409
    assert "Trainer" in response.json()["detail"]

    classroom_conflict = {
        **first_payload,
        "trainer_id": str(scenario["other_trainer"].id),
        "title": "Conflicting classroom workshop",
    }
    response = client.post(
        "/api/v1/operations/timetable", headers=headers, json=classroom_conflict
    )
    assert response.status_code == 409
    assert "Classroom" in response.json()["detail"]

    valid_parallel = {
        **classroom_conflict,
        "classroom_id": room_b["id"],
        "title": "Parallel room workshop",
    }
    response = client.post(
        "/api/v1/operations/timetable", headers=headers, json=valid_parallel
    )
    assert response.status_code == 201, response.text

    own = client.get(
        "/api/v1/operations/me", headers=login(client, scenario["trainee"])
    )
    assert len(own.json()["programmes"][0]["timetable"]) == 2


def test_bed_double_booking_and_check_in_out(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_operations_scenario(db_session, "HOSTEL")
    headers = login(client, scenario["admin"])
    building_response = client.post(
        "/api/v1/operations/hostels",
        headers=headers,
        json={
            "institution_id": str(scenario["institution"].id),
            "name": "Demonstration Hostel",
            "address": "2 Training Road, Demonstration City",
            "contact_phone": "+91 90000 00000",
        },
    )
    assert building_response.status_code == 201, building_response.text
    room_response = client.post(
        f"/api/v1/operations/hostels/{building_response.json()['id']}/rooms",
        headers=headers,
        json={
            "room_number": "101",
            "floor": "Ground",
            "capacity": 2,
            "bed_numbers": ["A", "B"],
            "is_accessible": True,
        },
    )
    assert room_response.status_code == 201, room_response.text
    beds = room_response.json()["beds"]
    base = {
        "bed_id": beds[0]["id"],
        "enrollment_id": str(scenario["first_enrollment"].id),
        "start_date": scenario["programme"].start_date.isoformat(),
        "end_date": scenario["programme"].end_date.isoformat(),
    }
    allocation = client.post(
        "/api/v1/operations/bed-allocations", headers=headers, json=base
    )
    assert allocation.status_code == 201, allocation.text

    occupied_bed = client.post(
        "/api/v1/operations/bed-allocations",
        headers=headers,
        json={
            **base,
            "enrollment_id": str(scenario["second_enrollment"].id),
        },
    )
    assert occupied_bed.status_code == 409
    duplicate_trainee = client.post(
        "/api/v1/operations/bed-allocations",
        headers=headers,
        json={**base, "bed_id": beds[1]["id"]},
    )
    assert duplicate_trainee.status_code == 409

    allocation_id = allocation.json()["id"]
    checked_in = client.post(
        f"/api/v1/operations/bed-allocations/{allocation_id}/check-in",
        headers=headers,
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "checked_in"
    checked_out = client.post(
        f"/api/v1/operations/bed-allocations/{allocation_id}/check-out",
        headers=headers,
    )
    assert checked_out.status_code == 200
    assert checked_out.json()["status"] == "checked_out"


def test_participant_logistics_materials_and_issue_privacy(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_operations_scenario(db_session, "PARTICIPANT")
    headers = login(client, scenario["admin"])
    enrollment_id = str(scenario["first_enrollment"].id)
    logistics = client.put(
        f"/api/v1/operations/enrollments/{enrollment_id}/logistics",
        headers=headers,
        json={
            "meal_preference": "vegetarian",
            "dietary_notes": "No peanuts",
            "arrival_mode": "train",
            "arrival_details": "Demonstration Express, coach D1",
            "arrival_at": (scenario["now"] + timedelta(days=1)).isoformat(),
            "departure_mode": "bus",
            "departure_details": "Institute shuttle",
            "departure_at": (scenario["now"] + timedelta(days=5)).isoformat(),
            "emergency_contact_name": "Demonstration Contact",
            "emergency_contact_phone": "+91 91111 11111",
            "emergency_contact_relationship": "Sibling",
        },
    )
    assert logistics.status_code == 200, logistics.text

    material = client.post(
        "/api/v1/operations/materials",
        headers=headers,
        json={
            "programme_id": str(scenario["programme"].id),
            "name": "Demonstration workbook",
            "description": "Fictional participant workbook.",
            "quantity_available": 20,
        },
    )
    assert material.status_code == 201, material.text
    distributed = client.post(
        f"/api/v1/operations/materials/{material.json()['id']}/distributions",
        headers=headers,
        json={"enrollment_id": enrollment_id, "quantity": 1},
    )
    assert distributed.status_code == 201, distributed.text
    second_distribution = client.post(
        f"/api/v1/operations/materials/{material.json()['id']}/distributions",
        headers=headers,
        json={
            "enrollment_id": str(scenario["second_enrollment"].id),
            "quantity": 1,
        },
    )
    assert second_distribution.status_code == 201, second_distribution.text

    trainee_headers = login(client, scenario["trainee"])
    issue = client.post(
        "/api/v1/operations/issues/me",
        headers=trainee_headers,
        json={
            "enrollment_id": enrollment_id,
            "issue_type": "participant",
            "priority": "medium",
            "title": "Dietary preference confirmation",
            "description": "Please confirm the allergy note with the kitchen.",
            "location": "Dining hall",
        },
    )
    assert issue.status_code == 201, issue.text
    impersonation = client.post(
        "/api/v1/operations/issues/me",
        headers=login(client, scenario["other_trainee"]),
        json={
            "enrollment_id": enrollment_id,
            "issue_type": "participant",
            "title": "Not my report",
            "description": "This enrollment belongs to another trainee.",
        },
    )
    assert impersonation.status_code == 403

    own = client.get("/api/v1/operations/me", headers=trainee_headers)
    programme = own.json()["programmes"][0]
    assert programme["logistics"]["dietary_notes"] == "No peanuts"
    assert programme["materials"][0]["name"] == "Demonstration workbook"
    assert [row["trainee_name"] for row in programme["materials"][0]["distributions"]] == [
        "First Operations Trainee"
    ]
    assert programme["issues"][0]["id"] == issue.json()["id"]

    other = client.get(
        "/api/v1/operations/me", headers=login(client, scenario["other_trainee"])
    )
    assert other.json()["programmes"][0]["logistics"] is None
    assert len(other.json()["programmes"][0]["materials"]) == 1
    assert [
        row["trainee_name"]
        for row in other.json()["programmes"][0]["materials"][0]["distributions"]
    ] == ["Second Operations Trainee"]
    assert other.json()["programmes"][0]["issues"] == []
