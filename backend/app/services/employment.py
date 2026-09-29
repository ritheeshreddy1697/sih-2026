from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.uploads import RESUME_TYPES, read_validated_upload
from app.models import (
    AccountStatus,
    AuditLog,
    CandidateShortlist,
    CertificateState,
    DigitalCertificate,
    EmployerProfile,
    EmployerVerificationStatus,
    JobApplication,
    JobApplicationCertificate,
    JobApplicationStatus,
    JobPosting,
    JobProgrammeRequirement,
    JobStatus,
    Programme,
    ProgrammeEnrollment,
    SavedJob,
    TraineeEmploymentProfile,
    TraineeProfile,
    User,
    VerifiedEmploymentSkill,
)
from app.schemas.employment import (
    CandidateContact,
    CandidatePublic,
    CandidateShortlistCreate,
    CertificateSummary,
    EmployerCompanyUpdate,
    EmployerProfilePublic,
    EmployerVerificationUpdate,
    EmployerWorkspacePublic,
    EmploymentProfilePublic,
    EmploymentProfileUpdate,
    JobApplicationCreate,
    JobApplicationPublic,
    JobApplicationStatusUpdate,
    JobCreate,
    JobPublic,
    JobUpdate,
    MatchBreakdown,
    ProgrammeRequirementPublic,
    TraineeEmploymentWorkspacePublic,
    VerifiedSkillPublic,
)
from app.services.auth import get_client_details
from app.services.certificates import as_utc, certificate_state, verification_url

MAX_RESUME_BYTES = 5 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(UTC)


def display_name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def add_audit(
    db: Session,
    request: Request,
    event_type: str,
    user: User,
    details: dict[str, Any],
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


def employer_options() -> tuple[Any, ...]:
    return (
        joinedload(EmployerProfile.institution),
        joinedload(EmployerProfile.registered_by).joinedload(User.profile),
    )


def job_options() -> tuple[Any, ...]:
    return (
        joinedload(JobPosting.employer).joinedload(EmployerProfile.institution),
        selectinload(JobPosting.programme_requirements).joinedload(
            JobProgrammeRequirement.programme
        ),
    )


def certificate_options() -> tuple[Any, ...]:
    return (joinedload(DigitalCertificate.enrollment).joinedload(ProgrammeEnrollment.programme),)


def load_employer_profile(
    db: Session, user: User, *, require_verified: bool = False
) -> EmployerProfile:
    profile = db.scalar(
        select(EmployerProfile)
        .where(EmployerProfile.institution_id == user.institution_id)
        .options(*employer_options())
    )
    if profile is None:
        raise HTTPException(status_code=403, detail="An employer company profile is required")
    if require_verified and profile.verification_status != EmployerVerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=403,
            detail="The employer must be verified before using recruitment tools",
        )
    return profile


def employer_public(profile: EmployerProfile) -> EmployerProfilePublic:
    return EmployerProfilePublic(
        id=profile.id,
        institution_id=profile.institution_id,
        company_name=profile.institution.name,
        institution_code=profile.institution.code,
        contact_name=display_name(profile.registered_by),
        contact_email=profile.registered_by.email,
        industry=profile.industry,
        website=profile.website,
        company_size=profile.company_size,
        description=profile.description,
        headquarters=profile.headquarters,
        registration_number=profile.registration_number,
        verification_status=profile.verification_status,
        verification_notes=profile.verification_notes,
        verified_at=profile.verified_at,
        updated_at=profile.updated_at,
    )


def list_employers(
    db: Session, status: EmployerVerificationStatus | None
) -> list[EmployerProfilePublic]:
    statement = (
        select(EmployerProfile)
        .options(*employer_options())
        .order_by(EmployerProfile.created_at.desc())
    )
    if status is not None:
        statement = statement.where(EmployerProfile.verification_status == status)
    return [employer_public(profile) for profile in db.scalars(statement)]


def verify_employer(
    db: Session,
    request: Request,
    user: User,
    profile_id: UUID,
    payload: EmployerVerificationUpdate,
) -> EmployerProfilePublic:
    profile = db.scalar(
        select(EmployerProfile).where(EmployerProfile.id == profile_id).options(*employer_options())
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    profile.verification_status = payload.status
    profile.verification_notes = payload.notes
    profile.verified_by_id = user.id
    profile.verified_at = utc_now()
    if payload.status == EmployerVerificationStatus.VERIFIED:
        profile.institution.is_active = True
        profile.registered_by.status = AccountStatus.ACTIVE
        profile.registered_by.email_verified_at = (
            profile.registered_by.email_verified_at or utc_now()
        )
    else:
        profile.institution.is_active = False
        profile.registered_by.status = AccountStatus.SUSPENDED
    add_audit(
        db,
        request,
        "employment.employer_verified"
        if payload.status == EmployerVerificationStatus.VERIFIED
        else "employment.employer_rejected",
        user,
        {"employer_profile_id": str(profile.id), "notes": payload.notes},
    )
    db.commit()
    refreshed = db.scalar(
        select(EmployerProfile).where(EmployerProfile.id == profile.id).options(*employer_options())
    )
    assert refreshed is not None
    return employer_public(refreshed)


def update_employer_profile(
    db: Session,
    request: Request,
    user: User,
    payload: EmployerCompanyUpdate,
) -> EmployerProfilePublic:
    profile = load_employer_profile(db, user)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    add_audit(
        db,
        request,
        "employment.company_profile_updated",
        user,
        {"employer_profile_id": str(profile.id)},
    )
    db.commit()
    refreshed = load_employer_profile(db, user)
    return employer_public(refreshed)


def _valid_certificates(db: Session, trainee_id: UUID) -> list[DigitalCertificate]:
    certificates = list(
        db.scalars(
            select(DigitalCertificate)
            .join(ProgrammeEnrollment)
            .where(ProgrammeEnrollment.trainee_id == trainee_id)
            .options(*certificate_options())
            .order_by(DigitalCertificate.issued_at.desc())
        )
    )
    return [
        certificate
        for certificate in certificates
        if certificate_state(certificate) == CertificateState.VALID
    ]


def _valid_skills(
    db: Session, trainee_id: UUID, certificates: list[DigitalCertificate] | None = None
) -> list[VerifiedEmploymentSkill]:
    certificates = certificates if certificates is not None else _valid_certificates(db, trainee_id)
    valid_ids = {certificate.id for certificate in certificates}
    if not valid_ids:
        return []
    return list(
        db.scalars(
            select(VerifiedEmploymentSkill)
            .where(
                VerifiedEmploymentSkill.trainee_id == trainee_id,
                VerifiedEmploymentSkill.certificate_id.in_(valid_ids),
            )
            .options(joinedload(VerifiedEmploymentSkill.certificate))
            .order_by(VerifiedEmploymentSkill.name)
        )
    )


def _career_interests(profile: TraineeProfile | None) -> list[str]:
    if profile is None or not profile.career_interests:
        return []
    return [term.strip() for term in profile.career_interests.split(",") if term.strip()]


def _employment_profile(db: Session, trainee_id: UUID) -> TraineeEmploymentProfile:
    profile = db.scalar(
        select(TraineeEmploymentProfile).where(TraineeEmploymentProfile.trainee_id == trainee_id)
    )
    if profile is None:
        profile = TraineeEmploymentProfile(trainee_id=trainee_id)
        db.add(profile)
        db.flush()
    return profile


def employment_profile_public(db: Session, user: User) -> EmploymentProfilePublic:
    employment = _employment_profile(db, user.id)
    trainee = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == user.id))
    certificates = _valid_certificates(db, user.id)
    skills = _valid_skills(db, user.id, certificates)
    return EmploymentProfilePublic(
        trainee_id=user.id,
        full_name=display_name(user),
        headline=employment.headline,
        professional_summary=employment.professional_summary,
        preferred_roles=employment.preferred_roles,
        preferred_locations=employment.preferred_locations,
        open_to_work=employment.open_to_work,
        location=(trainee.preferred_location or trainee.city) if trainee else None,
        career_interests=_career_interests(trainee),
        placement_visibility_consent=(trainee.placement_visibility_consent if trainee else False),
        data_sharing_consent=trainee.data_sharing_consent if trainee else False,
        verified_skills=[
            VerifiedSkillPublic(
                name=skill.name,
                certificate_id=skill.certificate_id,
                certificate_number=skill.certificate.certificate_number,
            )
            for skill in skills
        ],
        resume_filename=employment.resume_filename,
        resume_size_bytes=employment.resume_size_bytes,
        resume_uploaded_at=employment.resume_uploaded_at,
    )


def update_employment_profile(
    db: Session,
    request: Request,
    user: User,
    payload: EmploymentProfileUpdate,
) -> EmploymentProfilePublic:
    profile = _employment_profile(db, user.id)
    values = payload.model_dump()
    values["preferred_roles"] = _clean_terms(values["preferred_roles"])
    values["preferred_locations"] = _clean_terms(values["preferred_locations"])
    for field, value in values.items():
        setattr(profile, field, value)
    add_audit(
        db,
        request,
        "employment.trainee_profile_updated",
        user,
        {"open_to_work": profile.open_to_work},
    )
    db.commit()
    return employment_profile_public(db, user)


async def upload_resume(
    db: Session, request: Request, user: User, upload: UploadFile
) -> EmploymentProfilePublic:
    content, content_type, filename = await read_validated_upload(
        upload,
        allowed_types=RESUME_TYPES,
        maximum_bytes=MAX_RESUME_BYTES,
        kind="resume",
    )
    profile = _employment_profile(db, user.id)
    profile.resume_filename = filename
    profile.resume_content_type = content_type
    profile.resume_size_bytes = len(content)
    profile.resume_content = content
    profile.resume_uploaded_at = utc_now()
    add_audit(
        db,
        request,
        "employment.resume_uploaded",
        user,
        {"filename": profile.resume_filename, "size_bytes": len(content)},
    )
    db.commit()
    return employment_profile_public(db, user)


def _load_job(db: Session, job_id: UUID) -> JobPosting:
    job = db.scalar(select(JobPosting).where(JobPosting.id == job_id).options(*job_options()))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _owned_job(db: Session, user: User, job_id: UUID) -> JobPosting:
    profile = load_employer_profile(db, user, require_verified=True)
    job = _load_job(db, job_id)
    if job.employer_profile_id != profile.id:
        raise HTTPException(status_code=403, detail="You can manage only your company's jobs")
    return job


def _programme_requirements(
    db: Session, programme_ids: list[UUID]
) -> list[JobProgrammeRequirement]:
    unique_ids = list(dict.fromkeys(programme_ids))
    if not unique_ids:
        return []
    programmes = list(db.scalars(select(Programme).where(Programme.id.in_(unique_ids))))
    if len(programmes) != len(unique_ids):
        raise HTTPException(status_code=422, detail="One or more required programmes do not exist")
    return [JobProgrammeRequirement(programme_id=programme.id) for programme in programmes]


def create_job(db: Session, request: Request, user: User, payload: JobCreate) -> JobPublic:
    employer = load_employer_profile(db, user, require_verified=True)
    values = payload.model_dump(exclude={"required_programme_ids"})
    job = JobPosting(
        employer_profile_id=employer.id,
        created_by_id=user.id,
        updated_by_id=user.id,
        **values,
    )
    job.programme_requirements = _programme_requirements(db, payload.required_programme_ids)
    db.add(job)
    db.flush()
    add_audit(db, request, "employment.job_created", user, {"job_id": str(job.id)})
    db.commit()
    return job_public(db, _load_job(db, job.id))


def update_job(
    db: Session,
    request: Request,
    user: User,
    job_id: UUID,
    payload: JobUpdate,
) -> JobPublic:
    job = _owned_job(db, user, job_id)
    if job.status == JobStatus.CLOSED:
        raise HTTPException(status_code=409, detail="Closed jobs cannot be edited")
    for field, value in payload.model_dump(exclude={"required_programme_ids"}).items():
        setattr(job, field, value)
    job.programme_requirements = _programme_requirements(db, payload.required_programme_ids)
    job.updated_by_id = user.id
    add_audit(db, request, "employment.job_updated", user, {"job_id": str(job.id)})
    db.commit()
    return job_public(db, _load_job(db, job.id))


def publish_job(db: Session, request: Request, user: User, job_id: UUID) -> JobPublic:
    job = _owned_job(db, user, job_id)
    if job.status == JobStatus.CLOSED:
        raise HTTPException(status_code=409, detail="Closed jobs cannot be published")
    if job.application_deadline and as_utc(job.application_deadline) <= utc_now():
        raise HTTPException(status_code=422, detail="Application deadline must be in the future")
    job.status = JobStatus.PUBLISHED
    job.published_at = job.published_at or utc_now()
    job.updated_by_id = user.id
    add_audit(db, request, "employment.job_published", user, {"job_id": str(job.id)})
    db.commit()
    return job_public(db, _load_job(db, job.id))


def close_job(db: Session, request: Request, user: User, job_id: UUID) -> JobPublic:
    job = _owned_job(db, user, job_id)
    if job.status != JobStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Only published jobs can be closed")
    job.status = JobStatus.CLOSED
    job.closed_at = utc_now()
    job.updated_by_id = user.id
    add_audit(db, request, "employment.job_closed", user, {"job_id": str(job.id)})
    db.commit()
    return job_public(db, _load_job(db, job.id))


def _terms(values: list[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value.strip()}


def _clean_terms(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def match_job(
    job: JobPosting,
    employment: TraineeEmploymentProfile,
    trainee: TraineeProfile | None,
    skills: list[VerifiedEmploymentSkill],
    certificates: list[DigitalCertificate],
) -> MatchBreakdown:
    candidate_skills = _terms([skill.name for skill in skills])
    requested_skills = _terms(job.required_skills)
    matched_skills = requested_skills & candidate_skills
    skill_score = (
        round(40 * len(matched_skills) / len(requested_skills)) if requested_skills else 40
    )

    required_programmes = {item.programme_id for item in job.programme_requirements}
    certified_programmes = {certificate.enrollment.programme_id for certificate in certificates}
    matched_programmes = required_programmes & certified_programmes
    course_score = (
        round(25 * len(matched_programmes) / len(required_programmes))
        if required_programmes
        else 25
    )

    preferred_locations = _terms(
        employment.preferred_locations
        + ([trainee.preferred_location] if trainee and trainee.preferred_location else [])
    )
    location_match = (
        job.workplace_mode.value == "remote"
        or not preferred_locations
        or any(location in job.location.casefold() for location in preferred_locations)
    )
    location_score = 20 if location_match else 0

    interest_terms = _terms(employment.preferred_roles + _career_interests(trainee))
    job_text = f"{job.title} {job.description}".casefold()
    matched_interests = [interest for interest in interest_terms if interest in job_text]
    interest_score = 15 if not interest_terms or matched_interests else 0

    reasons: list[str] = []
    gaps: list[str] = []
    if requested_skills:
        reasons.append(
            f"{len(matched_skills)} of {len(requested_skills)} required verified skills match"
        )
        missing = sorted(requested_skills - matched_skills)
        if missing:
            gaps.append(f"Missing verified skills: {', '.join(missing)}")
    else:
        reasons.append("No mandatory skill filter")
    if required_programmes:
        reasons.append(
            f"{len(matched_programmes)} of {len(required_programmes)} "
            "required certified courses match"
        )
        if required_programmes - matched_programmes:
            gaps.append("One or more required course certificates are missing")
    else:
        reasons.append("No specific course certificate required")
    if location_match:
        reasons.append("Work location matches a preference or the role is remote")
    else:
        gaps.append("Location is outside current preferences")
    if matched_interests:
        reasons.append(f"Career interest aligns: {matched_interests[0]}")
    elif not interest_terms:
        reasons.append("No career-interest restriction")
    else:
        gaps.append("Role title does not match current career interests")
    return MatchBreakdown(
        score=skill_score + course_score + location_score + interest_score,
        skill_score=skill_score,
        course_score=course_score,
        location_score=location_score,
        interest_score=interest_score,
        reasons=reasons,
        gaps=gaps,
    )


def _certificate_summary(certificate: DigitalCertificate) -> CertificateSummary:
    programme = certificate.enrollment.programme
    return CertificateSummary(
        id=certificate.id,
        certificate_number=certificate.certificate_number,
        title=certificate.title,
        programme_title=programme.title,
        programme_code=programme.code,
        issued_at=certificate.issued_at,
        expires_at=certificate.expires_at,
        verification_url=verification_url(certificate.verification_token),
    )


def job_public(
    db: Session,
    job: JobPosting,
    *,
    trainee: User | None = None,
    include_match: bool = False,
) -> JobPublic:
    saved = False
    application_status = None
    match = None
    if trainee is not None:
        saved = (
            db.scalar(
                select(SavedJob.id).where(
                    SavedJob.job_id == job.id, SavedJob.trainee_id == trainee.id
                )
            )
            is not None
        )
        application_status = db.scalar(
            select(JobApplication.status).where(
                JobApplication.job_id == job.id,
                JobApplication.trainee_id == trainee.id,
            )
        )
        if include_match:
            employment = _employment_profile(db, trainee.id)
            trainee_profile = db.scalar(
                select(TraineeProfile).where(TraineeProfile.user_id == trainee.id)
            )
            certificates = _valid_certificates(db, trainee.id)
            skills = _valid_skills(db, trainee.id, certificates)
            match = match_job(job, employment, trainee_profile, skills, certificates)
    return JobPublic(
        id=job.id,
        employer_profile_id=job.employer_profile_id,
        company_name=job.employer.institution.name,
        title=job.title,
        description=job.description,
        location=job.location,
        employment_type=job.employment_type,
        workplace_mode=job.workplace_mode,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        minimum_experience_years=job.minimum_experience_years,
        vacancies=job.vacancies,
        salary_minimum=job.salary_minimum,
        salary_maximum=job.salary_maximum,
        application_deadline=job.application_deadline,
        status=job.status,
        published_at=job.published_at,
        closed_at=job.closed_at,
        required_programmes=[
            ProgrammeRequirementPublic(
                id=item.programme.id,
                code=item.programme.code,
                title=item.programme.title,
            )
            for item in job.programme_requirements
        ],
        saved=saved,
        application_status=application_status,
        match=match,
    )


def list_jobs(
    db: Session,
    trainee: User,
    *,
    query: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    programme_id: UUID | None = None,
) -> list[JobPublic]:
    now = utc_now()
    statement = (
        select(JobPosting)
        .join(EmployerProfile)
        .where(
            JobPosting.status == JobStatus.PUBLISHED,
            EmployerProfile.verification_status == EmployerVerificationStatus.VERIFIED,
            or_(JobPosting.application_deadline.is_(None), JobPosting.application_deadline > now),
        )
        .options(*job_options())
        .order_by(JobPosting.published_at.desc())
    )
    if query:
        term = f"%{query.strip()}%"
        statement = statement.where(
            or_(JobPosting.title.ilike(term), JobPosting.description.ilike(term))
        )
    if location:
        statement = statement.where(JobPosting.location.ilike(f"%{location.strip()}%"))
    jobs = list(db.scalars(statement).unique())
    if skill:
        needle = skill.strip().casefold()
        jobs = [job for job in jobs if needle in _terms(job.required_skills + job.preferred_skills)]
    if programme_id:
        jobs = [
            job
            for job in jobs
            if programme_id in {item.programme_id for item in job.programme_requirements}
        ]
    return [job_public(db, job, trainee=trainee, include_match=True) for job in jobs]


def recommendations(db: Session, trainee: User) -> list[JobPublic]:
    jobs = list_jobs(db, trainee)
    return sorted(jobs, key=lambda job: job.match.score if job.match else 0, reverse=True)


def save_job(db: Session, user: User, job_id: UUID) -> JobPublic:
    job = _load_job(db, job_id)
    if job.status != JobStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Only published jobs can be saved")
    saved = db.scalar(
        select(SavedJob).where(SavedJob.job_id == job.id, SavedJob.trainee_id == user.id)
    )
    if saved is None:
        db.add(SavedJob(job_id=job.id, trainee_id=user.id))
        db.commit()
    return job_public(db, job, trainee=user, include_match=True)


def unsave_job(db: Session, user: User, job_id: UUID) -> None:
    saved = db.scalar(
        select(SavedJob).where(SavedJob.job_id == job_id, SavedJob.trainee_id == user.id)
    )
    if saved is not None:
        db.delete(saved)
        db.commit()


def _load_application(db: Session, application_id: UUID) -> JobApplication:
    application = db.scalar(
        select(JobApplication)
        .where(JobApplication.id == application_id)
        .options(
            joinedload(JobApplication.trainee).joinedload(User.profile),
            joinedload(JobApplication.job)
            .joinedload(JobPosting.employer)
            .joinedload(EmployerProfile.institution),
            selectinload(JobApplication.certificates)
            .joinedload(JobApplicationCertificate.certificate)
            .joinedload(DigitalCertificate.enrollment)
            .joinedload(ProgrammeEnrollment.programme),
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Job application not found")
    return application


def _contact_allowed(db: Session, employer_id: UUID, trainee_id: UUID) -> tuple[bool, str | None]:
    trainee = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == trainee_id))
    if trainee is None or not trainee.data_sharing_consent:
        return False, "Contact details remain private until the trainee enables data sharing"
    application = db.scalar(
        select(JobApplication.id)
        .join(JobPosting)
        .where(
            JobPosting.employer_profile_id == employer_id,
            JobApplication.trainee_id == trainee_id,
            JobApplication.status != JobApplicationStatus.WITHDRAWN,
        )
    )
    if application is None:
        return False, "Contact details unlock after the trainee applies"
    return True, None


def application_public(
    db: Session,
    application: JobApplication,
    *,
    viewer_employer_id: UUID | None = None,
) -> JobApplicationPublic:
    contact = None
    if viewer_employer_id is None:
        contact = CandidateContact(
            email=application.trainee.email,
            phone=application.trainee.profile.phone if application.trainee.profile else None,
        )
    else:
        allowed, _ = _contact_allowed(db, viewer_employer_id, application.trainee_id)
        if allowed:
            contact = CandidateContact(
                email=application.trainee.email,
                phone=(application.trainee.profile.phone if application.trainee.profile else None),
            )
    return JobApplicationPublic(
        id=application.id,
        job_id=application.job_id,
        job_title=application.job.title,
        company_name=application.job.employer.institution.name,
        trainee_id=application.trainee_id,
        trainee_name=display_name(application.trainee),
        status=application.status,
        cover_note=application.cover_note,
        applied_at=application.applied_at,
        status_updated_at=application.status_updated_at,
        interview_at=application.interview_at,
        interview_mode=application.interview_mode,
        interview_details=application.interview_details,
        employer_notes=application.employer_notes,
        certificates=[_certificate_summary(item.certificate) for item in application.certificates],
        contact=contact,
    )


def apply_for_job(
    db: Session,
    request: Request,
    user: User,
    job_id: UUID,
    payload: JobApplicationCreate,
) -> JobApplicationPublic:
    job = _load_job(db, job_id)
    if job.status != JobStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="This job is not accepting applications")
    if job.application_deadline and as_utc(job.application_deadline) <= utc_now():
        raise HTTPException(status_code=409, detail="The application deadline has passed")
    duplicate = db.scalar(
        select(JobApplication.id).where(
            JobApplication.job_id == job.id, JobApplication.trainee_id == user.id
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="You have already applied for this job")
    certificates = _valid_certificates(db, user.id)
    if not certificates:
        raise HTTPException(status_code=422, detail="A valid NCCT certificate is required")
    certified_programmes = {certificate.enrollment.programme_id for certificate in certificates}
    required_programmes = {item.programme_id for item in job.programme_requirements}
    if not required_programmes.issubset(certified_programmes):
        raise HTTPException(
            status_code=422,
            detail="You do not hold every course certificate required for this job",
        )
    application = JobApplication(
        job_id=job.id,
        trainee_id=user.id,
        cover_note=payload.cover_note,
        certificates=[
            JobApplicationCertificate(certificate_id=certificate.id) for certificate in certificates
        ],
    )
    db.add(application)
    db.flush()
    add_audit(
        db,
        request,
        "employment.job_applied",
        user,
        {"job_id": str(job.id), "application_id": str(application.id)},
    )
    db.commit()
    return application_public(db, _load_application(db, application.id))


def trainee_applications(db: Session, user: User) -> list[JobApplicationPublic]:
    ids = list(
        db.scalars(
            select(JobApplication.id)
            .where(JobApplication.trainee_id == user.id)
            .order_by(JobApplication.applied_at.desc())
        )
    )
    return [application_public(db, _load_application(db, item)) for item in ids]


def withdraw_application(
    db: Session, request: Request, user: User, application_id: UUID
) -> JobApplicationPublic:
    application = _load_application(db, application_id)
    if application.trainee_id != user.id:
        raise HTTPException(status_code=403, detail="You can withdraw only your own application")
    if application.status in {
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
        JobApplicationStatus.WITHDRAWN,
    }:
        raise HTTPException(status_code=409, detail="This application can no longer be withdrawn")
    application.status = JobApplicationStatus.WITHDRAWN
    application.withdrawn_at = utc_now()
    application.status_updated_at = utc_now()
    add_audit(
        db,
        request,
        "employment.application_withdrawn",
        user,
        {"application_id": str(application.id)},
    )
    db.commit()
    return application_public(db, _load_application(db, application.id))


ALLOWED_TRANSITIONS: dict[JobApplicationStatus, set[JobApplicationStatus]] = {
    JobApplicationStatus.APPLIED: {
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.SHORTLISTED: {
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.OFFERED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.INTERVIEW_SCHEDULED: {
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.INTERVIEW_COMPLETED: {
        JobApplicationStatus.OFFERED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.OFFERED: {
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
}


def update_application_status(
    db: Session,
    request: Request,
    user: User,
    application_id: UUID,
    payload: JobApplicationStatusUpdate,
) -> JobApplicationPublic:
    employer = load_employer_profile(db, user, require_verified=True)
    application = _load_application(db, application_id)
    if application.job.employer_profile_id != employer.id:
        raise HTTPException(status_code=403, detail="You can manage only your company's applicants")
    if payload.status not in ALLOWED_TRANSITIONS.get(application.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change {application.status.value} to {payload.status.value}",
        )
    application.status = payload.status
    application.reviewed_by_id = user.id
    application.status_updated_at = utc_now()
    application.employer_notes = payload.employer_notes
    if payload.status == JobApplicationStatus.INTERVIEW_SCHEDULED:
        application.interview_at = payload.interview_at
        application.interview_mode = payload.interview_mode
        application.interview_details = payload.interview_details
    add_audit(
        db,
        request,
        "employment.application_status_updated",
        user,
        {"application_id": str(application.id), "status": payload.status.value},
    )
    db.commit()
    return application_public(
        db, _load_application(db, application.id), viewer_employer_id=employer.id
    )


def candidate_public(
    db: Session,
    employer: EmployerProfile,
    user: User,
    job: JobPosting | None,
) -> CandidatePublic:
    trainee = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == user.id))
    employment = _employment_profile(db, user.id)
    certificates = _valid_certificates(db, user.id)
    skills = _valid_skills(db, user.id, certificates)
    allowed, locked_reason = _contact_allowed(db, employer.id, user.id)
    shortlisted = False
    if job is not None:
        shortlisted = (
            db.scalar(
                select(CandidateShortlist.id).where(
                    CandidateShortlist.job_id == job.id,
                    CandidateShortlist.trainee_id == user.id,
                )
            )
            is not None
        )
    return CandidatePublic(
        trainee_id=user.id,
        full_name=display_name(user),
        headline=employment.headline,
        professional_summary=employment.professional_summary,
        location=(trainee.preferred_location or trainee.city) if trainee else None,
        verified_skills=sorted({skill.name for skill in skills}),
        career_interests=_career_interests(trainee),
        certificates=[_certificate_summary(certificate) for certificate in certificates],
        contact=(
            CandidateContact(
                email=user.email,
                phone=user.profile.phone if user.profile else None,
            )
            if allowed
            else None
        ),
        contact_locked_reason=locked_reason,
        resume_available=employment.resume_content is not None,
        resume_download_allowed=allowed and employment.resume_content is not None,
        shortlisted=shortlisted,
        match=(match_job(job, employment, trainee, skills, certificates) if job else None),
    )


def search_candidates(
    db: Session,
    user: User,
    *,
    job_id: UUID | None = None,
    skill: str | None = None,
    course_id: UUID | None = None,
    certificate_number: str | None = None,
    location: str | None = None,
) -> list[CandidatePublic]:
    employer = load_employer_profile(db, user, require_verified=True)
    job = _owned_job(db, user, job_id) if job_id else None
    candidates = list(
        db.scalars(
            select(User)
            .join(TraineeProfile, TraineeProfile.user_id == User.id)
            .join(
                TraineeEmploymentProfile,
                TraineeEmploymentProfile.trainee_id == User.id,
            )
            .where(
                TraineeProfile.placement_visibility_consent.is_(True),
                TraineeEmploymentProfile.open_to_work.is_(True),
                User.status == AccountStatus.ACTIVE,
            )
            .options(joinedload(User.profile))
            .order_by(User.created_at.desc())
        ).unique()
    )
    results: list[CandidatePublic] = []
    for candidate in candidates:
        item = candidate_public(db, employer, candidate, job)
        if not item.certificates:
            continue
        if skill and skill.casefold() not in _terms(item.verified_skills):
            continue
        if location and (not item.location or location.casefold() not in item.location.casefold()):
            continue
        if course_id and all(
            certificate.id != course_id
            and _certificate_programme_id(db, certificate.id) != course_id
            for certificate in item.certificates
        ):
            continue
        if certificate_number and all(
            certificate_number.casefold() not in certificate.certificate_number.casefold()
            for certificate in item.certificates
        ):
            continue
        results.append(item)
    return sorted(
        results,
        key=lambda item: item.match.score if item.match else 0,
        reverse=True,
    )


def _certificate_programme_id(db: Session, certificate_id: UUID) -> UUID | None:
    return db.scalar(
        select(ProgrammeEnrollment.programme_id)
        .join(DigitalCertificate, DigitalCertificate.enrollment_id == ProgrammeEnrollment.id)
        .where(DigitalCertificate.id == certificate_id)
    )


def shortlist_candidate(
    db: Session,
    request: Request,
    user: User,
    job_id: UUID,
    payload: CandidateShortlistCreate,
) -> CandidatePublic:
    employer = load_employer_profile(db, user, require_verified=True)
    job = _owned_job(db, user, job_id)
    visible_ids = {candidate.trainee_id for candidate in search_candidates(db, user, job_id=job.id)}
    if payload.trainee_id not in visible_ids:
        raise HTTPException(status_code=404, detail="Eligible candidate not found")
    shortlist = db.scalar(
        select(CandidateShortlist).where(
            CandidateShortlist.job_id == job.id,
            CandidateShortlist.trainee_id == payload.trainee_id,
        )
    )
    if shortlist is None:
        shortlist = CandidateShortlist(
            job_id=job.id,
            trainee_id=payload.trainee_id,
            shortlisted_by_id=user.id,
            notes=payload.notes,
        )
        db.add(shortlist)
    else:
        shortlist.notes = payload.notes
    add_audit(
        db,
        request,
        "employment.candidate_shortlisted",
        user,
        {"job_id": str(job.id), "trainee_id": str(payload.trainee_id)},
    )
    db.commit()
    candidate = db.scalar(
        select(User).where(User.id == payload.trainee_id).options(joinedload(User.profile))
    )
    assert candidate is not None
    return candidate_public(db, employer, candidate, _load_job(db, job.id))


def employer_resume(db: Session, user: User, trainee_id: UUID) -> TraineeEmploymentProfile:
    employer = load_employer_profile(db, user, require_verified=True)
    allowed, reason = _contact_allowed(db, employer.id, trainee_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)
    profile = _employment_profile(db, trainee_id)
    if profile.resume_content is None:
        raise HTTPException(status_code=404, detail="Resume not uploaded")
    return profile


def employer_workspace(db: Session, user: User) -> EmployerWorkspacePublic:
    employer = load_employer_profile(db, user)
    jobs = list(
        db.scalars(
            select(JobPosting)
            .where(JobPosting.employer_profile_id == employer.id)
            .options(*job_options())
            .order_by(JobPosting.created_at.desc())
        ).unique()
    )
    application_ids = list(
        db.scalars(
            select(JobApplication.id)
            .join(JobPosting)
            .where(JobPosting.employer_profile_id == employer.id)
            .order_by(JobApplication.applied_at.desc())
        )
    )
    shortlist_count = len(
        list(
            db.scalars(
                select(CandidateShortlist.id)
                .join(JobPosting)
                .where(JobPosting.employer_profile_id == employer.id)
            )
        )
    )
    return EmployerWorkspacePublic(
        profile=employer_public(employer),
        jobs=[job_public(db, job) for job in jobs],
        applications=[
            application_public(db, _load_application(db, item), viewer_employer_id=employer.id)
            for item in application_ids
        ],
        shortlisted_count=shortlist_count,
    )


def trainee_workspace(db: Session, user: User) -> TraineeEmploymentWorkspacePublic:
    saved_job_ids = list(
        db.scalars(
            select(SavedJob.job_id)
            .where(SavedJob.trainee_id == user.id)
            .order_by(SavedJob.saved_at.desc())
        )
    )
    return TraineeEmploymentWorkspacePublic(
        profile=employment_profile_public(db, user),
        recommendations=recommendations(db, user),
        saved_jobs=[
            job_public(db, _load_job(db, job_id), trainee=user, include_match=True)
            for job_id in saved_job_ids
        ],
        applications=trainee_applications(db, user),
    )


def trainee_resume(db: Session, user: User) -> TraineeEmploymentProfile:
    profile = _employment_profile(db, user.id)
    if profile.resume_content is None:
        raise HTTPException(status_code=404, detail="Resume not uploaded")
    return profile
