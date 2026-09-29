from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import Permission, has_permission
from app.models import (
    ApplicationStatus,
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentType,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceStatus,
    Course,
    CourseModule,
    CourseSection,
    CourseStatus,
    DigitalCertificate,
    EmployerProfile,
    EnrollmentStatus,
    Institution,
    JobApplication,
    JobApplicationStatus,
    JobPosting,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonProgress,
    Programme,
    ProgrammeApplication,
    ProgrammeEnrollment,
    ProgrammeNomination,
    TraineeProfile,
    User,
)
from app.schemas.analytics import (
    AnalyticsAppliedFilters,
    AnalyticsDashboardResponse,
    AnalyticsDrilldownColumn,
    AnalyticsDrilldownResponse,
    AnalyticsFilterOptions,
    AnalyticsGeographyRow,
    AnalyticsInstitutionOption,
    AnalyticsMetric,
    AnalyticsMetricKey,
    AnalyticsPerformanceRow,
    AnalyticsProgrammeOption,
)
from app.services.profiles import scoped_institution_ids

PARTICIPANT_CATEGORIES = ["individual", "pacs", "shg", "cooperative_institution"]

METRIC_DEFINITIONS: dict[str, tuple[str, str, str]] = {
    "registrations": (
        "Registrations",
        "count",
        "Individual applications plus institutional nominations for the selected programmes.",
    ),
    "approved_participants": (
        "Approved participants",
        "count",
        "Registrations whose current review status is approved.",
    ),
    "attendance_percentage": (
        "Attendance percentage",
        "percent",
        "Present check-ins divided by expected trainee-session attendances for "
        "non-cancelled sessions.",
    ),
    "course_completion_rate": (
        "Course-completion rate",
        "percent",
        "Enrolments completing every required lesson in a published course, divided by "
        "measurable enrolments.",
    ),
    "assessment_improvement": (
        "Assessment improvement",
        "percentage_points",
        "Average difference between each trainee's best post-training and best pre-training score.",
    ),
    "dropout_rate": (
        "Dropout rate",
        "percent",
        "Withdrawn enrolments divided by all enrolments in the selected programme cohort.",
    ),
    "certificates_issued": (
        "Certificates issued",
        "count",
        "Digital certificates issued for selected enrolments, including certificates later "
        "revoked or expired.",
    ),
    "job_applications": (
        "Job applications",
        "count",
        "Distinct employment applications submitted by trainees in the selected enrolment cohort.",
    ),
    "interviews": (
        "Interviews",
        "count",
        "Cohort job applications with an interview date recorded.",
    ),
    "placements": (
        "Placements",
        "count",
        "Cohort job applications whose current hiring status is hired.",
    ),
}


@dataclass(frozen=True)
class AnalyticsFilters:
    institution_id: UUID | None = None
    programme_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    state: str | None = None
    gender: str | None = None
    participant_category: str | None = None


@dataclass(frozen=True)
class Participant:
    user_id: UUID | None
    name: str
    email: str
    state: str | None
    gender: str | None
    is_demo: bool


@dataclass(frozen=True)
class RegistrationEntry:
    id: UUID
    programme_id: UUID
    participant: Participant
    category: str
    status: ApplicationStatus
    source: str
    submitted_at: datetime


@dataclass(frozen=True)
class EnrollmentEntry:
    enrollment: ProgrammeEnrollment
    participant: Participant
    category: str


@dataclass
class AnalyticsDataset:
    programmes: list[Programme]
    registrations: list[RegistrationEntry]
    enrollments: list[EnrollmentEntry]
    sessions: list[AttendanceSession]
    present_pairs: set[tuple[UUID, UUID]]
    required_lessons: dict[UUID, set[UUID]]
    completed_lessons: dict[UUID, set[UUID]]
    assessment_scores: dict[UUID, dict[AssessmentType, float]]
    certificates: list[DigitalCertificate]
    jobs: list[JobApplication]
    job_programmes: dict[UUID, set[UUID]]


def _normalise(value: str | None) -> str | None:
    return value.strip().casefold() if value and value.strip() else None


def _name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def _participant(user: User | None, *, name: str = "", email: str = "") -> Participant:
    if user is None:
        return Participant(None, name or email, email, None, None, False)
    profile = user.trainee_profile
    return Participant(
        user.id,
        _name(user),
        user.email,
        profile.state if profile else None,
        profile.gender if profile else None,
        bool(profile and profile.is_demo),
    )


def _matches_participant(participant: Participant, filters: AnalyticsFilters) -> bool:
    if filters.state and _normalise(participant.state) != _normalise(filters.state):
        return False
    if filters.gender and _normalise(participant.gender) != _normalise(filters.gender):
        return False
    return True


def _programme_query(db: Session, user: User, filters: AnalyticsFilters) -> list[Programme]:
    if filters.start_date and filters.end_date and filters.start_date > filters.end_date:
        raise HTTPException(status_code=422, detail="Start date must be on or before end date")
    if filters.participant_category and filters.participant_category not in PARTICIPANT_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported participant category")

    allowed = scoped_institution_ids(db, user)
    if filters.institution_id and allowed is not None and filters.institution_id not in allowed:
        raise HTTPException(status_code=403, detail="Institution is outside your analytics scope")

    statement = select(Programme).options(joinedload(Programme.institution))
    if allowed is not None:
        if not allowed:
            return []
        statement = statement.where(Programme.institution_id.in_(allowed))
    if filters.institution_id:
        statement = statement.where(Programme.institution_id == filters.institution_id)
    if filters.programme_id:
        statement = statement.where(Programme.id == filters.programme_id)
    if filters.start_date:
        statement = statement.where(Programme.start_date >= filters.start_date)
    if filters.end_date:
        statement = statement.where(Programme.start_date <= filters.end_date)
    return list(
        db.scalars(statement.order_by(Programme.start_date.desc(), Programme.title)).unique()
    )


def _load_dataset(db: Session, user: User, filters: AnalyticsFilters) -> AnalyticsDataset:
    programmes = _programme_query(db, user, filters)
    programme_ids = {programme.id for programme in programmes}
    if not programme_ids:
        return AnalyticsDataset(programmes, [], [], [], set(), {}, {}, {}, [], [], {})

    applications = list(
        db.scalars(
            select(ProgrammeApplication)
            .where(ProgrammeApplication.programme_id.in_(programme_ids))
            .options(
                joinedload(ProgrammeApplication.trainee).joinedload(User.profile),
                joinedload(ProgrammeApplication.trainee).joinedload(User.trainee_profile),
            )
        ).unique()
    )
    nominations = list(
        db.scalars(
            select(ProgrammeNomination).where(ProgrammeNomination.programme_id.in_(programme_ids))
        )
    )

    nomination_emails = {_normalise(item.candidate_email) for item in nominations}
    nomination_emails.discard(None)
    nominated_users: dict[str, User] = {}
    if nomination_emails:
        users = db.scalars(
            select(User)
            .where(func.lower(User.email).in_(nomination_emails))
            .options(joinedload(User.profile), joinedload(User.trainee_profile))
        ).unique()
        nominated_users = {user.email.casefold(): user for user in users}

    registrations: list[RegistrationEntry] = []
    category_by_enrolment_key: dict[tuple[UUID, UUID], str] = {}
    for application in applications:
        participant = _participant(application.trainee)
        category = "individual"
        if _matches_participant(participant, filters) and (
            not filters.participant_category or filters.participant_category == category
        ):
            registrations.append(
                RegistrationEntry(
                    application.id,
                    application.programme_id,
                    participant,
                    category,
                    application.status,
                    "Individual application",
                    application.submitted_at,
                )
            )
        if application.status == ApplicationStatus.APPROVED:
            category_by_enrolment_key[(application.programme_id, application.trainee_id)] = category

    for nomination in nominations:
        user_match = nominated_users.get(nomination.candidate_email.casefold())
        participant = _participant(
            user_match,
            name=nomination.candidate_full_name,
            email=nomination.candidate_email,
        )
        category = nomination.nomination_type.value
        if _matches_participant(participant, filters) and (
            not filters.participant_category or filters.participant_category == category
        ):
            registrations.append(
                RegistrationEntry(
                    nomination.id,
                    nomination.programme_id,
                    participant,
                    category,
                    nomination.status,
                    "Institutional nomination",
                    nomination.submitted_at,
                )
            )
        if user_match and nomination.status == ApplicationStatus.APPROVED:
            category_by_enrolment_key.setdefault((nomination.programme_id, user_match.id), category)

    raw_enrollments = list(
        db.scalars(
            select(ProgrammeEnrollment)
            .where(ProgrammeEnrollment.programme_id.in_(programme_ids))
            .options(
                joinedload(ProgrammeEnrollment.trainee).joinedload(User.profile),
                joinedload(ProgrammeEnrollment.trainee).joinedload(User.trainee_profile),
            )
        ).unique()
    )
    enrollments: list[EnrollmentEntry] = []
    for enrollment in raw_enrollments:
        participant = _participant(enrollment.trainee)
        category = category_by_enrolment_key.get(
            (enrollment.programme_id, enrollment.trainee_id), "individual"
        )
        if not _matches_participant(participant, filters):
            continue
        if filters.participant_category and category != filters.participant_category:
            continue
        enrollments.append(EnrollmentEntry(enrollment, participant, category))

    enrollment_ids = {item.enrollment.id for item in enrollments}
    sessions = list(
        db.scalars(
            select(AttendanceSession).where(
                AttendanceSession.programme_id.in_(programme_ids),
                AttendanceSession.status != AttendanceSessionStatus.CANCELLED,
            )
        )
    )
    session_ids = {session.id for session in sessions}
    present_pairs: set[tuple[UUID, UUID]] = set()
    if session_ids and enrollment_ids:
        present_pairs = set(
            db.execute(
                select(
                    AttendanceCheckIn.attendance_session_id,
                    AttendanceCheckIn.enrollment_id,
                ).where(
                    AttendanceCheckIn.attendance_session_id.in_(session_ids),
                    AttendanceCheckIn.enrollment_id.in_(enrollment_ids),
                    AttendanceCheckIn.status == AttendanceStatus.PRESENT,
                )
            ).all()
        )

    required_lessons: dict[UUID, set[UUID]] = defaultdict(set)
    lesson_rows = db.execute(
        select(Course.programme_id, Lesson.id)
        .select_from(Course)
        .join(CourseSection, CourseSection.course_id == Course.id)
        .join(CourseModule, CourseModule.section_id == CourseSection.id)
        .join(Lesson, Lesson.module_id == CourseModule.id)
        .where(
            Course.programme_id.in_(programme_ids),
            Course.status == CourseStatus.PUBLISHED,
            Lesson.is_required.is_(True),
        )
    ).all()
    for programme_id, lesson_id in lesson_rows:
        required_lessons[programme_id].add(lesson_id)

    completed_lessons: dict[UUID, set[UUID]] = defaultdict(set)
    if enrollment_ids:
        for enrollment_id, lesson_id in db.execute(
            select(LessonProgress.enrollment_id, LessonProgress.lesson_id).where(
                LessonProgress.enrollment_id.in_(enrollment_ids),
                LessonProgress.status == LearningProgressStatus.COMPLETED,
            )
        ):
            completed_lessons[enrollment_id].add(lesson_id)

    assessment_scores: dict[UUID, dict[AssessmentType, float]] = defaultdict(dict)
    if enrollment_ids:
        attempt_rows = db.execute(
            select(
                AssessmentAttempt.enrollment_id,
                LearnerAssessment.assessment_type,
                AssessmentAttempt.score_percent,
            )
            .join(
                LearnerAssessment,
                LearnerAssessment.id == AssessmentAttempt.assessment_id,
            )
            .where(
                AssessmentAttempt.enrollment_id.in_(enrollment_ids),
                AssessmentAttempt.status == AssessmentAttemptStatus.SUBMITTED,
                AssessmentAttempt.score_percent.is_not(None),
                LearnerAssessment.assessment_type.in_(
                    [AssessmentType.PRE_TRAINING, AssessmentType.POST_TRAINING]
                ),
            )
        ).all()
        for enrollment_id, assessment_type, score in attempt_rows:
            if score is None:
                continue
            current = assessment_scores[enrollment_id].get(assessment_type)
            if current is None or float(score) > current:
                assessment_scores[enrollment_id][assessment_type] = float(score)

    certificates: list[DigitalCertificate] = []
    jobs: list[JobApplication] = []
    job_programmes: dict[UUID, set[UUID]] = defaultdict(set)
    if enrollment_ids:
        certificates = list(
            db.scalars(
                select(DigitalCertificate).where(
                    DigitalCertificate.enrollment_id.in_(enrollment_ids)
                )
            )
        )
        trainee_programmes: dict[UUID, set[UUID]] = defaultdict(set)
        for item in enrollments:
            trainee_programmes[item.enrollment.trainee_id].add(item.enrollment.programme_id)
        jobs = list(
            db.scalars(
                select(JobApplication)
                .where(JobApplication.trainee_id.in_(trainee_programmes))
                .options(
                    joinedload(JobApplication.trainee).joinedload(User.profile),
                    joinedload(JobApplication.job)
                    .joinedload(JobPosting.employer)
                    .joinedload(EmployerProfile.institution),
                )
            ).unique()
        )
        for job in jobs:
            job_programmes[job.id].update(trainee_programmes[job.trainee_id])

    return AnalyticsDataset(
        programmes,
        registrations,
        enrollments,
        sessions,
        present_pairs,
        dict(required_lessons),
        dict(completed_lessons),
        dict(assessment_scores),
        certificates,
        jobs,
        dict(job_programmes),
    )


def _calculate(
    dataset: AnalyticsDataset, programme_ids: set[UUID]
) -> dict[str, tuple[float, float | None]]:
    registrations = [item for item in dataset.registrations if item.programme_id in programme_ids]
    enrollments = [
        item for item in dataset.enrollments if item.enrollment.programme_id in programme_ids
    ]
    enrollment_ids = {item.enrollment.id for item in enrollments}

    expected_pairs: set[tuple[UUID, UUID]] = set()
    for session in dataset.sessions:
        if session.programme_id not in programme_ids:
            continue
        for item in enrollments:
            enrollment = item.enrollment
            if (
                enrollment.programme_id == session.programme_id
                and enrollment.batch_id == session.batch_id
            ):
                expected_pairs.add((session.id, enrollment.id))
    present_count = len(expected_pairs & dataset.present_pairs)

    measurable = [
        item for item in enrollments if dataset.required_lessons.get(item.enrollment.programme_id)
    ]
    completed_count = sum(
        dataset.required_lessons[item.enrollment.programme_id]
        <= dataset.completed_lessons.get(item.enrollment.id, set())
        for item in measurable
    )

    improvements: list[float] = []
    for item in enrollments:
        scores = dataset.assessment_scores.get(item.enrollment.id, {})
        if AssessmentType.PRE_TRAINING in scores and AssessmentType.POST_TRAINING in scores:
            improvements.append(
                scores[AssessmentType.POST_TRAINING] - scores[AssessmentType.PRE_TRAINING]
            )

    jobs = [
        job for job in dataset.jobs if dataset.job_programmes.get(job.id, set()) & programme_ids
    ]
    certificates = [item for item in dataset.certificates if item.enrollment_id in enrollment_ids]
    return {
        "registrations": (float(len(registrations)), None),
        "approved_participants": (
            float(sum(item.status == ApplicationStatus.APPROVED for item in registrations)),
            None,
        ),
        "attendance_percentage": (
            round(present_count / len(expected_pairs) * 100, 1) if expected_pairs else 0.0,
            float(len(expected_pairs)),
        ),
        "course_completion_rate": (
            round(completed_count / len(measurable) * 100, 1) if measurable else 0.0,
            float(len(measurable)),
        ),
        "assessment_improvement": (
            round(sum(improvements) / len(improvements), 1) if improvements else 0.0,
            float(len(improvements)),
        ),
        "dropout_rate": (
            round(
                sum(item.enrollment.status == EnrollmentStatus.WITHDRAWN for item in enrollments)
                / len(enrollments)
                * 100,
                1,
            )
            if enrollments
            else 0.0,
            float(len(enrollments)),
        ),
        "certificates_issued": (float(len(certificates)), None),
        "job_applications": (float(len(jobs)), None),
        "interviews": (float(sum(job.interview_at is not None for job in jobs)), None),
        "placements": (
            float(sum(job.status == JobApplicationStatus.HIRED for job in jobs)),
            None,
        ),
    }


def _metric_numerator(key: str, value: float, denominator: float | None) -> float:
    if denominator is None:
        return value
    if key == "assessment_improvement":
        return round(value * denominator, 1)
    return round(value * denominator / 100, 1)


def _metrics(dataset: AnalyticsDataset, programme_ids: set[UUID]) -> list[AnalyticsMetric]:
    calculated = _calculate(dataset, programme_ids)
    metrics: list[AnalyticsMetric] = []
    for key, (label, unit, definition) in METRIC_DEFINITIONS.items():
        value, denominator = calculated[key]
        metrics.append(
            AnalyticsMetric(
                key=key,
                label=label,
                value=value,
                unit=unit,
                numerator=_metric_numerator(key, value, denominator),
                denominator=denominator,
                definition=definition,
            )
        )
    return metrics


def _performance_row(
    dataset: AnalyticsDataset,
    programme_ids: set[UUID],
    *,
    row_id: UUID,
    label: str,
    secondary_label: str,
    is_demo: bool,
) -> AnalyticsPerformanceRow:
    values = _calculate(dataset, programme_ids)
    enrollment_count = sum(
        item.enrollment.programme_id in programme_ids for item in dataset.enrollments
    )
    return AnalyticsPerformanceRow(
        id=row_id,
        label=label,
        secondary_label=secondary_label,
        is_demo=is_demo,
        registrations=int(values["registrations"][0]),
        approved_participants=int(values["approved_participants"][0]),
        enrollments=enrollment_count,
        attendance_percentage=values["attendance_percentage"][0],
        course_completion_rate=values["course_completion_rate"][0],
        assessment_improvement=values["assessment_improvement"][0],
        dropout_rate=values["dropout_rate"][0],
        certificates_issued=int(values["certificates_issued"][0]),
        job_applications=int(values["job_applications"][0]),
        interviews=int(values["interviews"][0]),
        placements=int(values["placements"][0]),
    )


def _geography(dataset: AnalyticsDataset, programme_ids: set[UUID]) -> list[AnalyticsGeographyRow]:
    values: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    enrolment_by_id = {
        item.enrollment.id: item
        for item in dataset.enrollments
        if item.enrollment.programme_id in programme_ids
    }
    for registration in dataset.registrations:
        if registration.programme_id not in programme_ids:
            continue
        state = registration.participant.state or "Not provided"
        values[state]["registrations"] += 1
        if registration.status == ApplicationStatus.APPROVED:
            values[state]["approved_participants"] += 1
    for item in enrolment_by_id.values():
        values[item.participant.state or "Not provided"]["enrollments"] += 1
    for certificate in dataset.certificates:
        enrollment = enrolment_by_id.get(certificate.enrollment_id)
        if enrollment:
            values[enrollment.participant.state or "Not provided"]["certificates_issued"] += 1
    for job in dataset.jobs:
        if job.status != JobApplicationStatus.HIRED:
            continue
        eligible = [
            item
            for item in enrolment_by_id.values()
            if item.enrollment.trainee_id == job.trainee_id
        ]
        if eligible:
            values[eligible[0].participant.state or "Not provided"]["placements"] += 1
    return [
        AnalyticsGeographyRow(state=state, **counts)
        for state, counts in sorted(
            values.items(), key=lambda item: (-item[1]["enrollments"], item[0])
        )
    ]


def filter_options(db: Session, user: User) -> AnalyticsFilterOptions:
    allowed = scoped_institution_ids(db, user)
    institution_statement = select(Institution).where(Institution.is_active.is_(True))
    programme_statement = select(Programme).options(joinedload(Programme.institution))
    if allowed is not None:
        if not allowed:
            return AnalyticsFilterOptions(
                institutions=[],
                programmes=[],
                states=[],
                genders=[],
                participant_categories=PARTICIPANT_CATEGORIES,
                start_date_min=None,
                start_date_max=None,
            )
        institution_statement = institution_statement.where(Institution.id.in_(allowed))
        programme_statement = programme_statement.where(Programme.institution_id.in_(allowed))
    institutions = list(db.scalars(institution_statement.order_by(Institution.name)))
    programmes = list(
        db.scalars(
            programme_statement.order_by(Programme.start_date.desc(), Programme.title)
        ).unique()
    )
    programme_ids = {item.id for item in programmes}
    states: set[str] = set()
    genders: set[str] = set()
    if programme_ids:
        profile_rows = db.execute(
            select(TraineeProfile.state, TraineeProfile.gender)
            .join(User, User.id == TraineeProfile.user_id)
            .join(ProgrammeEnrollment, ProgrammeEnrollment.trainee_id == User.id)
            .where(ProgrammeEnrollment.programme_id.in_(programme_ids))
        ).all()
        states = {state for state, _ in profile_rows if state}
        genders = {gender for _, gender in profile_rows if gender}
    dates = [programme.start_date for programme in programmes]
    return AnalyticsFilterOptions(
        institutions=[
            AnalyticsInstitutionOption(
                id=item.id,
                name=item.name,
                code=item.code,
                state=item.state,
                is_demo=item.is_demo,
            )
            for item in institutions
        ],
        programmes=[
            AnalyticsProgrammeOption(
                id=item.id,
                institution_id=item.institution_id,
                title=item.title,
                code=item.code,
                start_date=item.start_date,
                is_demo=item.institution.is_demo,
            )
            for item in programmes
        ],
        states=sorted(states),
        genders=sorted(genders),
        participant_categories=PARTICIPANT_CATEGORIES,
        start_date_min=min(dates) if dates else None,
        start_date_max=max(dates) if dates else None,
    )


def dashboard(db: Session, user: User, filters: AnalyticsFilters) -> AnalyticsDashboardResponse:
    dataset = _load_dataset(db, user, filters)
    programme_ids = {programme.id for programme in dataset.programmes}
    institution_programmes: dict[UUID, set[UUID]] = defaultdict(set)
    institution_map: dict[UUID, Institution] = {}
    for programme in dataset.programmes:
        institution_programmes[programme.institution_id].add(programme.id)
        institution_map[programme.institution_id] = programme.institution

    institution_rows = [
        _performance_row(
            dataset,
            ids,
            row_id=institution_id,
            label=institution_map[institution_id].name,
            secondary_label=institution_map[institution_id].code,
            is_demo=institution_map[institution_id].is_demo,
        )
        for institution_id, ids in institution_programmes.items()
    ]
    programme_rows = [
        _performance_row(
            dataset,
            {programme.id},
            row_id=programme.id,
            label=programme.title,
            secondary_label=f"{programme.code} | {programme.institution.name}",
            is_demo=programme.institution.is_demo,
        )
        for programme in dataset.programmes
    ]
    institution_rows.sort(key=lambda row: (-row.approved_participants, row.label))
    programme_rows.sort(key=lambda row: (-row.approved_participants, row.label))

    is_platform = has_permission({role.code for role in user.roles}, Permission.PLATFORM_MANAGE)
    if filters.institution_id and filters.institution_id in institution_map:
        scope_label = institution_map[filters.institution_id].name
    elif is_platform:
        scope_label = "NCCT network"
    elif user.institution:
        scope_label = f"{user.institution.name} and its institutions"
    else:
        scope_label = "No institution assigned"
    contains_demo = (
        any(programme.institution.is_demo for programme in dataset.programmes)
        or any(item.participant.is_demo for item in dataset.registrations)
        or any(item.participant.is_demo for item in dataset.enrollments)
    )
    return AnalyticsDashboardResponse(
        generated_at=datetime.now(UTC),
        scope_label=scope_label,
        contains_demo_data=contains_demo,
        filters=AnalyticsAppliedFilters(**filters.__dict__),
        metrics=_metrics(dataset, programme_ids),
        institution_performance=institution_rows,
        programme_performance=programme_rows,
        geographic_distribution=_geography(dataset, programme_ids),
    )


def _common_row(
    dataset: AnalyticsDataset, programme_id: UUID, participant: Participant
) -> dict[str, str]:
    programme = next(item for item in dataset.programmes if item.id == programme_id)
    return {
        "participant": participant.name,
        "email": participant.email,
        "programme": programme.title,
        "institution": programme.institution.name,
        "state": participant.state or "Not provided",
    }


def _drilldown_rows(
    dataset: AnalyticsDataset, metric: AnalyticsMetricKey
) -> tuple[list[AnalyticsDrilldownColumn], list[dict[str, str | int | float | None]]]:
    rows: list[dict[str, str | int | float | None]] = []
    if metric in {"registrations", "approved_participants"}:
        registration_items = dataset.registrations
        if metric == "approved_participants":
            registration_items = [
                registration
                for registration in registration_items
                if registration.status == ApplicationStatus.APPROVED
            ]
        for registration in registration_items:
            rows.append(
                {
                    **_common_row(dataset, registration.programme_id, registration.participant),
                    "category": registration.category.replace("_", " ").title(),
                    "source": registration.source,
                    "status": registration.status.value.replace("_", " ").title(),
                    "submitted": registration.submitted_at.date().isoformat(),
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="category", label="Category"),
            AnalyticsDrilldownColumn(key="source", label="Source"),
            AnalyticsDrilldownColumn(key="status", label="Status"),
            AnalyticsDrilldownColumn(key="state", label="State"),
            AnalyticsDrilldownColumn(key="submitted", label="Submitted"),
        ]
        return columns, rows

    if metric == "attendance_percentage":
        for enrollment_entry in dataset.enrollments:
            enrollment = enrollment_entry.enrollment
            sessions = [
                session
                for session in dataset.sessions
                if session.programme_id == enrollment.programme_id
                and session.batch_id == enrollment.batch_id
            ]
            if not sessions:
                continue
            present = sum(
                (session.id, enrollment.id) in dataset.present_pairs for session in sessions
            )
            rows.append(
                {
                    **_common_row(dataset, enrollment.programme_id, enrollment_entry.participant),
                    "present": present,
                    "expected": len(sessions),
                    "attendance": round(present / len(sessions) * 100, 1),
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="present", label="Present"),
            AnalyticsDrilldownColumn(key="expected", label="Expected"),
            AnalyticsDrilldownColumn(key="attendance", label="Attendance %"),
        ]
        return columns, rows

    if metric == "course_completion_rate":
        for enrollment_entry in dataset.enrollments:
            enrollment = enrollment_entry.enrollment
            required = dataset.required_lessons.get(enrollment.programme_id, set())
            if not required:
                continue
            completed = len(required & dataset.completed_lessons.get(enrollment.id, set()))
            rows.append(
                {
                    **_common_row(dataset, enrollment.programme_id, enrollment_entry.participant),
                    "completed_lessons": completed,
                    "required_lessons": len(required),
                    "completion": round(completed / len(required) * 100, 1),
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="completed_lessons", label="Completed lessons"),
            AnalyticsDrilldownColumn(key="required_lessons", label="Required lessons"),
            AnalyticsDrilldownColumn(key="completion", label="Completion %"),
        ]
        return columns, rows

    if metric == "assessment_improvement":
        for enrollment_entry in dataset.enrollments:
            enrollment = enrollment_entry.enrollment
            scores = dataset.assessment_scores.get(enrollment.id, {})
            if (
                AssessmentType.PRE_TRAINING not in scores
                or AssessmentType.POST_TRAINING not in scores
            ):
                continue
            pre = scores[AssessmentType.PRE_TRAINING]
            post = scores[AssessmentType.POST_TRAINING]
            rows.append(
                {
                    **_common_row(dataset, enrollment.programme_id, enrollment_entry.participant),
                    "pre_score": pre,
                    "post_score": post,
                    "improvement": round(post - pre, 1),
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="pre_score", label="Pre-training %"),
            AnalyticsDrilldownColumn(key="post_score", label="Post-training %"),
            AnalyticsDrilldownColumn(key="improvement", label="Improvement points"),
        ]
        return columns, rows

    if metric == "dropout_rate":
        dropout_entries = [
            enrollment_entry
            for enrollment_entry in dataset.enrollments
            if enrollment_entry.enrollment.status == EnrollmentStatus.WITHDRAWN
        ]
        for dropout_entry in dropout_entries:
            rows.append(
                {
                    **_common_row(
                        dataset,
                        dropout_entry.enrollment.programme_id,
                        dropout_entry.participant,
                    ),
                    "category": dropout_entry.category.replace("_", " ").title(),
                    "enrolled": dropout_entry.enrollment.enrolled_at.date().isoformat(),
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="category", label="Category"),
            AnalyticsDrilldownColumn(key="enrolled", label="Enrolled"),
        ]
        return columns, rows

    if metric == "certificates_issued":
        enrollment_map = {item.enrollment.id: item for item in dataset.enrollments}
        for certificate in dataset.certificates:
            certificate_entry = enrollment_map.get(certificate.enrollment_id)
            if not certificate_entry:
                continue
            rows.append(
                {
                    **_common_row(
                        dataset,
                        certificate_entry.enrollment.programme_id,
                        certificate_entry.participant,
                    ),
                    "certificate_number": certificate.certificate_number,
                    "issued": certificate.issued_at.date().isoformat(),
                    "state_of_certificate": "Revoked" if certificate.revoked_at else "Issued",
                }
            )
        columns = [
            AnalyticsDrilldownColumn(key="participant", label="Participant"),
            AnalyticsDrilldownColumn(key="programme", label="Programme"),
            AnalyticsDrilldownColumn(key="institution", label="Institution"),
            AnalyticsDrilldownColumn(key="certificate_number", label="Certificate number"),
            AnalyticsDrilldownColumn(key="issued", label="Issued"),
            AnalyticsDrilldownColumn(key="state_of_certificate", label="Certificate state"),
        ]
        return columns, rows

    jobs = dataset.jobs
    if metric == "interviews":
        jobs = [job for job in jobs if job.interview_at is not None]
    elif metric == "placements":
        jobs = [job for job in jobs if job.status == JobApplicationStatus.HIRED]
    enrollment_by_trainee = {item.enrollment.trainee_id: item for item in dataset.enrollments}
    for job in jobs:
        job_enrollment = enrollment_by_trainee.get(job.trainee_id)
        if not job_enrollment:
            continue
        rows.append(
            {
                **_common_row(
                    dataset,
                    job_enrollment.enrollment.programme_id,
                    job_enrollment.participant,
                ),
                "job": job.job.title,
                "employer": job.job.employer.institution.name,
                "application_status": job.status.value.replace("_", " ").title(),
                "applied": job.applied_at.date().isoformat(),
                "interview": job.interview_at.date().isoformat() if job.interview_at else None,
            }
        )
    columns = [
        AnalyticsDrilldownColumn(key="participant", label="Participant"),
        AnalyticsDrilldownColumn(key="job", label="Job"),
        AnalyticsDrilldownColumn(key="employer", label="Employer"),
        AnalyticsDrilldownColumn(key="programme", label="Programme"),
        AnalyticsDrilldownColumn(key="application_status", label="Status"),
        AnalyticsDrilldownColumn(key="applied", label="Applied"),
        AnalyticsDrilldownColumn(key="interview", label="Interview"),
    ]
    return columns, rows


def drilldown(
    db: Session,
    user: User,
    filters: AnalyticsFilters,
    metric: AnalyticsMetricKey,
    page: int,
    page_size: int,
) -> AnalyticsDrilldownResponse:
    dataset = _load_dataset(db, user, filters)
    columns, rows = _drilldown_rows(dataset, metric)
    rows.sort(key=lambda row: (str(row.get("institution", "")), str(row.get("participant", ""))))
    total = len(rows)
    start = (page - 1) * page_size
    label, _, definition = METRIC_DEFINITIONS[metric]
    return AnalyticsDrilldownResponse(
        metric=metric,
        title=f"{label} detail",
        definition=definition,
        columns=columns,
        rows=rows[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def export_csv(dashboard_data: AnalyticsDashboardResponse, view: str) -> str:
    output = io.StringIO()
    if view == "geography":
        fields = [
            "state",
            "registrations",
            "approved_participants",
            "enrollments",
            "certificates_issued",
            "placements",
        ]
        rows = [row.model_dump() for row in dashboard_data.geographic_distribution]
    else:
        fields = [
            "label",
            "secondary_label",
            "is_demo",
            "registrations",
            "approved_participants",
            "enrollments",
            "attendance_percentage",
            "course_completion_rate",
            "assessment_improvement",
            "dropout_rate",
            "certificates_issued",
            "job_applications",
            "interviews",
            "placements",
        ]
        source = (
            dashboard_data.institution_performance
            if view == "institution"
            else dashboard_data.programme_performance
        )
        rows = [row.model_dump() for row in source]
    rows = [
        {
            key: (
                f"'{value}"
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
                else value
            )
            for key, value in row.items()
        }
        for row in rows
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
