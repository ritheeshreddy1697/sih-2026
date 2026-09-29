from datetime import UTC, date, datetime, timedelta
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AuditLog,
    CareerFaq,
    CareerLanguage,
    Institution,
    InstitutionType,
    Programme,
    ProgrammeMode,
    ProgrammeStatus,
    RoleCode,
    TraineeProfile,
    User,
)
from app.services.career_ai import CareerAIProvider, CareerAIRequest, get_career_ai_provider
from tests.conftest import create_test_user
from tests.test_employment import build_scenario, create_and_publish_job


class MockCareerProvider:
    name = "mock-provider"

    def __init__(self) -> None:
        self.requests: list[CareerAIRequest] = []

    def generate(self, request: CareerAIRequest) -> str:
        self.requests.append(request)
        if request.intent == "greeting":
            return "Hello! I can help with your training and career questions."
        return "Use verified achievements and keep the resume concise. [F1]"


def login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DemoOnly!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_english_faqs(db: Session, admin: User) -> None:
    db.add_all(
        [
            CareerFaq(
                slug="resume",
                language=CareerLanguage.ENGLISH,
                category="resume",
                question="How should I prepare my resume?",
                answer="Use verified achievements and keep the resume concise.",
                keywords=["resume", "cv", "skills"],
                platform_url="/employment",
                approved_by_id=admin.id,
            ),
            CareerFaq(
                slug="interview",
                language=CareerLanguage.ENGLISH,
                category="interview",
                question="How should I prepare for an interview?",
                answer="Read the published job record and practise structured examples.",
                keywords=["interview", "prepare"],
                platform_url="/employment",
                approved_by_id=admin.id,
            ),
            CareerFaq(
                slug="entrepreneurship",
                language=CareerLanguage.ENGLISH,
                category="entrepreneurship",
                question="How can I explore cooperative entrepreneurship?",
                answer=(
                    "Start with a member need and operating plan. This counsellor does not claim "
                    "eligibility for government schemes."
                ),
                keywords=["cooperative", "entrepreneurship", "scheme"],
                platform_url="/career-counsellor",
                approved_by_id=admin.id,
            ),
        ]
    )
    db.commit()


def seed_available_programme(db: Session, scenario: dict[str, object]) -> Programme:
    now = datetime.now(UTC)
    trainee = scenario["trainee"]
    super_admin = scenario["admin"]
    assert isinstance(trainee, User)
    assert isinstance(super_admin, User)
    institution = trainee.institution
    assert institution is not None
    admin = create_test_user(
        db,
        email="career.institute@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        approved_by_id=super_admin.id,
        title="Member Services Leadership Test Programme",
        code="CAREER-PROGRAMME-TEST",
        summary="A fictional published programme used only for counselling tests.",
        description="Develop member support and cooperative leadership skills in this test.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Open to individual trainees with an active platform account.",
        eligible_applicant_types=["individual"],
        capacity=30,
        location="Hyderabad",
        language="English",
        duration_days=3,
        application_deadline=now + timedelta(days=10),
        start_date=date.today() + timedelta(days=15),
        end_date=date.today() + timedelta(days=17),
        approved_at=now,
        published_at=now,
    )
    db.add(programme)
    db.commit()
    return programme


def test_grounded_counselling_history_feedback_and_support(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_scenario(db_session, "career")
    admin = scenario["admin"]
    trainee = scenario["trainee"]
    employer = scenario["employer"]
    assert isinstance(admin, User)
    assert isinstance(trainee, User)
    assert isinstance(employer, User)
    seed_english_faqs(db_session, admin)
    programme = seed_available_programme(db_session, scenario)
    job = create_and_publish_job(client, scenario, login(client, employer))
    provider = MockCareerProvider()
    test_app = cast(FastAPI, client.app)
    test_app.dependency_overrides[get_career_ai_provider] = lambda: provider
    headers = login(client, trainee)

    created = client.post(
        "/api/v1/career/conversations",
        headers=headers,
        json={"language": "en"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    greeting = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Hi"},
    )
    assert greeting.status_code == 201, greeting.text
    assert greeting.json()["assistant_message"]["provider"] == "mock-provider"
    assert greeting.json()["assistant_message"]["sources"] == []
    assert "training and career questions" in greeting.json()["assistant_message"]["content"]
    assert provider.requests[-1].intent == "greeting"

    resume = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Help me prepare my resume"},
    )
    assert resume.status_code == 201, resume.text
    assert resume.json()["assistant_message"]["provider"] == "mock-provider"
    assert resume.json()["assistant_message"]["sources"][0]["source_type"] == "faq"
    assert len(provider.requests) == 2

    programmes = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Which training programme can I apply for?"},
    )
    assert programmes.status_code == 201, programmes.text
    programme_answer = programmes.json()["assistant_message"]
    assert programme.title in programme_answer["content"]
    assert programme.eligibility_criteria in programme_answer["content"]
    assert programme_answer["sources"][0]["url"] == f"/programmes/{programme.id}"
    assert len(provider.requests) == 2

    jobs = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Show jobs matching my verified skills"},
    )
    assert jobs.status_code == 201, jobs.text
    job_answer = jobs.json()["assistant_message"]
    assert job["title"] in job_answer["content"]
    assert "Invented vacancy" not in job_answer["content"]
    assert job_answer["sources"][0]["url"] == f"/employment?job={job['id']}"
    assert len(provider.requests) == 2

    entrepreneurship = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Is there a cooperative entrepreneurship scheme for me?"},
    )
    assert entrepreneurship.status_code == 201
    entrepreneurship_answer = entrepreneurship.json()["assistant_message"]
    assert "does not claim eligibility for government schemes" in entrepreneurship_answer["content"]
    assert entrepreneurship_answer["provider"] == "local-faq"
    assert len(provider.requests) == 2

    assistant_message_id = resume.json()["assistant_message"]["id"]
    feedback = client.put(
        f"/api/v1/career/conversations/{conversation_id}/messages/{assistant_message_id}/feedback",
        headers=headers,
        json={"rating": "helpful"},
    )
    assert feedback.status_code == 200
    assert feedback.json()["rating"] == "helpful"

    escalation = client.post(
        f"/api/v1/career/conversations/{conversation_id}/escalate",
        headers=headers,
        json={"reason": "I need help comparing two career paths."},
    )
    assert escalation.status_code == 201
    assert escalation.json()["status"] == "open"

    history = client.get(f"/api/v1/career/conversations/{conversation_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["messages"]) == 10
    assert history.json()["escalation"]["status"] == "open"

    admin_support = client.get("/api/v1/career/support", headers=login(client, admin))
    assert admin_support.status_code == 200
    assert admin_support.json()[0]["requester_email"] == trainee.email
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "career.support_requested")
    )


def test_career_permissions_validation_and_rate_limit(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    institution = Institution(
        code="CAREER-AUTH-TEST",
        name="Career authorization test institute",
        institution_type=InstitutionType.ICM,
    )
    db_session.add(institution)
    db_session.commit()
    trainee = create_test_user(
        db_session,
        email="career.rate.trainee@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    trainer = create_test_user(
        db_session,
        email="career.trainer@example.com",
        role_code=RoleCode.TRAINER,
        institution=institution,
    )
    admin = create_test_user(
        db_session,
        email="career.rate.admin@example.com",
        role_code=RoleCode.NCCT_SUPER_ADMIN,
        institution=institution,
    )
    db_session.add(TraineeProfile(user_id=trainee.id))
    seed_english_faqs(db_session, admin)
    trainee_headers = login(client, trainee)
    trainer_headers = login(client, trainer)
    provider: CareerAIProvider = MockCareerProvider()
    test_app = cast(FastAPI, client.app)
    test_app.dependency_overrides[get_career_ai_provider] = lambda: provider

    forbidden = client.get("/api/v1/career/conversations", headers=trainer_headers)
    assert forbidden.status_code == 403
    invalid = client.post(
        "/api/v1/career/conversations",
        headers=trainee_headers,
        json={"language": "mr"},
    )
    assert invalid.status_code == 422
    created = client.post(
        "/api/v1/career/conversations",
        headers=trainee_headers,
        json={"language": "en"},
    )
    conversation_id = created.json()["id"]

    monkeypatch.setattr(settings, "career_chat_rate_limit_per_minute", 1)
    first = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=trainee_headers,
        json={"content": "Help with my resume"},
    )
    assert first.status_code == 201
    limited = client.post(
        f"/api/v1/career/conversations/{conversation_id}/messages",
        headers=trainee_headers,
        json={"content": "Help with an interview"},
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
