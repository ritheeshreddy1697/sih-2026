from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AttendanceCheckIn,
    AttendanceSource,
    AuditLog,
    BiometricChallengeType,
    BiometricEnrollment,
    BiometricVerification,
    BiometricVerificationStatus,
    ConsentRecord,
)
from app.services import biometrics as biometric_service
from app.services.face_verification import (
    DemoFaceVerificationProvider,
    FaceCaptureAnalysis,
    LivenessCheckFailed,
)
from tests.test_attendance import (
    build_attendance_scenario,
    create_session,
    login,
    register_device,
)


def camera_frames(*, subject: str = "primary", moving: bool = True) -> list[bytes]:
    result: list[bytes] = []
    offsets = (-12, 12, 0) if moving else (0, 0, 0)
    for offset in offsets:
        image = Image.new("RGB", (240, 180), (226, 232, 240))
        drawing = ImageDraw.Draw(image)
        if subject == "primary":
            drawing.ellipse((68 + offset, 25, 172 + offset, 160), fill=(174, 116, 82))
            drawing.ellipse((92 + offset, 72, 102 + offset, 82), fill=(20, 25, 35))
            drawing.ellipse((138 + offset, 72, 148 + offset, 82), fill=(20, 25, 35))
            drawing.arc((100 + offset, 92, 143 + offset, 132), 10, 170, fill=(90, 30, 30), width=4)
        else:
            drawing.rectangle((45 + offset, 30, 195 + offset, 155), fill=(55, 92, 170))
            drawing.line((60 + offset, 45, 180 + offset, 140), fill=(245, 220, 50), width=16)
            drawing.line((180 + offset, 45, 60 + offset, 140), fill=(245, 220, 50), width=16)
        output = io.BytesIO()
        image.save(output, format="PNG")
        result.append(output.getvalue())
    return result


def multipart_frames(frames: list[bytes]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [
        ("frames", (f"frame-{index}.png", frame, "image/png"))
        for index, frame in enumerate(frames, start=1)
    ]


def enroll_trainee(
    client: TestClient,
    scenario: dict[str, Any],
    frames: list[bytes] | None = None,
) -> dict[str, Any]:
    headers = login(client, scenario["trainee"])
    challenge = client.post(
        "/api/v1/attendance/biometrics/enrollment/challenge", headers=headers
    )
    assert challenge.status_code == 201, challenge.text
    response = client.post(
        "/api/v1/attendance/biometrics/enrollment",
        headers=headers,
        data={"challenge_id": challenge.json()["id"], "consent_granted": "true"},
        files=multipart_frames(frames or camera_frames()),
    )
    assert response.status_code == 200, response.text
    return response.json()


def kiosk_challenge(
    client: TestClient,
    scenario: dict[str, Any],
    session: dict[str, Any],
    kiosk_headers: dict[str, str],
) -> dict[str, Any]:
    identity = client.get(
        "/api/v1/attendance/identity/me", headers=login(client, scenario["trainee"])
    )
    response = client.post(
        "/api/v1/attendance/kiosk/biometrics/challenge",
        headers=kiosk_headers,
        json={
            "session_id": session["id"],
            "identity_code": identity.json()["identity_code"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


class ControlledProvider:
    name = DemoFaceVerificationProvider.name
    model_version = DemoFaceVerificationProvider.model_version
    is_demo = True

    def __init__(self, confidence: float) -> None:
        self.confidence = confidence

    def analyze(self, frames: list[bytes], challenge_type: object) -> FaceCaptureAnalysis:
        return FaceCaptureAnalysis(embedding=(1.0, 0.0), liveness_score=0.2, quality_score=0.8)

    def compare(self, enrolled: tuple[float, ...], candidate: tuple[float, ...]) -> float:
        return self.confidence


def test_demo_provider_rejects_static_frame_spoof() -> None:
    provider = DemoFaceVerificationProvider(liveness_threshold=0.025)
    static = camera_frames(moving=False)[0]
    with pytest.raises(LivenessCheckFailed):
        provider.analyze(
            [static, static, static],
            BiometricChallengeType.TURN_HEAD,
        )


def test_enrollment_requires_consent_encrypts_and_supports_deletion(
    client: TestClient,
    db_session: Session,
) -> None:
    scenario = build_attendance_scenario(db_session, "BIO-CONSENT")
    headers = login(client, scenario["trainee"])
    challenge = client.post(
        "/api/v1/attendance/biometrics/enrollment/challenge", headers=headers
    )
    denied = client.post(
        "/api/v1/attendance/biometrics/enrollment",
        headers=headers,
        data={"challenge_id": challenge.json()["id"], "consent_granted": "false"},
        files=multipart_frames(camera_frames()),
    )
    assert denied.status_code == 422
    assert "consent" in denied.json()["detail"].lower()

    enrolled = client.post(
        "/api/v1/attendance/biometrics/enrollment",
        headers=headers,
        data={"challenge_id": challenge.json()["id"], "consent_granted": "true"},
        files=multipart_frames(camera_frames()),
    )
    assert enrolled.status_code == 200, enrolled.text
    assert enrolled.json()["enrolled"] is True
    assert enrolled.json()["is_demo"] is True

    stored = db_session.scalar(
        select(BiometricEnrollment).where(
            BiometricEnrollment.trainee_id == scenario["trainee"].id
        )
    )
    assert stored is not None
    assert len(stored.encrypted_embedding) > 100
    assert camera_frames()[0] not in stored.encrypted_embedding
    assert db_session.scalar(
        select(func.count(ConsentRecord.id)).where(
            ConsentRecord.user_id == scenario["trainee"].id,
            ConsentRecord.consent_type == "biometric_attendance_face_verification",
            ConsentRecord.granted.is_(True),
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.event_type == "biometric.consent_granted"
        )
    ) == 1

    trainer_delete = client.delete(
        f"/api/v1/attendance/biometrics/enrollments/{scenario['trainee'].id}",
        headers=login(client, scenario["trainer"]),
    )
    assert trainer_delete.status_code == 403

    admin_delete = client.delete(
        f"/api/v1/attendance/biometrics/enrollments/{scenario['trainee'].id}",
        headers=login(client, scenario["admin"]),
    )
    assert admin_delete.status_code == 200
    assert db_session.scalar(
        select(BiometricEnrollment).where(
            BiometricEnrollment.trainee_id == scenario["trainee"].id
        )
    ) is None

    enroll_trainee(client, scenario)

    deleted = client.delete("/api/v1/attendance/biometrics/enrollment/me", headers=headers)
    assert deleted.status_code == 200
    assert db_session.scalar(
        select(BiometricEnrollment).where(
            BiometricEnrollment.trainee_id == scenario["trainee"].id
        )
    ) is None
    assert db_session.scalar(
        select(func.count(ConsentRecord.id)).where(
            ConsentRecord.user_id == scenario["trainee"].id,
            ConsentRecord.granted.is_(False),
        )
    ) == 2


def test_low_confidence_rejects_and_unknown_people_are_not_identified(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = build_attendance_scenario(db_session, "BIO-REJECT")
    session, trainer_headers = create_session(client, scenario)
    _, kiosk_headers = register_device(client, scenario, trainer_headers)
    enroll_trainee(client, scenario)

    unknown = client.post(
        "/api/v1/attendance/kiosk/biometrics/challenge",
        headers=kiosk_headers,
        json={"session_id": session["id"], "identity_code": "NCCT-DEADBEEF"},
    )
    assert unknown.status_code == 422
    assert "not eligible" in unknown.json()["detail"]

    challenge = kiosk_challenge(client, scenario, session, kiosk_headers)
    monkeypatch.setattr(biometric_service, "face_provider", lambda: ControlledProvider(0.2))
    idempotency_key = str(uuid4())
    rejected = client.post(
        "/api/v1/attendance/kiosk/biometrics/verify",
        headers=kiosk_headers,
        data={
            "challenge_id": challenge["id"],
            "idempotency_key": idempotency_key,
            "captured_at": scenario["now"].isoformat(),
        },
        files=multipart_frames(camera_frames(subject="other")),
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["attendance_recorded"] is False
    assert db_session.scalar(select(func.count(AttendanceCheckIn.id))) == 0
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.event_type == "biometric.verification_rejected"
        )
    ) == 1

    replay = client.post(
        "/api/v1/attendance/kiosk/biometrics/verify",
        headers=kiosk_headers,
        data={
            "challenge_id": challenge["id"],
            "idempotency_key": idempotency_key,
            "captured_at": scenario["now"].isoformat(),
        },
        files=multipart_frames(camera_frames(subject="other")),
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == rejected.json()["id"]
    assert db_session.scalar(select(func.count(BiometricVerification.id))) == 1


def test_high_confidence_face_verification_records_attendance_once(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = build_attendance_scenario(db_session, "BIO-PASS")
    session, trainer_headers = create_session(client, scenario)
    _, kiosk_headers = register_device(client, scenario, trainer_headers)
    enroll_trainee(client, scenario)
    challenge = kiosk_challenge(client, scenario, session, kiosk_headers)
    monkeypatch.setattr(biometric_service, "face_provider", lambda: ControlledProvider(0.97))
    idempotency_key = str(uuid4())
    payload = {
        "challenge_id": challenge["id"],
        "idempotency_key": idempotency_key,
        "captured_at": scenario["now"].isoformat(),
    }

    verified = client.post(
        "/api/v1/attendance/kiosk/biometrics/verify",
        headers=kiosk_headers,
        data=payload,
        files=multipart_frames(camera_frames()),
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    assert verified.json()["attendance_recorded"] is True
    assert verified.json()["confidence"] == 0.97

    replay = client.post(
        "/api/v1/attendance/kiosk/biometrics/verify",
        headers=kiosk_headers,
        data=payload,
        files=multipart_frames(camera_frames()),
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == verified.json()["id"]
    assert db_session.scalar(select(func.count(AttendanceCheckIn.id))) == 1
    check_in = db_session.scalar(select(AttendanceCheckIn))
    assert check_in is not None
    assert check_in.source == AttendanceSource.BIOMETRIC


def test_uncertain_match_requires_admin_review_before_attendance(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = build_attendance_scenario(db_session, "BIO-REVIEW")
    session, trainer_headers = create_session(client, scenario)
    _, kiosk_headers = register_device(client, scenario, trainer_headers)
    enroll_trainee(client, scenario)
    challenge = kiosk_challenge(client, scenario, session, kiosk_headers)
    monkeypatch.setattr(biometric_service, "face_provider", lambda: ControlledProvider(0.8))

    uncertain = client.post(
        "/api/v1/attendance/kiosk/biometrics/verify",
        headers=kiosk_headers,
        data={
            "challenge_id": challenge["id"],
            "idempotency_key": str(uuid4()),
            "captured_at": scenario["now"].isoformat(),
        },
        files=multipart_frames(camera_frames()),
    )
    assert uncertain.status_code == 200, uncertain.text
    assert uncertain.json()["status"] == "manual_review"
    assert uncertain.json()["review_status"] == "pending"
    assert uncertain.json()["attendance_recorded"] is False
    assert db_session.scalar(select(func.count(AttendanceCheckIn.id))) == 0

    trainer_review = client.patch(
        f"/api/v1/attendance/biometrics/reviews/{uncertain.json()['id']}",
        headers=trainer_headers,
        json={"decision": "approved", "review_notes": "Checked in person."},
    )
    assert trainer_review.status_code == 403

    approved = client.patch(
        f"/api/v1/attendance/biometrics/reviews/{uncertain.json()['id']}",
        headers=login(client, scenario["admin"]),
        json={"decision": "approved", "review_notes": "Identity checked in person."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["attendance_recorded"] is True
    check_in = db_session.scalar(select(AttendanceCheckIn))
    assert check_in is not None
    assert check_in.source == AttendanceSource.BIOMETRIC_MANUAL
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.event_type == "biometric.manual_review_approved"
        )
    ) == 1
    verification = db_session.get(BiometricVerification, UUID(uncertain.json()["id"]))
    assert verification is not None
    assert verification.status == BiometricVerificationStatus.MANUAL_REVIEW
