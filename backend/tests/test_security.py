from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AccountStatus, AuditLog, RoleCode, User
from tests.conftest import create_test_user


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_security_headers_and_sanitized_validation_errors(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]

    invalid = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Person",
            "email": "person@example.com",
            "password": "secret-value-that-must-not-be-reflected",
            "role_code": "trainee",
            "consent_accepted": True,
        },
    )
    assert invalid.status_code == 422
    assert "secret-value-that-must-not-be-reflected" not in invalid.text


def test_kiosk_token_is_allowed_by_explicit_cors_policy(client: TestClient) -> None:
    response = client.options(
        "/api/v1/attendance/kiosk/pair",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-kiosk-token",
        },
    )
    assert response.status_code == 200
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-kiosk-token" in allowed_headers


def test_authentication_rate_limit(client: TestClient, monkeypatch: object) -> None:
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)  # type: ignore[attr-defined]
    payload = {"email": "missing@example.com", "password": "WrongPassword!2026"}
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    limited = client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"]


def test_upload_rejects_mime_spoofing(client: TestClient, db_session: Session) -> None:
    trainee = create_test_user(db_session, email="upload-security@example.com")
    response = client.post(
        "/api/v1/profiles/me/documents",
        headers=login(client, trainee.email),
        data={"document_type": "identity"},
        files={"document": ("identity.png", b"this is not a png", "image/png")},
    )
    assert response.status_code == 422
    assert "does not match" in response.json()["detail"]


def test_account_deletion_requires_password_and_is_audited(
    client: TestClient, db_session: Session
) -> None:
    trainee = create_test_user(db_session, email="delete-me@example.com")
    admin = create_test_user(
        db_session,
        email="deletion-admin@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
    )
    trainee_headers = login(client, trainee.email)

    rejected = client.post(
        "/api/v1/auth/account-deletion",
        headers=trainee_headers,
        json={
            "current_password": "Incorrect!2026",
            "reason": "Testing the deletion control",
            "acknowledge_retention": True,
        },
    )
    assert rejected.status_code == 400

    requested = client.post(
        "/api/v1/auth/account-deletion",
        headers=trainee_headers,
        json={
            "current_password": "DemoOnly!2026",
            "reason": "Testing the deletion control",
            "acknowledge_retention": True,
        },
    )
    assert requested.status_code == 201
    request_id = requested.json()["id"]

    completed = client.post(
        f"/api/v1/auth/admin/account-deletions/{request_id}/complete",
        headers=login(client, admin.email),
        json={"resolution_note": "Identity and retention obligations reviewed by NCCT."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    db_session.expire_all()
    erased = db_session.get(User, trainee.id)
    assert erased is not None
    assert erased.status == AccountStatus.SUSPENDED
    assert erased.email.endswith("@example.invalid")
    assert erased.profile is not None and erased.profile.full_name == "Deleted account"
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "auth.account_deletion.completed")
    )
    assert audit is not None and audit.success is True
