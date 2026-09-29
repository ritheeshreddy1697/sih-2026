from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AssessmentType,
    Assignment,
    Course,
    CourseLanguage,
    CourseModule,
    CourseSection,
    CourseStatus,
    EligibilityType,
    EnrollmentStatus,
    Institution,
    InstitutionType,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonContent,
    LessonProgress,
    LessonType,
    Programme,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    Question,
    QuestionBank,
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


def build_learning_scenario(db: Session, suffix: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    email_suffix = suffix.lower()
    institution = Institution(
        code=f"ICM-LMS-{suffix}",
        name=f"ICM Learning Demonstration {suffix}",
        institution_type=InstitutionType.ICM,
        is_demo=True,
    )
    db.add(institution)
    db.commit()
    admin = create_test_user(
        db,
        email=f"lms.admin.{email_suffix}@example.com",
        role_code=RoleCode.INSTITUTE_ADMIN,
        institution=institution,
    )
    trainee = create_test_user(
        db,
        email=f"lms.trainee.{email_suffix}@example.com",
        role_code=RoleCode.TRAINEE,
        institution=institution,
    )
    outsider = create_test_user(
        db,
        email=f"lms.outsider.{email_suffix}@example.com",
        role_code=RoleCode.TRAINEE,
    )
    programme = Programme(
        institution_id=institution.id,
        created_by_id=admin.id,
        updated_by_id=admin.id,
        title=f"Learning Programme {suffix}",
        code=f"LMS-{suffix}",
        summary="A demonstration programme for secure digital learning workflows.",
        description="Structured lessons, assignments and assessments for cooperative training.",
        mode=ProgrammeMode.HYBRID,
        status=ProgrammeStatus.PUBLISHED,
        eligibility_criteria="Open to enrolled demonstration trainees.",
        eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
        capacity=30,
        location="Demonstration Training Centre",
        language="English, Hindi and Telugu",
        duration_days=5,
        application_deadline=now + timedelta(days=10),
        start_date=(now + timedelta(days=15)).date(),
        end_date=(now + timedelta(days=19)).date(),
        published_at=now,
    )
    text_lesson = Lesson(
        title="Cooperative foundations",
        lesson_type=LessonType.TEXT,
        position=1,
        is_required=True,
        contents=[
            LessonContent(
                language_code="en",
                title="Cooperative foundations",
                text_content="A cooperative is owned and governed by its members.",
            )
        ],
    )
    video_lesson = Lesson(
        title="Member governance video",
        lesson_type=LessonType.VIDEO,
        position=2,
        duration_seconds=90,
        is_required=True,
        contents=[
            LessonContent(
                language_code="en",
                title="Member governance video",
                external_url="https://example.test/governance.mp4",
            )
        ],
    )
    module = CourseModule(
        title="Learning basics",
        description="Core cooperative learning concepts.",
        position=1,
        lessons=[text_lesson, video_lesson],
    )
    section = CourseSection(title="Foundation", position=1, modules=[module])
    bank = QuestionBank(
        title="Foundation question bank",
        description="Questions used by the demonstration assessment.",
        questions=[
            Question(
                prompt="Who owns a cooperative?",
                choices=["Members", "External investors", "One supplier"],
                correct_option_index=0,
                explanation="Cooperatives are owned by their members.",
                points=1,
                position=1,
            ),
            Question(
                prompt="Which principle supports member voice?",
                choices=["Closed records", "Democratic control", "Unlimited attempts"],
                correct_option_index=1,
                explanation="Democratic member control gives members a voice.",
                points=1,
                position=2,
            ),
        ],
    )
    course = Course(
        programme=programme,
        created_by=admin,
        title=f"Cooperative learning course {suffix}",
        summary="A complete demonstration course with lessons and assessments.",
        status=CourseStatus.PUBLISHED,
        default_language_code="en",
        languages=[CourseLanguage(code="en", name="English")],
        sections=[section],
        question_banks=[bank],
    )
    assignment = Assignment(
        course=course,
        module=module,
        title="Member governance reflection",
        instructions="Submit a short PDF reflection on democratic member control.",
        max_score=20,
        allowed_content_types=["application/pdf"],
        is_published=True,
    )
    assessment = LearnerAssessment(
        course=course,
        question_bank=bank,
        title="Foundation quiz",
        instructions="Choose one response for each question.",
        assessment_type=AssessmentType.QUIZ,
        attempt_limit=1,
        passing_score_percent=60,
        is_published=True,
    )
    enrollment = ProgrammeEnrollment(
        trainee=trainee,
        programme=programme,
        status=EnrollmentStatus.ENROLLED,
    )
    db.add_all([course, assignment, assessment, enrollment])
    db.commit()
    return {
        "admin": admin,
        "trainee": trainee,
        "outsider": outsider,
        "course": course,
        "text_lesson": text_lesson,
        "video_lesson": video_lesson,
        "assignment": assignment,
        "assessment": assessment,
    }


def test_course_requires_enrolment_and_exposes_resume_state(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "ACCESS")
    trainee_headers = login(client, scenario["trainee"])
    outsider_headers = login(client, scenario["outsider"])

    catalogue = client.get("/api/v1/learning/courses", headers=trainee_headers)
    assert catalogue.status_code == 200
    assert catalogue.json()["total"] == 1
    assert catalogue.json()["items"][0]["resume_lesson_id"] == str(scenario["text_lesson"].id)

    forbidden = client.get(
        f"/api/v1/learning/courses/{scenario['course'].id}",
        headers=outsider_headers,
    )
    assert forbidden.status_code == 403
    outsider_catalogue = client.get("/api/v1/learning/courses", headers=outsider_headers)
    assert outsider_catalogue.status_code == 200
    assert outsider_catalogue.json()["items"] == []


def test_lesson_progress_is_server_owned_and_media_time_is_bounded(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "PROGRESS")
    headers = login(client, scenario["trainee"])
    text_id = scenario["text_lesson"].id
    video_id = scenario["video_lesson"].id

    started = client.post(f"/api/v1/learning/lessons/{text_id}/start", headers=headers)
    assert started.status_code == 200
    completed = client.post(f"/api/v1/learning/lessons/{text_id}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == LearningProgressStatus.COMPLETED.value

    client.post(f"/api/v1/learning/lessons/{video_id}/start", headers=headers)
    manipulated = client.post(
        f"/api/v1/learning/lessons/{video_id}/heartbeat",
        headers=headers,
        json={
            "position_seconds": 90,
            "elapsed_seconds": 30,
            "viewed_seconds": 90,
            "status": "completed",
        },
    )
    assert manipulated.status_code == 422
    rapid = client.post(
        f"/api/v1/learning/lessons/{video_id}/heartbeat",
        headers=headers,
        json={"position_seconds": 30, "elapsed_seconds": 30},
    )
    assert rapid.status_code == 200
    assert rapid.json()["viewed_seconds"] == 0

    progress = db_session.scalar(select(LessonProgress).where(LessonProgress.lesson_id == video_id))
    assert progress is not None
    progress.last_position_seconds = 0
    for position in (30, 60, 90):
        progress.last_accessed_at = datetime.now(UTC) - timedelta(seconds=31)
        db_session.commit()
        heartbeat = client.post(
            f"/api/v1/learning/lessons/{video_id}/heartbeat",
            headers=headers,
            json={"position_seconds": position, "elapsed_seconds": 30},
        )
        assert heartbeat.status_code == 200
    assert heartbeat.json()["viewed_seconds"] == 90
    assert heartbeat.json()["status"] == LearningProgressStatus.COMPLETED.value

    detail = client.get(f"/api/v1/learning/courses/{scenario['course'].id}", headers=headers)
    assert detail.json()["progress_percent"] == 100
    assert detail.json()["resume_lesson_id"] is None


def test_offline_progress_sync_is_ordered_monotonic_and_idempotent(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "OFFLINE")
    headers = login(client, scenario["trainee"])
    video_id = scenario["video_lesson"].id
    started_at = datetime.now(UTC) - timedelta(seconds=95)
    events = [
        {
            "idempotency_key": str(uuid4()),
            "lesson_id": str(video_id),
            "action": "start",
            "captured_at": started_at.isoformat(),
        },
        *[
            {
                "idempotency_key": str(uuid4()),
                "lesson_id": str(video_id),
                "action": "heartbeat",
                "captured_at": (started_at + timedelta(seconds=offset)).isoformat(),
                "position_seconds": offset,
                "elapsed_seconds": 30,
            }
            for offset in (30, 60, 90)
        ],
        {
            "idempotency_key": str(uuid4()),
            "lesson_id": str(video_id),
            "action": "complete",
            "captured_at": (started_at + timedelta(seconds=91)).isoformat(),
        },
    ]

    first = client.post(
        "/api/v1/learning/progress/sync",
        headers=headers,
        json={"events": list(reversed(events))},
    )
    assert first.status_code == 200
    assert first.json()["applied"] == 5
    assert first.json()["rejected"] == 0
    assert first.json()["items"][0]["result"] == "applied"

    progress = db_session.scalar(select(LessonProgress).where(LessonProgress.lesson_id == video_id))
    assert progress is not None
    assert progress.viewed_seconds == 90
    assert progress.last_position_seconds == 90
    assert progress.status == LearningProgressStatus.COMPLETED

    retried = client.post(
        "/api/v1/learning/progress/sync",
        headers=headers,
        json={"events": events},
    )
    assert retried.status_code == 200
    assert retried.json()["duplicates"] == 5
    assert retried.json()["applied"] == 0
    db_session.refresh(progress)
    assert progress.viewed_seconds == 90


def test_offline_progress_sync_rejects_ineligible_lessons_and_key_reuse(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "OFFLINE-ACCESS")
    trainee_headers = login(client, scenario["trainee"])
    outsider_headers = login(client, scenario["outsider"])
    key = str(uuid4())
    captured_at = datetime.now(UTC).isoformat()
    payload = {
        "events": [
            {
                "idempotency_key": key,
                "lesson_id": str(scenario["text_lesson"].id),
                "action": "start",
                "captured_at": captured_at,
            }
        ]
    }

    accepted = client.post("/api/v1/learning/progress/sync", headers=trainee_headers, json=payload)
    assert accepted.status_code == 200
    assert accepted.json()["applied"] == 1

    reused = client.post(
        "/api/v1/learning/progress/sync",
        headers=trainee_headers,
        json={
            "events": [
                {
                    **payload["events"][0],
                    "action": "complete",
                }
            ]
        },
    )
    assert reused.status_code == 200
    assert reused.json()["items"][0]["result"] == "rejected"

    forbidden = client.post(
        "/api/v1/learning/progress/sync", headers=outsider_headers, json=payload
    )
    assert forbidden.status_code == 200
    assert forbidden.json()["items"][0]["result"] == "rejected"


def test_assessment_hides_answers_and_computes_score_on_server(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "SCORING")
    headers = login(client, scenario["trainee"])
    assessment_id = scenario["assessment"].id

    started = client.post(f"/api/v1/learning/assessments/{assessment_id}/attempts", headers=headers)
    assert started.status_code == 200
    body = started.json()
    assert all("correct_option_index" not in item for item in body["questions"])
    answers = [
        {"question_id": body["questions"][0]["id"], "option_index": 0},
        {"question_id": body["questions"][1]["id"], "option_index": 0},
    ]

    manipulated = client.post(
        f"/api/v1/learning/attempts/{body['id']}/submit",
        headers=headers,
        json={"answers": answers, "score_percent": 100, "passed": True},
    )
    assert manipulated.status_code == 422
    submitted = client.post(
        f"/api/v1/learning/attempts/{body['id']}/submit",
        headers=headers,
        json={"answers": answers},
    )
    assert submitted.status_code == 200
    assert submitted.json()["score_percent"] == 50
    assert submitted.json()["passed"] is False
    assert [item["correct"] for item in submitted.json()["grading_details"]] == [
        True,
        False,
    ]


def test_assessment_attempt_limit_is_enforced(client: TestClient, db_session: Session) -> None:
    scenario = build_learning_scenario(db_session, "LIMIT")
    headers = login(client, scenario["trainee"])
    assessment_id = scenario["assessment"].id
    started = client.post(f"/api/v1/learning/assessments/{assessment_id}/attempts", headers=headers)
    answers = [
        {"question_id": item["id"], "option_index": index}
        for item, index in zip(started.json()["questions"], (0, 1), strict=True)
    ]
    submitted = client.post(
        f"/api/v1/learning/attempts/{started.json()['id']}/submit",
        headers=headers,
        json={"answers": answers},
    )
    assert submitted.status_code == 200
    assert submitted.json()["score_percent"] == 100

    blocked = client.post(f"/api/v1/learning/assessments/{assessment_id}/attempts", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Assessment attempt limit has been reached"


def test_assignment_file_type_and_enrolment_permissions(
    client: TestClient, db_session: Session
) -> None:
    scenario = build_learning_scenario(db_session, "FILES")
    trainee_headers = login(client, scenario["trainee"])
    outsider_headers = login(client, scenario["outsider"])
    assignment_id = scenario["assignment"].id

    invalid = client.post(
        f"/api/v1/learning/assignments/{assignment_id}/submissions",
        headers=trainee_headers,
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert invalid.status_code == 422
    submitted = client.post(
        f"/api/v1/learning/assignments/{assignment_id}/submissions",
        headers=trainee_headers,
        files={"file": ("reflection.pdf", b"%PDF-test", "application/pdf")},
    )
    assert submitted.status_code == 201
    assert submitted.json()["filename"] == "reflection.pdf"
    forbidden = client.post(
        f"/api/v1/learning/assignments/{assignment_id}/submissions",
        headers=outsider_headers,
        files={"file": ("reflection.pdf", b"%PDF-test", "application/pdf")},
    )
    assert forbidden.status_code == 403
