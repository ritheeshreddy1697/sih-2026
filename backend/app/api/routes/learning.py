from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth, require_permission
from app.core.permissions import Permission
from app.core.uploads import attachment_header
from app.db.session import get_db
from app.schemas.learning import (
    AssessmentAttemptPublic,
    AssessmentCreate,
    AssessmentFeedback,
    AssessmentSubmission,
    AssessmentSummary,
    AssignmentCreate,
    AssignmentPublic,
    AssignmentReview,
    AssignmentSubmissionPublic,
    CourseCreate,
    CourseDetail,
    CourseLanguageCreate,
    CourseListResponse,
    CourseUpdate,
    LessonContentPublic,
    LessonCreate,
    LessonProgressPublic,
    LessonUpdate,
    ModuleCreate,
    ModuleUpdate,
    ProgressHeartbeat,
    ProgressSyncRequest,
    ProgressSyncResponse,
    QuestionBankCreate,
    QuestionBankPublic,
    QuestionCreate,
    SectionCreate,
    SectionUpdate,
)
from app.services import learning as learning_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]
LearningManager = Annotated[AuthContext, Depends(require_permission(Permission.LEARNING_MANAGE))]
LearningTrainee = Annotated[AuthContext, Depends(require_permission(Permission.LEARNING_ACCESS))]


@router.get("/courses", response_model=CourseListResponse)
def get_courses(db: DbSession, auth: CurrentAuth) -> CourseListResponse:
    items = learning_service.list_courses(db, auth.user)
    return CourseListResponse(items=items, total=len(items))


@router.post("/courses", response_model=CourseDetail, status_code=201)
def create_course(
    payload: CourseCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    course = learning_service.create_course(db, request, auth.user, payload)
    return learning_service.course_detail(db, course, auth.user)


@router.get("/courses/{course_id}", response_model=CourseDetail)
def get_course(course_id: UUID, db: DbSession, auth: CurrentAuth) -> CourseDetail:
    course = learning_service.load_course(db, course_id)
    return learning_service.course_detail(db, course, auth.user)


@router.patch("/courses/{course_id}", response_model=CourseDetail)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    course = learning_service.load_course(db, course_id)
    updated = learning_service.update_course(db, request, auth.user, course, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.post("/courses/{course_id}/languages", response_model=CourseDetail, status_code=201)
def add_language(
    course_id: UUID,
    payload: CourseLanguageCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    course = learning_service.load_course(db, course_id)
    updated = learning_service.add_language(db, request, auth.user, course, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.post("/courses/{course_id}/sections", response_model=CourseDetail, status_code=201)
def add_section(
    course_id: UUID,
    payload: SectionCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    course = learning_service.load_course(db, course_id)
    updated = learning_service.add_section(db, request, auth.user, course, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.patch("/sections/{section_id}", response_model=CourseDetail)
def update_section(
    section_id: UUID,
    payload: SectionUpdate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    section = learning_service.load_section(db, section_id)
    updated = learning_service.update_section(db, request, auth.user, section, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.post("/sections/{section_id}/modules", response_model=CourseDetail, status_code=201)
def add_module(
    section_id: UUID,
    payload: ModuleCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    section = learning_service.load_section(db, section_id)
    updated = learning_service.add_module(db, request, auth.user, section, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.patch("/modules/{module_id}", response_model=CourseDetail)
def update_module(
    module_id: UUID,
    payload: ModuleUpdate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    module = learning_service.load_module(db, module_id)
    updated = learning_service.update_module(db, request, auth.user, module, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.post("/modules/{module_id}/lessons", response_model=CourseDetail, status_code=201)
def add_lesson(
    module_id: UUID,
    payload: LessonCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    module = learning_service.load_module(db, module_id)
    updated = learning_service.add_lesson(db, request, auth.user, module, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.patch("/lessons/{lesson_id}", response_model=CourseDetail)
def update_lesson(
    lesson_id: UUID,
    payload: LessonUpdate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> CourseDetail:
    lesson = learning_service.load_lesson(db, lesson_id)
    updated = learning_service.update_lesson(db, request, auth.user, lesson, payload)
    return learning_service.course_detail(db, updated, auth.user)


@router.put("/lessons/{lesson_id}/content", response_model=LessonContentPublic)
async def put_lesson_content(
    lesson_id: UUID,
    request: Request,
    db: DbSession,
    auth: LearningManager,
    language_code: Annotated[str, Form(min_length=2, max_length=16)],
    title: Annotated[str, Form(min_length=2, max_length=255)],
    text_content: Annotated[str | None, Form()] = None,
    external_url: Annotated[str | None, Form(max_length=1000)] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> LessonContentPublic:
    lesson = learning_service.load_lesson(db, lesson_id)
    content = await learning_service.upsert_lesson_content(
        db,
        request,
        auth.user,
        lesson,
        language_code=language_code,
        title=title,
        text_content=text_content,
        external_url=external_url,
        upload=file,
    )
    return learning_service.content_public(content)


@router.get("/content/{content_id}/asset")
def get_lesson_asset(content_id: UUID, db: DbSession, auth: CurrentAuth) -> Response:
    content = learning_service.content_asset_for_user(db, auth.user, content_id)
    return Response(
        content=content.content,
        media_type=content.content_type,
        headers={
            "Content-Disposition": attachment_header(content.filename or "lesson-file", inline=True)
        },
    )


@router.post("/lessons/{lesson_id}/start", response_model=LessonProgressPublic)
def start_lesson(
    lesson_id: UUID,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
) -> LessonProgressPublic:
    lesson = learning_service.load_lesson(db, lesson_id)
    progress = learning_service.start_lesson(db, request, auth.user, lesson)
    return learning_service.progress_public(progress)


@router.post("/lessons/{lesson_id}/heartbeat", response_model=LessonProgressPublic)
def heartbeat_lesson(
    lesson_id: UUID,
    payload: ProgressHeartbeat,
    db: DbSession,
    auth: LearningTrainee,
) -> LessonProgressPublic:
    lesson = learning_service.load_lesson(db, lesson_id)
    progress = learning_service.heartbeat_lesson(db, auth.user, lesson, payload)
    return learning_service.progress_public(progress)


@router.post("/lessons/{lesson_id}/complete", response_model=LessonProgressPublic)
def complete_lesson(
    lesson_id: UUID,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
) -> LessonProgressPublic:
    lesson = learning_service.load_lesson(db, lesson_id)
    progress = learning_service.complete_lesson(db, request, auth.user, lesson)
    return learning_service.progress_public(progress)


@router.post("/progress/sync", response_model=ProgressSyncResponse)
def sync_lesson_progress(
    payload: ProgressSyncRequest,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
) -> ProgressSyncResponse:
    return learning_service.synchronize_lesson_progress(db, request, auth.user, payload.events)


@router.post("/courses/{course_id}/assignments", response_model=AssignmentPublic, status_code=201)
def create_assignment(
    course_id: UUID,
    payload: AssignmentCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> AssignmentPublic:
    course = learning_service.load_course(db, course_id)
    assignment = learning_service.create_assignment(db, request, auth.user, course, payload)
    return learning_service.assignment_public(db, assignment, None)


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionPublic,
    status_code=201,
)
async def submit_assignment(
    assignment_id: UUID,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
    file: Annotated[UploadFile, File()],
) -> AssignmentSubmissionPublic:
    assignment = learning_service.load_assignment(db, assignment_id)
    submission = await learning_service.submit_assignment(db, request, auth.user, assignment, file)
    return learning_service.submission_public(submission)


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=list[AssignmentSubmissionPublic],
)
def get_assignment_submissions(
    assignment_id: UUID,
    db: DbSession,
    auth: LearningManager,
) -> list[AssignmentSubmissionPublic]:
    assignment = learning_service.load_assignment(db, assignment_id)
    return learning_service.list_submissions(db, auth.user, assignment)


@router.patch("/submissions/{submission_id}", response_model=AssignmentSubmissionPublic)
def review_submission(
    submission_id: UUID,
    payload: AssignmentReview,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> AssignmentSubmissionPublic:
    submission = learning_service.load_submission(db, submission_id)
    updated = learning_service.review_submission(db, request, auth.user, submission, payload)
    return learning_service.submission_public(updated)


@router.get("/submissions/{submission_id}/file")
def get_submission_file(submission_id: UUID, db: DbSession, auth: CurrentAuth) -> Response:
    submission = learning_service.submission_file_for_user(db, auth.user, submission_id)
    return Response(
        content=submission.content,
        media_type=submission.content_type,
        headers={"Content-Disposition": attachment_header(submission.filename)},
    )


@router.get("/courses/{course_id}/question-banks", response_model=list[QuestionBankPublic])
def get_question_banks(
    course_id: UUID, db: DbSession, auth: LearningManager
) -> list[QuestionBankPublic]:
    course = learning_service.load_course(db, course_id)
    return learning_service.list_question_banks(db, auth.user, course)


@router.post(
    "/courses/{course_id}/question-banks",
    response_model=QuestionBankPublic,
    status_code=201,
)
def create_question_bank(
    course_id: UUID,
    payload: QuestionBankCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> QuestionBankPublic:
    course = learning_service.load_course(db, course_id)
    bank = learning_service.create_question_bank(db, request, auth.user, course, payload)
    return learning_service.question_bank_public(bank)


@router.post(
    "/question-banks/{bank_id}/questions",
    response_model=QuestionBankPublic,
    status_code=201,
)
def add_question(
    bank_id: UUID,
    payload: QuestionCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> QuestionBankPublic:
    bank = learning_service.load_question_bank(db, bank_id)
    updated = learning_service.add_question(db, request, auth.user, bank, payload)
    return learning_service.question_bank_public(updated)


@router.post(
    "/courses/{course_id}/assessments",
    response_model=AssessmentSummary,
    status_code=201,
)
def create_assessment(
    course_id: UUID,
    payload: AssessmentCreate,
    request: Request,
    db: DbSession,
    auth: LearningManager,
) -> AssessmentSummary:
    course = learning_service.load_course(db, course_id)
    assessment = learning_service.create_assessment(db, request, auth.user, course, payload)
    return learning_service.assessment_summary(db, assessment, None)


@router.post("/assessments/{assessment_id}/attempts", response_model=AssessmentAttemptPublic)
def start_assessment(
    assessment_id: UUID,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
) -> AssessmentAttemptPublic:
    assessment = learning_service.load_assessment(db, assessment_id)
    attempt = learning_service.start_assessment(db, request, auth.user, assessment)
    return learning_service.attempt_public(db, attempt)


@router.get(
    "/assessments/{assessment_id}/attempts",
    response_model=list[AssessmentAttemptPublic],
)
def get_assessment_attempts(
    assessment_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ASSESSMENTS_REVIEW))],
) -> list[AssessmentAttemptPublic]:
    assessment = learning_service.load_assessment(db, assessment_id)
    return learning_service.list_assessment_attempts(db, auth.user, assessment)


@router.get("/attempts/{attempt_id}", response_model=AssessmentAttemptPublic)
def get_attempt(attempt_id: UUID, db: DbSession, auth: CurrentAuth) -> AssessmentAttemptPublic:
    attempt = learning_service.attempt_for_user(db, auth.user, attempt_id)
    return learning_service.attempt_public(db, attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=AssessmentAttemptPublic)
def submit_assessment(
    attempt_id: UUID,
    payload: AssessmentSubmission,
    request: Request,
    db: DbSession,
    auth: LearningTrainee,
) -> AssessmentAttemptPublic:
    attempt = learning_service.load_attempt(db, attempt_id)
    submitted = learning_service.submit_assessment(db, request, auth.user, attempt, payload)
    return learning_service.attempt_public(db, submitted)


@router.patch("/attempts/{attempt_id}/feedback", response_model=AssessmentAttemptPublic)
def add_assessment_feedback(
    attempt_id: UUID,
    payload: AssessmentFeedback,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ASSESSMENTS_REVIEW))],
) -> AssessmentAttemptPublic:
    attempt = learning_service.load_attempt(db, attempt_id)
    updated = learning_service.add_assessment_feedback(db, request, auth.user, attempt, payload)
    return learning_service.attempt_public(db, updated)
