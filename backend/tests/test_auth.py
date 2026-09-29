from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AccountStatus, AuditLog, ConsentRecord, Role, RoleCode, User, UserSession
from tests.conftest import create_test_user


def login(client: TestClient, email: str, password: str = "DemoOnly!2026") -> dict[str, Any]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def test_successful_login_creates_session_and_audit_log(
    client: TestClient, db_session: Session
) -> None:
    user = create_test_user(
        db_session,
        email="admin@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["roles"][0]["code"] == "ncct_super_admin"
    assert "platform:manage" in response.json()["user"]["permissions"]
    assert response.cookies.get(settings.refresh_cookie_name)
    assert db_session.scalar(select(UserSession).where(UserSession.user_id == user.id))
    audit = db_session.scalar(select(AuditLog).where(AuditLog.event_type == "auth.login.succeeded"))
    assert audit is not None
    assert audit.success is True


def test_invalid_login_returns_401_and_is_audited(client: TestClient, db_session: Session) -> None:
    create_test_user(db_session, email="trainee@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "trainee@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    audit = db_session.scalar(select(AuditLog).where(AuditLog.event_type == "auth.login.failed"))
    assert audit is not None
    assert audit.success is False


def test_protected_endpoint_returns_401_without_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_role_restriction_returns_403(client: TestClient, db_session: Session) -> None:
    create_test_user(
        db_session,
        email="trainer@example.com",
        role_code=RoleCode.TRAINER,
    )
    auth = login(client, "trainer@example.com")

    response = client.get(
        "/api/v1/auth/admin-check",
        headers={"Authorization": f"Bearer {auth['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have the required permission"


@pytest.mark.parametrize(
    "account_status",
    [AccountStatus.SUSPENDED, AccountStatus.PENDING_VERIFICATION],
)
def test_non_active_accounts_cannot_login(
    client: TestClient,
    db_session: Session,
    account_status: AccountStatus,
) -> None:
    create_test_user(
        db_session,
        email=f"{account_status.value}@example.com",
        status=account_status,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{account_status.value}@example.com",
            "password": "DemoOnly!2026",
        },
    )

    assert response.status_code == 403


def test_refresh_rotation_and_logout_revoke_session(
    client: TestClient, db_session: Session
) -> None:
    create_test_user(db_session, email="refresh@example.com")
    initial_auth = login(client, "refresh@example.com")

    refresh_response = client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    refreshed_auth = refresh_response.json()
    assert refreshed_auth["access_token"] != initial_auth["access_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed_auth['access_token']}"},
    )
    assert logout_response.status_code == 200

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed_auth['access_token']}"},
    )
    assert me_response.status_code == 401


def test_password_reset_invalidates_existing_sessions(
    client: TestClient, db_session: Session
) -> None:
    create_test_user(db_session, email="reset@example.com")
    existing_auth = login(client, "reset@example.com")

    request_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    assert request_response.status_code == 202
    reset_token = request_response.json()["reset_token"]
    assert reset_token

    confirm_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewDemoOnly!2026"},
    )
    assert confirm_response.status_code == 200

    old_session_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {existing_auth['access_token']}"},
    )
    assert old_session_response.status_code == 401
    login(client, "reset@example.com", "NewDemoOnly!2026")


def test_public_registration_creates_pending_account_with_consent(
    client: TestClient, db_session: Session
) -> None:
    db_session.add(Role(code=RoleCode.TRAINEE, display_name="Trainee"))
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ananya Deshmukh",
            "email": "ananya@example.com",
            "password": "Registration!2026",
            "role_code": "trainee",
            "phone": "+91 98765 43210",
            "consent_accepted": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_verification"
    user = db_session.scalar(select(User).where(User.email == "ananya@example.com"))
    assert user is not None
    assert user.status == AccountStatus.PENDING_VERIFICATION
    assert db_session.scalar(select(ConsentRecord).where(ConsentRecord.user_id == user.id))
