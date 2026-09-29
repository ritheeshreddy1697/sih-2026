from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.permissions import Permission, has_permission
from app.core.uploads import ASSIGNMENT_TYPES, LESSON_MEDIA_TYPES, read_validated_upload
from app.models import (
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentRecord,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    AuditLog,
    BatchTrainerAssignment,
    Course,
    CourseLanguage,
    CourseModule,
    CourseSection,
    CourseStatus,
    EnrollmentStatus,
    LearnerAssessment,
    LearningProgressStatus,
    LearningProgressSyncEvent,
    Lesson,
    LessonContent,
    LessonProgress,
    LessonType,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    Question,
    QuestionBank,
    RoleCode,
    User,
)
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
    CourseLanguagePublic,
    CourseListItem,
    CourseUpdate,
    GradingDetailPublic,
    LessonContentPublic,
    LessonCreate,
    LessonProgressPublic,
    LessonPublic,
    LessonUpdate,
    ModuleCreate,
    ModulePublic,
    ModuleUpdate,
    ProgressHeartbeat,
    ProgressSyncEvent,
    ProgressSyncResponse,
    ProgressSyncResult,
    QuestionBankCreate,
    QuestionBankPublic,
    QuestionCreate,
    QuestionForAttempt,
    QuestionManagerPublic,
    SectionCreate,
    SectionPublic,
    SectionUpdate,
)
from app.services.auth import get_client_details

MAX_LESSON_ASSET_BYTES = 50 * 1024 * 1024
MAX_ASSIGNMENT_BYTES = 10 * 1024 * 1024
DEFAULT_ASSIGNMENT_CONTENT_TYPES = ASSIGNMENT_TYPES
LESSON_CONTENT_TYPES = {
    LessonType.PDF: {"application/pdf"},
    LessonType.VIDEO: {"video/mp4", "video/webm"},
    LessonType.AUDIO: {"audio/mpeg", "audio/wav", "audio/ogg"},
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def user_has(user: User, permission: Permission) -> bool:
    return has_permission({role.code for role in user.roles}, permission)


def role_codes(user: User) -> set[RoleCode]:
    return {role.code for role in user.roles}


def add_learning_audit(
    db: Session,
    request: Request,
    user: User,
    event_type: str,
    **details: Any,
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id,
            event_type=event_type,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    )


def course_options() -> tuple[Any, ...]:
    return (
        joinedload(Course.programme).joinedload(Programme.institution),
        selectinload(Course.languages),
        selectinload(Course.sections)
        .selectinload(CourseSection.modules)
        .selectinload(CourseModule.lessons)
        .selectinload(Lesson.contents),
        selectinload(Course.assignments),
        selectinload(Course.assessments).joinedload(LearnerAssessment.question_bank),
    )


def load_course(db: Session, course_id: UUID) -> Course:
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(*course_options())
        .execution_options(populate_existing=True)
    )
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def manager_can_manage_programme(db: Session, user: User, programme: Programme) -> bool:
    roles = role_codes(user)
    if user_has(user, Permission.PLATFORM_MANAGE):
        return True
    if RoleCode.INSTITUTE_ADMIN in roles and user.institution_id == programme.institution_id:
        return True
    if RoleCode.TRAINER in roles:
        assignment = db.scalar(
            select(BatchTrainerAssignment.id)
            .join(ProgrammeBatch, ProgrammeBatch.id == BatchTrainerAssignment.batch_id)
            .where(
                BatchTrainerAssignment.trainer_id == user.id,
                ProgrammeBatch.programme_id == programme.id,
            )
            .limit(1)
        )
        return assignment is not None
    return False


def ensure_manager(db: Session, user: User, course: Course) -> None:
    if not user_has(user, Permission.LEARNING_MANAGE):
        raise HTTPException(status_code=403, detail="Learning content management is not permitted")
    if not manager_can_manage_programme(db, user, course.programme):
        raise HTTPException(
            status_code=403,
            detail="You can manage only assigned or institution-owned programmes",
        )


def enrollment_for_course(db: Session, user: User, course: Course) -> ProgrammeEnrollment:
    if not user_has(user, Permission.LEARNING_ACCESS):
        raise HTTPException(status_code=403, detail="Learning access is not permitted")
    enrollment = db.scalar(
        select(ProgrammeEnrollment).where(
            ProgrammeEnrollment.trainee_id == user.id,
            ProgrammeEnrollment.programme_id == course.programme_id,
            ProgrammeEnrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]),
        )
    )
    if enrollment is None or course.status != CourseStatus.PUBLISHED:
        raise HTTPException(status_code=403, detail="An active enrolment is required")
    return enrollment


def access_context(
    db: Session, user: User, course: Course
) -> tuple[ProgrammeEnrollment | None, bool]:
    if user_has(user, Permission.LEARNING_MANAGE) and manager_can_manage_programme(
        db, user, course.programme
    ):
        return None, True
    return enrollment_for_course(db, user, course), False


def list_courses(db: Session, user: User) -> list[CourseListItem]:
    roles = role_codes(user)
    if RoleCode.TRAINEE in roles:
        courses = list(
            db.scalars(
                select(Course)
                .join(ProgrammeEnrollment, ProgrammeEnrollment.programme_id == Course.programme_id)
                .where(
                    ProgrammeEnrollment.trainee_id == user.id,
                    ProgrammeEnrollment.status.in_(
                        [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
                    ),
                    Course.status == CourseStatus.PUBLISHED,
                )
                .options(*course_options())
                .order_by(Course.title)
            ).unique()
        )
        return [course_list_item(db, course, user) for course in courses]

    if not user_has(user, Permission.LEARNING_MANAGE):
        raise HTTPException(status_code=403, detail="Learning access is not permitted")
    statement = select(Course).options(*course_options()).order_by(Course.title)
    if not user_has(user, Permission.PLATFORM_MANAGE):
        if RoleCode.INSTITUTE_ADMIN in roles:
            statement = statement.join(Programme).where(
                Programme.institution_id == user.institution_id
            )
        elif RoleCode.TRAINER in roles:
            statement = (
                statement.join(ProgrammeBatch, ProgrammeBatch.programme_id == Course.programme_id)
                .join(
                    BatchTrainerAssignment,
                    BatchTrainerAssignment.batch_id == ProgrammeBatch.id,
                )
                .where(BatchTrainerAssignment.trainer_id == user.id)
            )
        else:
            raise HTTPException(status_code=403, detail="Learning access is not permitted")
    courses = list(db.scalars(statement).unique())
    return [course_list_item(db, course, user) for course in courses]


def flatten_lessons(course: Course) -> list[Lesson]:
    return [
        lesson
        for section in sorted(course.sections, key=lambda item: item.position)
        for module in sorted(section.modules, key=lambda item: item.position)
        for lesson in sorted(module.lessons, key=lambda item: item.position)
    ]


def progress_map(db: Session, enrollment: ProgrammeEnrollment | None) -> dict[UUID, LessonProgress]:
    if enrollment is None:
        return {}
    return {
        item.lesson_id: item
        for item in db.scalars(
            select(LessonProgress).where(LessonProgress.enrollment_id == enrollment.id)
        ).all()
    }


def progress_public(progress: LessonProgress | None) -> LessonProgressPublic:
    if progress is None:
        return LessonProgressPublic(
            status=LearningProgressStatus.NOT_STARTED,
            last_position_seconds=0,
            viewed_seconds=0,
            completed_at=None,
        )
    return LessonProgressPublic(
        status=progress.status,
        last_position_seconds=progress.last_position_seconds,
        viewed_seconds=progress.viewed_seconds,
        completed_at=progress.completed_at,
    )


def content_public(content: LessonContent) -> LessonContentPublic:
    return LessonContentPublic(
        id=content.id,
        language_code=content.language_code,
        title=content.title,
        text_content=content.text_content,
        external_url=content.external_url,
        filename=content.filename,
        content_type=content.content_type,
        size_bytes=content.size_bytes,
        has_asset=content.content is not None,
    )


def lesson_public(lesson: Lesson, progress: LessonProgress | None) -> LessonPublic:
    return LessonPublic(
        id=lesson.id,
        title=lesson.title,
        lesson_type=lesson.lesson_type,
        position=lesson.position,
        duration_seconds=lesson.duration_seconds,
        is_required=lesson.is_required,
        contents=[content_public(item) for item in lesson.contents],
        progress=progress_public(progress),
    )


def resume_details(
    lessons: list[Lesson], progress: dict[UUID, LessonProgress]
) -> tuple[UUID | None, int]:
    incomplete_activity = [
        item for item in progress.values() if item.status != LearningProgressStatus.COMPLETED
    ]
    if incomplete_activity:
        latest = max(incomplete_activity, key=lambda item: item.last_accessed_at)
        return latest.lesson_id, latest.last_position_seconds
    first_incomplete = next(
        (
            lesson
            for lesson in lessons
            if progress.get(lesson.id) is None
            or progress[lesson.id].status != LearningProgressStatus.COMPLETED
        ),
        None,
    )
    return (first_incomplete.id, 0) if first_incomplete else (None, 0)


def course_list_item(db: Session, course: Course, user: User) -> CourseListItem:
    enrollment, can_manage = access_context(db, user, course)
    lessons = flatten_lessons(course)
    progress = progress_map(db, enrollment)
    required = [item for item in lessons if item.is_required]
    completed = sum(
        progress.get(item.id) is not None
        and progress[item.id].status == LearningProgressStatus.COMPLETED
        for item in required
    )
    percent = round(completed / len(required) * 100) if required else 0
    resume_id, resume_position = resume_details(lessons, progress)
    return CourseListItem(
        id=course.id,
        programme_id=course.programme_id,
        programme_title=course.programme.title,
        programme_code=course.programme.code,
        title=course.title,
        summary=course.summary,
        status=course.status,
        languages=[CourseLanguagePublic.model_validate(item) for item in course.languages],
        lesson_count=len(lessons),
        completed_lesson_count=completed,
        progress_percent=percent,
        resume_lesson_id=resume_id,
        resume_position_seconds=resume_position,
        can_manage=can_manage,
    )


def submission_public(submission: AssignmentSubmission) -> AssignmentSubmissionPublic:
    trainee = submission.enrollment.trainee
    reviewer = submission.reviewed_by
    return AssignmentSubmissionPublic(
        id=submission.id,
        enrollment_id=submission.enrollment_id,
        trainee_name=trainee.profile.full_name if trainee.profile else trainee.email,
        submission_number=submission.submission_number,
        status=submission.status,
        filename=submission.filename,
        content_type=submission.content_type,
        size_bytes=submission.size_bytes,
        submitted_at=submission.submitted_at,
        score=submission.score,
        trainer_feedback=submission.trainer_feedback,
        reviewed_by_name=(reviewer.profile.full_name if reviewer and reviewer.profile else None),
        reviewed_at=submission.reviewed_at,
    )


def assignment_public(
    db: Session, assignment: Assignment, enrollment: ProgrammeEnrollment | None
) -> AssignmentPublic:
    latest = None
    if enrollment:
        latest = db.scalar(
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.enrollment_id == enrollment.id,
            )
            .options(
                joinedload(AssignmentSubmission.enrollment)
                .joinedload(ProgrammeEnrollment.trainee)
                .joinedload(User.profile),
                joinedload(AssignmentSubmission.reviewed_by).joinedload(User.profile),
            )
            .order_by(AssignmentSubmission.submission_number.desc())
            .limit(1)
        )
    return AssignmentPublic(
        id=assignment.id,
        module_id=assignment.module_id,
        title=assignment.title,
        instructions=assignment.instructions,
        due_at=assignment.due_at,
        max_score=assignment.max_score,
        allowed_content_types=assignment.allowed_content_types,
        is_published=assignment.is_published,
        latest_submission=submission_public(latest) if latest else None,
    )


def assessment_summary(
    db: Session, assessment: LearnerAssessment, enrollment: ProgrammeEnrollment | None
) -> AssessmentSummary:
    attempts: list[AssessmentAttempt] = []
    if enrollment:
        attempts = list(
            db.scalars(
                select(AssessmentAttempt).where(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.enrollment_id == enrollment.id,
                )
            ).all()
        )
    submitted = [item for item in attempts if item.status == AssessmentAttemptStatus.SUBMITTED]
    scores = [item.score_percent for item in submitted if item.score_percent is not None]
    return AssessmentSummary(
        id=assessment.id,
        title=assessment.title,
        instructions=assessment.instructions,
        assessment_type=assessment.assessment_type,
        attempt_limit=assessment.attempt_limit,
        attempts_used=len(attempts),
        attempts_remaining=max(assessment.attempt_limit - len(attempts), 0),
        passing_score_percent=assessment.passing_score_percent,
        best_score_percent=max(scores) if scores else None,
        passed=any(item.passed is True for item in submitted),
        is_published=assessment.is_published,
    )


def course_detail(db: Session, course: Course, user: User) -> CourseDetail:
    base = course_list_item(db, course, user)
    enrollment, can_manage = access_context(db, user, course)
    progress = progress_map(db, enrollment)
    sections = [
        SectionPublic(
            id=section.id,
            title=section.title,
            position=section.position,
            modules=[
                ModulePublic(
                    id=module.id,
                    title=module.title,
                    description=module.description,
                    position=module.position,
                    lessons=[
                        lesson_public(lesson, progress.get(lesson.id))
                        for lesson in sorted(module.lessons, key=lambda item: item.position)
                    ],
                )
                for module in sorted(section.modules, key=lambda item: item.position)
            ],
        )
        for section in sorted(course.sections, key=lambda item: item.position)
    ]
    assignments = [
        assignment_public(db, item, enrollment)
        for item in course.assignments
        if can_manage or item.is_published
    ]
    assessments = [
        assessment_summary(db, item, enrollment)
        for item in course.assessments
        if can_manage or item.is_published
    ]
    return CourseDetail(
        **base.model_dump(),
        default_language_code=course.default_language_code,
        sections=sections,
        assignments=assignments,
        assessments=assessments,
    )


def create_course(db: Session, request: Request, user: User, payload: CourseCreate) -> Course:
    programme = db.scalar(
        select(Programme)
        .where(Programme.id == payload.programme_id)
        .options(joinedload(Programme.institution))
    )
    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    if not user_has(user, Permission.LEARNING_MANAGE) or not manager_can_manage_programme(
        db, user, programme
    ):
        raise HTTPException(status_code=403, detail="You cannot create content for this programme")
    if db.scalar(select(Course.id).where(Course.programme_id == programme.id)):
        raise HTTPException(status_code=409, detail="This programme already has a course")
    course = Course(
        programme_id=programme.id,
        created_by_id=user.id,
        title=payload.title,
        summary=payload.summary,
        default_language_code=payload.default_language_code,
    )
    course.languages.append(
        CourseLanguage(code=payload.default_language_code, name=payload.default_language_code)
    )
    db.add(course)
    db.flush()
    add_learning_audit(db, request, user, "learning.course_created", course_id=str(course.id))
    db.commit()
    return load_course(db, course.id)


def update_course(
    db: Session,
    request: Request,
    user: User,
    course: Course,
    payload: CourseUpdate,
) -> Course:
    ensure_manager(db, user, course)
    changes = payload.model_dump(exclude_unset=True)
    if "default_language_code" in changes and not any(
        item.code == changes["default_language_code"] for item in course.languages
    ):
        raise HTTPException(status_code=422, detail="Add the default language to the course first")
    if changes.get("status") == CourseStatus.PUBLISHED:
        lessons = flatten_lessons(course)
        if not lessons:
            raise HTTPException(status_code=409, detail="Add at least one lesson before publishing")
        incomplete = [
            lesson.title
            for lesson in lessons
            if not any(
                content.language_code == course.default_language_code for content in lesson.contents
            )
        ]
        if incomplete:
            raise HTTPException(
                status_code=409,
                detail="Every lesson needs content in the default language before publishing",
            )
    for key, value in changes.items():
        setattr(course, key, value)
    add_learning_audit(
        db,
        request,
        user,
        "learning.course_updated",
        course_id=str(course.id),
        fields=sorted(changes),
    )
    db.commit()
    return load_course(db, course.id)


def add_language(
    db: Session,
    request: Request,
    user: User,
    course: Course,
    payload: CourseLanguageCreate,
) -> Course:
    ensure_manager(db, user, course)
    if any(item.code == payload.code for item in course.languages):
        raise HTTPException(status_code=409, detail="Language already exists")
    db.add(CourseLanguage(course_id=course.id, **payload.model_dump()))
    add_learning_audit(
        db,
        request,
        user,
        "learning.language_added",
        course_id=str(course.id),
        language_code=payload.code,
    )
    db.commit()
    return load_course(db, course.id)


def add_section(
    db: Session, request: Request, user: User, course: Course, payload: SectionCreate
) -> Course:
    ensure_manager(db, user, course)
    if db.scalar(
        select(CourseSection.id).where(
            CourseSection.course_id == course.id, CourseSection.position == payload.position
        )
    ):
        raise HTTPException(status_code=409, detail="Section position is already in use")
    db.add(CourseSection(course_id=course.id, **payload.model_dump()))
    add_learning_audit(db, request, user, "learning.section_added", course_id=str(course.id))
    db.commit()
    return load_course(db, course.id)


def load_section(db: Session, section_id: UUID) -> CourseSection:
    section = db.scalar(
        select(CourseSection)
        .where(CourseSection.id == section_id)
        .options(joinedload(CourseSection.course).joinedload(Course.programme))
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Course section not found")
    return section


def update_section(
    db: Session,
    request: Request,
    user: User,
    section: CourseSection,
    payload: SectionUpdate,
) -> Course:
    ensure_manager(db, user, section.course)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(section, key, value)
    add_learning_audit(
        db, request, user, "learning.section_updated", course_id=str(section.course_id)
    )
    db.commit()
    return load_course(db, section.course_id)


def add_module(
    db: Session,
    request: Request,
    user: User,
    section: CourseSection,
    payload: ModuleCreate,
) -> Course:
    ensure_manager(db, user, section.course)
    if db.scalar(
        select(CourseModule.id).where(
            CourseModule.section_id == section.id, CourseModule.position == payload.position
        )
    ):
        raise HTTPException(status_code=409, detail="Module position is already in use")
    db.add(CourseModule(section_id=section.id, **payload.model_dump()))
    add_learning_audit(db, request, user, "learning.module_added", course_id=str(section.course_id))
    db.commit()
    return load_course(db, section.course_id)


def load_module(db: Session, module_id: UUID) -> CourseModule:
    module = db.scalar(
        select(CourseModule)
        .where(CourseModule.id == module_id)
        .options(
            joinedload(CourseModule.section)
            .joinedload(CourseSection.course)
            .joinedload(Course.programme)
        )
    )
    if module is None:
        raise HTTPException(status_code=404, detail="Course module not found")
    return module


def update_module(
    db: Session,
    request: Request,
    user: User,
    module: CourseModule,
    payload: ModuleUpdate,
) -> Course:
    ensure_manager(db, user, module.section.course)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(module, key, value)
    add_learning_audit(
        db,
        request,
        user,
        "learning.module_updated",
        course_id=str(module.section.course_id),
    )
    db.commit()
    return load_course(db, module.section.course_id)


def add_lesson(
    db: Session,
    request: Request,
    user: User,
    module: CourseModule,
    payload: LessonCreate,
) -> Course:
    ensure_manager(db, user, module.section.course)
    if db.scalar(
        select(Lesson.id).where(Lesson.module_id == module.id, Lesson.position == payload.position)
    ):
        raise HTTPException(status_code=409, detail="Lesson position is already in use")
    db.add(Lesson(module_id=module.id, **payload.model_dump()))
    add_learning_audit(
        db,
        request,
        user,
        "learning.lesson_added",
        course_id=str(module.section.course_id),
    )
    db.commit()
    return load_course(db, module.section.course_id)


def load_lesson(db: Session, lesson_id: UUID) -> Lesson:
    lesson = db.scalar(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(
            selectinload(Lesson.contents),
            joinedload(Lesson.module)
            .joinedload(CourseModule.section)
            .joinedload(CourseSection.course)
            .joinedload(Course.programme),
        )
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def update_lesson(
    db: Session,
    request: Request,
    user: User,
    lesson: Lesson,
    payload: LessonUpdate,
) -> Course:
    course = lesson.module.section.course
    ensure_manager(db, user, course)
    changes = payload.model_dump(exclude_unset=True)
    resulting_type = changes.get("lesson_type", lesson.lesson_type)
    resulting_duration = changes.get("duration_seconds", lesson.duration_seconds)
    if resulting_type in {LessonType.VIDEO, LessonType.AUDIO} and not resulting_duration:
        raise HTTPException(status_code=422, detail="Video and audio lessons require a duration")
    for key, value in changes.items():
        setattr(lesson, key, value)
    add_learning_audit(db, request, user, "learning.lesson_updated", course_id=str(course.id))
    db.commit()
    return load_course(db, course.id)


async def upsert_lesson_content(
    db: Session,
    request: Request,
    user: User,
    lesson: Lesson,
    *,
    language_code: str,
    title: str,
    text_content: str | None,
    external_url: str | None,
    upload: UploadFile | None,
) -> LessonContent:
    course = lesson.module.section.course
    ensure_manager(db, user, course)
    if not any(item.code == language_code for item in course.languages):
        raise HTTPException(status_code=422, detail="Language is not enabled for this course")
    cleaned_url = external_url.strip() if external_url else None
    if cleaned_url and not cleaned_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=422, detail="External resource URL must use HTTP or HTTPS")
    content_bytes: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    if upload and upload.filename:
        allowed = LESSON_CONTENT_TYPES.get(lesson.lesson_type)
        if allowed is None:
            raise HTTPException(status_code=422, detail="File type does not match the lesson type")
        content_bytes, content_type, filename = await read_validated_upload(
            upload,
            allowed_types=allowed & LESSON_MEDIA_TYPES,
            maximum_bytes=MAX_LESSON_ASSET_BYTES,
            kind="lesson file",
        )

    if lesson.lesson_type == LessonType.TEXT and not (text_content and text_content.strip()):
        raise HTTPException(status_code=422, detail="Text lessons require text content")
    if lesson.lesson_type == LessonType.EXTERNAL_RESOURCE and not cleaned_url:
        raise HTTPException(status_code=422, detail="External-resource lessons require a URL")
    if lesson.lesson_type == LessonType.PDF and content_bytes is None:
        raise HTTPException(status_code=422, detail="PDF lessons require a PDF file")
    if lesson.lesson_type in {LessonType.VIDEO, LessonType.AUDIO} and not (
        content_bytes or cleaned_url
    ):
        raise HTTPException(status_code=422, detail="Media lessons require a file or URL")

    content = db.scalar(
        select(LessonContent).where(
            LessonContent.lesson_id == lesson.id,
            LessonContent.language_code == language_code,
        )
    )
    if content is None:
        content = LessonContent(
            lesson_id=lesson.id,
            language_code=language_code,
            title=title,
        )
        db.add(content)
    content.title = title
    content.text_content = text_content.strip() if text_content else None
    content.external_url = cleaned_url
    if content_bytes is not None:
        content.filename = filename
        content.content_type = content_type
        content.size_bytes = len(content_bytes)
        content.content = content_bytes
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.lesson_content_updated",
        course_id=str(course.id),
        lesson_id=str(lesson.id),
        language_code=language_code,
    )
    db.commit()
    refreshed = db.get(LessonContent, content.id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Lesson content not found")
    return refreshed


def content_asset_for_user(db: Session, user: User, content_id: UUID) -> LessonContent:
    content = db.scalar(
        select(LessonContent)
        .where(LessonContent.id == content_id)
        .options(
            joinedload(LessonContent.lesson)
            .joinedload(Lesson.module)
            .joinedload(CourseModule.section)
            .joinedload(CourseSection.course)
            .joinedload(Course.programme)
        )
    )
    if content is None or content.content is None:
        raise HTTPException(status_code=404, detail="Lesson asset not found")
    access_context(db, user, content.lesson.module.section.course)
    return content


def progress_for_lesson(
    db: Session, user: User, lesson: Lesson, *, create: bool
) -> tuple[ProgrammeEnrollment, LessonProgress | None]:
    enrollment = enrollment_for_course(db, user, lesson.module.section.course)
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    if progress is None and create:
        progress = LessonProgress(enrollment_id=enrollment.id, lesson_id=lesson.id)
        db.add(progress)
        db.flush()
    return enrollment, progress


def start_lesson(db: Session, request: Request, user: User, lesson: Lesson) -> LessonProgress:
    _enrollment, progress = progress_for_lesson(db, user, lesson, create=True)
    if progress is None:
        raise HTTPException(status_code=500, detail="Unable to start lesson")
    progress.last_accessed_at = utc_now()
    add_learning_audit(
        db,
        request,
        user,
        "learning.lesson_started",
        course_id=str(lesson.module.section.course_id),
        lesson_id=str(lesson.id),
    )
    db.commit()
    db.refresh(progress)
    return progress


def heartbeat_lesson(
    db: Session, user: User, lesson: Lesson, payload: ProgressHeartbeat
) -> LessonProgress:
    _enrollment, progress = progress_for_lesson(db, user, lesson, create=True)
    if progress is None:
        raise HTTPException(status_code=500, detail="Unable to update lesson progress")
    if lesson.lesson_type not in {LessonType.VIDEO, LessonType.AUDIO}:
        raise HTTPException(status_code=422, detail="Heartbeats apply only to video and audio")
    duration = lesson.duration_seconds or 0
    now = utc_now()
    previous_access = progress.last_accessed_at
    if previous_access.tzinfo is None:
        previous_access = previous_access.replace(tzinfo=UTC)
    server_elapsed = max(int((now - previous_access).total_seconds()), 0)
    reported_position = min(payload.position_seconds, duration)
    forward_movement = max(reported_position - progress.last_position_seconds, 0)
    credited_seconds = min(
        payload.elapsed_seconds,
        server_elapsed,
        forward_movement,
    )
    progress.last_position_seconds = max(progress.last_position_seconds, reported_position)
    progress.viewed_seconds = min(progress.viewed_seconds + credited_seconds, duration)
    progress.last_accessed_at = now
    if duration and progress.viewed_seconds >= math.ceil(duration * 0.8):
        progress.status = LearningProgressStatus.COMPLETED
        progress.completed_at = progress.completed_at or utc_now()
    db.commit()
    db.refresh(progress)
    return progress


def complete_lesson(db: Session, request: Request, user: User, lesson: Lesson) -> LessonProgress:
    _enrollment, progress = progress_for_lesson(db, user, lesson, create=True)
    if progress is None:
        raise HTTPException(status_code=500, detail="Unable to complete lesson")
    if lesson.lesson_type in {LessonType.VIDEO, LessonType.AUDIO}:
        required = math.ceil((lesson.duration_seconds or 0) * 0.8)
        if progress.viewed_seconds < required:
            raise HTTPException(
                status_code=409,
                detail="Complete at least 80% of this media lesson before finishing",
            )
    progress.status = LearningProgressStatus.COMPLETED
    progress.completed_at = progress.completed_at or utc_now()
    progress.last_accessed_at = utc_now()
    add_learning_audit(
        db,
        request,
        user,
        "learning.lesson_completed",
        course_id=str(lesson.module.section.course_id),
        lesson_id=str(lesson.id),
    )
    db.commit()
    db.refresh(progress)
    return progress


def _matching_sync_event(
    stored: LearningProgressSyncEvent, user: User, event: ProgressSyncEvent
) -> bool:
    stored_captured_at = stored.captured_at
    if stored_captured_at.tzinfo is None:
        stored_captured_at = stored_captured_at.replace(tzinfo=UTC)
    return (
        stored.user_id == user.id
        and stored.lesson_id == event.lesson_id
        and stored.event_type == event.action
        and stored.position_seconds == event.position_seconds
        and stored.elapsed_seconds == event.elapsed_seconds
        and stored_captured_at == event.captured_at.astimezone(UTC)
    )


def _progress_for_sync_event(
    db: Session, event: LearningProgressSyncEvent
) -> LessonProgress | None:
    return db.scalar(
        select(LessonProgress).where(
            LessonProgress.enrollment_id == event.enrollment_id,
            LessonProgress.lesson_id == event.lesson_id,
        )
    )


def _apply_progress_sync_event(
    db: Session, user: User, event: ProgressSyncEvent
) -> LessonProgress:
    now = utc_now()
    captured_at = event.captured_at.astimezone(UTC)
    if captured_at > now + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Progress time is too far in the future")

    lesson = load_lesson(db, event.lesson_id)
    enrollment, progress = progress_for_lesson(db, user, lesson, create=True)
    if progress is None:
        raise HTTPException(status_code=500, detail="Unable to update lesson progress")

    if event.action == "heartbeat":
        if lesson.lesson_type not in {LessonType.VIDEO, LessonType.AUDIO}:
            raise HTTPException(status_code=422, detail="Heartbeats apply only to video and audio")
        if event.position_seconds is None or event.elapsed_seconds is None:
            raise HTTPException(status_code=422, detail="Heartbeat timing is required")
        previous_captured_at = db.scalar(
            select(LearningProgressSyncEvent.captured_at)
            .where(
                LearningProgressSyncEvent.user_id == user.id,
                LearningProgressSyncEvent.lesson_id == lesson.id,
                LearningProgressSyncEvent.captured_at < captured_at,
            )
            .order_by(LearningProgressSyncEvent.captured_at.desc())
            .limit(1)
        )
        offline_elapsed = 0
        if previous_captured_at is not None:
            if previous_captured_at.tzinfo is None:
                previous_captured_at = previous_captured_at.replace(tzinfo=UTC)
            offline_elapsed = max(int((captured_at - previous_captured_at).total_seconds()), 0)
        duration = lesson.duration_seconds or 0
        reported_position = min(event.position_seconds, duration)
        forward_movement = max(reported_position - progress.last_position_seconds, 0)
        credited_seconds = min(event.elapsed_seconds, offline_elapsed, forward_movement)
        progress.last_position_seconds = max(progress.last_position_seconds, reported_position)
        progress.viewed_seconds = min(progress.viewed_seconds + credited_seconds, duration)
        if duration and progress.viewed_seconds >= math.ceil(duration * 0.8):
            progress.status = LearningProgressStatus.COMPLETED
            progress.completed_at = progress.completed_at or now
    elif event.action == "complete":
        if lesson.lesson_type in {LessonType.VIDEO, LessonType.AUDIO}:
            required = math.ceil((lesson.duration_seconds or 0) * 0.8)
            if progress.viewed_seconds < required:
                raise HTTPException(
                    status_code=409,
                    detail="Complete at least 80% of this media lesson before finishing",
                )
        progress.status = LearningProgressStatus.COMPLETED
        progress.completed_at = progress.completed_at or now

    progress.last_accessed_at = now
    db.add(
        LearningProgressSyncEvent(
            idempotency_key=event.idempotency_key,
            user_id=user.id,
            enrollment_id=enrollment.id,
            lesson_id=lesson.id,
            event_type=event.action,
            position_seconds=event.position_seconds,
            elapsed_seconds=event.elapsed_seconds,
            captured_at=captured_at,
        )
    )
    db.flush()
    return progress


def synchronize_lesson_progress(
    db: Session,
    request: Request,
    user: User,
    events: list[ProgressSyncEvent],
) -> ProgressSyncResponse:
    results: dict[UUID, ProgressSyncResult] = {}
    applied = duplicates = rejected = 0

    for event in sorted(events, key=lambda item: item.captured_at):
        stored = db.scalar(
            select(LearningProgressSyncEvent).where(
                LearningProgressSyncEvent.idempotency_key == event.idempotency_key
            )
        )
        if stored is not None:
            if not _matching_sync_event(stored, user, event):
                rejected += 1
                results[event.idempotency_key] = ProgressSyncResult(
                    idempotency_key=event.idempotency_key,
                    lesson_id=event.lesson_id,
                    result="rejected",
                    detail="Idempotency key was already used for different progress data",
                    progress=None,
                )
                continue
            duplicates += 1
            results[event.idempotency_key] = ProgressSyncResult(
                idempotency_key=event.idempotency_key,
                lesson_id=event.lesson_id,
                result="duplicate",
                detail="Progress event was already synchronized",
                progress=progress_public(_progress_for_sync_event(db, stored)),
            )
            continue

        try:
            with db.begin_nested():
                progress = _apply_progress_sync_event(db, user, event)
        except IntegrityError:
            stored = db.scalar(
                select(LearningProgressSyncEvent).where(
                    LearningProgressSyncEvent.idempotency_key == event.idempotency_key
                )
            )
            if stored is None or not _matching_sync_event(stored, user, event):
                rejected += 1
                results[event.idempotency_key] = ProgressSyncResult(
                    idempotency_key=event.idempotency_key,
                    lesson_id=event.lesson_id,
                    result="rejected",
                    detail="Progress event conflicts with an existing event",
                    progress=None,
                )
            else:
                duplicates += 1
                results[event.idempotency_key] = ProgressSyncResult(
                    idempotency_key=event.idempotency_key,
                    lesson_id=event.lesson_id,
                    result="duplicate",
                    detail="Progress event was already synchronized",
                    progress=progress_public(_progress_for_sync_event(db, stored)),
                )
        except HTTPException as exc:
            rejected += 1
            results[event.idempotency_key] = ProgressSyncResult(
                idempotency_key=event.idempotency_key,
                lesson_id=event.lesson_id,
                result="rejected",
                detail=str(exc.detail),
                progress=None,
            )
        else:
            applied += 1
            results[event.idempotency_key] = ProgressSyncResult(
                idempotency_key=event.idempotency_key,
                lesson_id=event.lesson_id,
                result="applied",
                detail="Progress synchronized",
                progress=progress_public(progress),
            )

    if applied:
        add_learning_audit(
            db,
            request,
            user,
            "learning.progress_synchronized",
            applied=applied,
            duplicates=duplicates,
            rejected=rejected,
        )
    db.commit()
    return ProgressSyncResponse(
        items=[results[event.idempotency_key] for event in events],
        applied=applied,
        duplicates=duplicates,
        rejected=rejected,
    )


def create_assignment(
    db: Session,
    request: Request,
    user: User,
    course: Course,
    payload: AssignmentCreate,
) -> Assignment:
    ensure_manager(db, user, course)
    if not set(payload.allowed_content_types) <= ASSIGNMENT_TYPES:
        raise HTTPException(status_code=422, detail="Assignment allows an unsupported file type")
    unsupported = set(payload.allowed_content_types) - DEFAULT_ASSIGNMENT_CONTENT_TYPES
    if unsupported:
        raise HTTPException(status_code=422, detail="Unsupported assignment file type")
    if payload.module_id:
        module = db.get(CourseModule, payload.module_id)
        if module is None or module.section.course_id != course.id:
            raise HTTPException(status_code=422, detail="Assignment module is outside this course")
    assignment = Assignment(course_id=course.id, **payload.model_dump())
    db.add(assignment)
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assignment_created",
        course_id=str(course.id),
        assignment_id=str(assignment.id),
    )
    db.commit()
    return assignment


def load_assignment(db: Session, assignment_id: UUID) -> Assignment:
    assignment = db.scalar(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(joinedload(Assignment.course).joinedload(Course.programme))
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


async def submit_assignment(
    db: Session,
    request: Request,
    user: User,
    assignment: Assignment,
    upload: UploadFile,
) -> AssignmentSubmission:
    enrollment = enrollment_for_course(db, user, assignment.course)
    if not assignment.is_published:
        raise HTTPException(status_code=404, detail="Assignment not found")
    content, content_type, filename = await read_validated_upload(
        upload,
        allowed_types=set(assignment.allowed_content_types) & ASSIGNMENT_TYPES,
        maximum_bytes=MAX_ASSIGNMENT_BYTES,
        kind="submission",
    )
    submission_number = (
        int(
            db.scalar(
                select(func.count(AssignmentSubmission.id)).where(
                    AssignmentSubmission.assignment_id == assignment.id,
                    AssignmentSubmission.enrollment_id == enrollment.id,
                )
            )
            or 0
        )
        + 1
    )
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        enrollment_id=enrollment.id,
        submission_number=submission_number,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        content=content,
    )
    db.add(submission)
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assignment_submitted",
        course_id=str(assignment.course_id),
        assignment_id=str(assignment.id),
        submission_id=str(submission.id),
    )
    db.commit()
    return load_submission(db, submission.id)


def load_submission(db: Session, submission_id: UUID) -> AssignmentSubmission:
    submission = db.scalar(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.id == submission_id)
        .options(
            joinedload(AssignmentSubmission.assignment)
            .joinedload(Assignment.course)
            .joinedload(Course.programme),
            joinedload(AssignmentSubmission.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(AssignmentSubmission.reviewed_by).joinedload(User.profile),
        )
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Assignment submission not found")
    return submission


def list_submissions(
    db: Session, user: User, assignment: Assignment
) -> list[AssignmentSubmissionPublic]:
    ensure_manager(db, user, assignment.course)
    items = db.scalars(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == assignment.id)
        .options(
            joinedload(AssignmentSubmission.enrollment)
            .joinedload(ProgrammeEnrollment.trainee)
            .joinedload(User.profile),
            joinedload(AssignmentSubmission.reviewed_by).joinedload(User.profile),
        )
        .order_by(AssignmentSubmission.submitted_at.desc())
    ).unique()
    return [submission_public(item) for item in items]


def review_submission(
    db: Session,
    request: Request,
    user: User,
    submission: AssignmentSubmission,
    payload: AssignmentReview,
) -> AssignmentSubmission:
    ensure_manager(db, user, submission.assignment.course)
    if payload.score is not None and payload.score > submission.assignment.max_score:
        raise HTTPException(status_code=422, detail="Score cannot exceed the assignment maximum")
    submission.score = payload.score
    submission.trainer_feedback = payload.trainer_feedback
    submission.status = payload.status
    submission.reviewed_by_id = user.id
    submission.reviewed_at = utc_now()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assignment_reviewed",
        course_id=str(submission.assignment.course_id),
        submission_id=str(submission.id),
        status=payload.status.value,
    )
    db.commit()
    return load_submission(db, submission.id)


def submission_file_for_user(db: Session, user: User, submission_id: UUID) -> AssignmentSubmission:
    submission = load_submission(db, submission_id)
    if submission.enrollment.trainee_id == user.id:
        return submission
    ensure_manager(db, user, submission.assignment.course)
    return submission


def create_question_bank(
    db: Session,
    request: Request,
    user: User,
    course: Course,
    payload: QuestionBankCreate,
) -> QuestionBank:
    ensure_manager(db, user, course)
    bank = QuestionBank(course_id=course.id, **payload.model_dump())
    db.add(bank)
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.question_bank_created",
        course_id=str(course.id),
        question_bank_id=str(bank.id),
    )
    db.commit()
    return load_question_bank(db, bank.id)


def load_question_bank(db: Session, bank_id: UUID) -> QuestionBank:
    bank = db.scalar(
        select(QuestionBank)
        .where(QuestionBank.id == bank_id)
        .options(
            joinedload(QuestionBank.course).joinedload(Course.programme),
            selectinload(QuestionBank.questions),
        )
    )
    if bank is None:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return bank


def question_bank_public(bank: QuestionBank) -> QuestionBankPublic:
    return QuestionBankPublic(
        id=bank.id,
        title=bank.title,
        description=bank.description,
        questions=[QuestionManagerPublic.model_validate(item) for item in bank.questions],
    )


def list_question_banks(db: Session, user: User, course: Course) -> list[QuestionBankPublic]:
    ensure_manager(db, user, course)
    banks = db.scalars(
        select(QuestionBank)
        .where(QuestionBank.course_id == course.id)
        .options(selectinload(QuestionBank.questions))
        .order_by(QuestionBank.title)
    ).all()
    return [question_bank_public(item) for item in banks]


def add_question(
    db: Session,
    request: Request,
    user: User,
    bank: QuestionBank,
    payload: QuestionCreate,
) -> QuestionBank:
    ensure_manager(db, user, bank.course)
    if db.scalar(
        select(Question.id).where(
            Question.question_bank_id == bank.id, Question.position == payload.position
        )
    ):
        raise HTTPException(status_code=409, detail="Question position is already in use")
    db.add(Question(question_bank_id=bank.id, **payload.model_dump()))
    add_learning_audit(
        db,
        request,
        user,
        "learning.question_added",
        course_id=str(bank.course_id),
        question_bank_id=str(bank.id),
    )
    db.commit()
    return load_question_bank(db, bank.id)


def create_assessment(
    db: Session,
    request: Request,
    user: User,
    course: Course,
    payload: AssessmentCreate,
) -> LearnerAssessment:
    ensure_manager(db, user, course)
    bank = load_question_bank(db, payload.question_bank_id)
    if bank.course_id != course.id:
        raise HTTPException(status_code=422, detail="Question bank is outside this course")
    if payload.is_published and not bank.questions:
        raise HTTPException(status_code=409, detail="Add questions before publishing assessment")
    assessment = LearnerAssessment(course_id=course.id, **payload.model_dump())
    db.add(assessment)
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assessment_created",
        course_id=str(course.id),
        assessment_id=str(assessment.id),
    )
    db.commit()
    return load_assessment(db, assessment.id)


def load_assessment(db: Session, assessment_id: UUID) -> LearnerAssessment:
    assessment = db.scalar(
        select(LearnerAssessment)
        .where(LearnerAssessment.id == assessment_id)
        .options(
            joinedload(LearnerAssessment.course)
            .joinedload(Course.programme)
            .joinedload(Programme.institution),
            joinedload(LearnerAssessment.question_bank).selectinload(QuestionBank.questions),
        )
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def attempt_public(db: Session, attempt: AssessmentAttempt) -> AssessmentAttemptPublic:
    identifiers = [UUID(item) for item in attempt.question_ids]
    questions = list(db.scalars(select(Question).where(Question.id.in_(identifiers))).all())
    by_id = {item.id: item for item in questions}
    ordered = [by_id[item] for item in identifiers if item in by_id]
    return AssessmentAttemptPublic(
        id=attempt.id,
        assessment_id=attempt.assessment_id,
        assessment_title=attempt.assessment.title,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        questions=[
            QuestionForAttempt(
                id=item.id,
                prompt=item.prompt,
                choices=item.choices,
                points=item.points,
                position=item.position,
            )
            for item in ordered
        ],
        score_percent=attempt.score_percent,
        points_earned=attempt.points_earned,
        points_available=attempt.points_available,
        passed=attempt.passed,
        grading_details=[
            GradingDetailPublic.model_validate(item) for item in attempt.grading_details
        ],
        trainer_feedback=attempt.trainer_feedback,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
    )


def load_attempt(db: Session, attempt_id: UUID) -> AssessmentAttempt:
    attempt = db.scalar(
        select(AssessmentAttempt)
        .where(AssessmentAttempt.id == attempt_id)
        .options(
            joinedload(AssessmentAttempt.assessment)
            .joinedload(LearnerAssessment.course)
            .joinedload(Course.programme),
            joinedload(AssessmentAttempt.enrollment),
        )
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    return attempt


def attempt_for_user(db: Session, user: User, attempt_id: UUID) -> AssessmentAttempt:
    attempt = load_attempt(db, attempt_id)
    if attempt.enrollment.trainee_id == user.id:
        return attempt
    ensure_manager(db, user, attempt.assessment.course)
    return attempt


def start_assessment(
    db: Session,
    request: Request,
    user: User,
    assessment: LearnerAssessment,
) -> AssessmentAttempt:
    enrollment = enrollment_for_course(db, user, assessment.course)
    if not assessment.is_published:
        raise HTTPException(status_code=404, detail="Assessment not found")
    existing = db.scalar(
        select(AssessmentAttempt).where(
            AssessmentAttempt.assessment_id == assessment.id,
            AssessmentAttempt.enrollment_id == enrollment.id,
            AssessmentAttempt.status == AssessmentAttemptStatus.IN_PROGRESS,
        )
    )
    if existing:
        return load_attempt(db, existing.id)
    attempts_used = int(
        db.scalar(
            select(func.count(AssessmentAttempt.id)).where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.enrollment_id == enrollment.id,
            )
        )
        or 0
    )
    if attempts_used >= assessment.attempt_limit:
        raise HTTPException(status_code=409, detail="Assessment attempt limit has been reached")
    questions = sorted(assessment.question_bank.questions, key=lambda item: item.position)
    if not questions:
        raise HTTPException(status_code=409, detail="Assessment has no questions")
    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        enrollment_id=enrollment.id,
        attempt_number=attempts_used + 1,
        question_ids=[str(item.id) for item in questions],
        answers={},
        grading_details=[],
    )
    db.add(attempt)
    db.flush()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assessment_started",
        course_id=str(assessment.course_id),
        assessment_id=str(assessment.id),
        attempt_id=str(attempt.id),
    )
    db.commit()
    return load_attempt(db, attempt.id)


def list_assessment_attempts(
    db: Session, user: User, assessment: LearnerAssessment
) -> list[AssessmentAttemptPublic]:
    ensure_manager(db, user, assessment.course)
    attempt_ids = db.scalars(
        select(AssessmentAttempt.id)
        .where(AssessmentAttempt.assessment_id == assessment.id)
        .order_by(AssessmentAttempt.started_at.desc())
    ).all()
    return [attempt_public(db, load_attempt(db, item)) for item in attempt_ids]


def submit_assessment(
    db: Session,
    request: Request,
    user: User,
    attempt: AssessmentAttempt,
    payload: AssessmentSubmission,
) -> AssessmentAttempt:
    if attempt.enrollment.trainee_id != user.id:
        raise HTTPException(status_code=403, detail="This attempt belongs to another trainee")
    if attempt.status != AssessmentAttemptStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Assessment attempt is already submitted")
    ordered_question_ids = [UUID(item) for item in attempt.question_ids]
    question_ids = set(ordered_question_ids)
    answer_map = {item.question_id: item.option_index for item in payload.answers}
    if not set(answer_map).issubset(question_ids):
        raise HTTPException(status_code=422, detail="Answers contain an unexpected question")
    loaded_questions = db.scalars(select(Question).where(Question.id.in_(question_ids))).all()
    questions_by_id = {item.id: item for item in loaded_questions}
    questions = [questions_by_id[item] for item in ordered_question_ids if item in questions_by_id]
    points_available = sum(item.points for item in questions)
    points_earned = 0.0
    details: list[dict[str, Any]] = []
    for question in questions:
        selected = answer_map.get(question.id)
        if selected is not None and selected >= len(question.choices):
            raise HTTPException(status_code=422, detail="Answer option is outside the choices")
        correct = selected == question.correct_option_index
        earned = question.points if correct else 0.0
        points_earned += earned
        details.append(
            {
                "question_id": str(question.id),
                "selected_option_index": selected,
                "correct": correct,
                "points_earned": earned,
                "explanation": question.explanation,
            }
        )
    score = round(points_earned / points_available * 100, 2) if points_available else 0.0
    attempt.answers = {str(key): value for key, value in answer_map.items()}
    attempt.grading_details = details
    attempt.points_earned = points_earned
    attempt.points_available = points_available
    attempt.score_percent = score
    attempt.passed = score >= attempt.assessment.passing_score_percent
    attempt.status = AssessmentAttemptStatus.SUBMITTED
    attempt.submitted_at = utc_now()
    db.add(
        AssessmentRecord(
            enrollment_id=attempt.enrollment_id,
            title=attempt.assessment.title,
            score=score,
            maximum_score=100,
            result=AssessmentResult.PASSED if attempt.passed else AssessmentResult.FAILED,
            assessed_at=attempt.submitted_at,
        )
    )
    add_learning_audit(
        db,
        request,
        user,
        "learning.assessment_submitted",
        course_id=str(attempt.assessment.course_id),
        assessment_id=str(attempt.assessment_id),
        attempt_id=str(attempt.id),
        score_percent=score,
        passed=attempt.passed,
    )
    db.commit()
    return load_attempt(db, attempt.id)


def add_assessment_feedback(
    db: Session,
    request: Request,
    user: User,
    attempt: AssessmentAttempt,
    payload: AssessmentFeedback,
) -> AssessmentAttempt:
    ensure_manager(db, user, attempt.assessment.course)
    if attempt.status != AssessmentAttemptStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail="Submit the assessment before adding feedback")
    attempt.trainer_feedback = payload.trainer_feedback
    attempt.reviewed_by_id = user.id
    attempt.reviewed_at = utc_now()
    add_learning_audit(
        db,
        request,
        user,
        "learning.assessment_feedback_added",
        course_id=str(attempt.assessment.course_id),
        attempt_id=str(attempt.id),
    )
    db.commit()
    return load_attempt(db, attempt.id)
