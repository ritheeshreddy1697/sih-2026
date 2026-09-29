from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import RoleCode
from tests.conftest import create_test_user


@pytest.mark.parametrize("role_code", list(RoleCode))
def test_each_role_receives_its_authorized_dashboard(
    client: TestClient,
    db_session: Session,
    role_code: RoleCode,
) -> None:
    email = f"{role_code.value}@example.com"
    create_test_user(db_session, email=email, role_code=role_code)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "DemoOnly!2026"},
    )
    access_token: str = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/dashboard",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["dashboard_key"] == role_code.value
    assert len(body["metrics"]) == 4
    assert body["quick_actions"]
