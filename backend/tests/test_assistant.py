from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Institution, InstitutionType, RoleCode, User
from app.services.platform_ai import (
    PlatformAIError,
    PlatformAIProvider,
    PlatformAIRequest,
    get_platform_ai_provider,
)
from tests.conftest import create_test_user


class MockPlatformProvider:
    name = "gemini"

    def __init__(self) -> None:
        self.requests: list[PlatformAIRequest] = []

    def generate(self, request: PlatformAIRequest) -> str:
        self.requests.append(request)
        return "Open Programmes and review the options available to your role."


class FailingPlatformProvider:
    name = "gemini"

    def generate(self, request: PlatformAIRequest) -> str:
        raise PlatformAIError("provider unavailable")


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_trainer(db: Session, email: str) -> User:
    institution = Institution(
        code=f"ASSIST-{email.split('@')[0].upper()}",
        name="Assistant test institute",
        institution_type=InstitutionType.ICM,
    )
    db.add(institution)
    db.commit()
    return create_test_user(
        db,
        email=email,
        role_code=RoleCode.TRAINER,
        institution=institution,
    )


def test_authenticated_user_can_send_contextual_assistant_message(
    client: TestClient, db_session: Session
) -> None:
    trainer = create_trainer(db_session, "assistant.trainer@example.com")
    provider = MockPlatformProvider()
    test_app = cast(FastAPI, client.app)
    test_app.dependency_overrides[get_platform_ai_provider] = lambda: provider

    response = client.post(
        "/api/v1/assistant/chat",
        headers=login(client, trainer),
        json={
            "message": "Where can I see programmes?",
            "history": [{"role": "assistant", "content": "How can I help?"}],
            "page_path": "/dashboard",
            "language": "en",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "answer": "Open Programmes and review the options available to your role.",
        "provider": "gemini",
        "used_local_fallback": False,
    }
    assert provider.requests[0].page_path == "/dashboard"
    assert provider.requests[0].role_names == ["Trainer"]
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.user_id == trainer.id,
            AuditLog.event_type == "assistant.message",
        )
    )
    assert audit is not None
    assert audit.details == {"provider": "gemini", "page_path": "/dashboard"}
    assert "Where can I see programmes?" not in str(audit.details)


def test_assistant_requires_authentication_and_falls_back_safely(
    client: TestClient, db_session: Session
) -> None:
    unauthorized = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Help me", "page_path": "/dashboard"},
    )
    assert unauthorized.status_code == 401

    trainer = create_trainer(db_session, "assistant.fallback@example.com")
    provider: PlatformAIProvider = FailingPlatformProvider()
    test_app = cast(FastAPI, client.app)
    test_app.dependency_overrides[get_platform_ai_provider] = lambda: provider
    response = client.post(
        "/api/v1/assistant/chat",
        headers=login(client, trainer),
        json={"message": "How do I check attendance?", "page_path": "/dashboard"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "local-guide"
    assert response.json()["used_local_fallback"] is True
    assert "/attendance" in response.json()["answer"]
