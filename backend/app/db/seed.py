from datetime import UTC, date, datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.career_seed import seed_career_faqs
from app.db.session import SessionLocal
from app.models import (
    AccountStatus,
    AssessmentAttempt,
    AssessmentAttemptStatus,
    AssessmentRecord,
    AssessmentResult,
    AssessmentType,
    Assignment,
    AssignmentSubmission,
    AssignmentSubmissionStatus,
    AttendanceRecord,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceStatus,
    AuditLog,
    BatchTrainerAssignment,
    BedAllocation,
    BedAllocationStatus,
    CertificatePolicy,
    CertificateRecord,
    Classroom,
    ConsentRecord,
    CooperativeMembership,
    Course,
    CourseLanguage,
    CourseModule,
    CourseSection,
    CourseStatus,
    DigitalCertificate,
    DocumentValidationStatus,
    EducationRecord,
    EligibilityType,
    EmployerProfile,
    EmployerVerificationStatus,
    EmploymentRecord,
    EmploymentType,
    EnrollmentStatus,
    HostelBed,
    HostelBuilding,
    HostelRoom,
    Institution,
    InstitutionType,
    JobPosting,
    JobProgrammeRequirement,
    JobStatus,
    LearnerAssessment,
    LearningProgressStatus,
    Lesson,
    LessonContent,
    LessonProgress,
    LessonType,
    MaterialDistribution,
    MealPreference,
    OperationsIssue,
    OperationsIssuePriority,
    OperationsIssueStatus,
    OperationsIssueType,
    ParticipantLogistics,
    ProfileDocumentType,
    Programme,
    ProgrammeBatch,
    ProgrammeEnrollment,
    ProgrammeMode,
    ProgrammeStatus,
    Question,
    QuestionBank,
    Role,
    RoleCode,
    ScheduleStatus,
    TimetableSession,
    TraineeDocument,
    TraineeEmploymentProfile,
    TraineeProfile,
    TrainingMaterial,
    TrainingVenue,
    TransportMode,
    User,
    UserProfile,
    VerifiedEmploymentSkill,
    WorkplaceMode,
)
from app.services.certificates import generate_certificate_pdf

ROLE_NAMES = {
    RoleCode.NCCT_SUPER_ADMIN: "NCCT super administrator",
    RoleCode.INSTITUTE_ADMIN: "Institute administrator",
    RoleCode.TRAINER: "Trainer",
    RoleCode.TRAINEE: "Trainee",
    RoleCode.NOMINATING_INSTITUTION: "Nominating institution",
    RoleCode.EMPLOYER_RECRUITER: "Employer / recruiter",
}

INSTITUTIONS = (
    ("NCCT", "NCCT Demonstration Headquarters", InstitutionType.NCCT, None, "Delhi", None),
    (
        "VAMNICOM",
        "VAMNICOM Demonstration Institute",
        InstitutionType.VAMNICOM,
        "NCCT",
        "Maharashtra",
        "Pune",
    ),
    (
        "RICM-BLR-DEMO",
        "RICM Bengaluru Demonstration Centre",
        InstitutionType.RICM,
        "NCCT",
        "Karnataka",
        "Bengaluru Urban",
    ),
    (
        "ICM-PUNE-DEMO",
        "ICM Pune Demonstration Centre",
        InstitutionType.ICM,
        "VAMNICOM",
        "Maharashtra",
        "Pune",
    ),
    (
        "PACS-SATARA-DEMO",
        "Satara PACS Demonstration Society",
        InstitutionType.PACS,
        "VAMNICOM",
        "Maharashtra",
        "Satara",
    ),
    (
        "SHG-PUNE-DEMO",
        "Sahyog SHG Demonstration Federation",
        InstitutionType.SHG,
        "ICM-PUNE-DEMO",
        "Maharashtra",
        "Pune",
    ),
    (
        "DAIRY-GUJ-DEMO",
        "Gujarat Dairy Demonstration Cooperative",
        InstitutionType.DAIRY_COOPERATIVE,
        "RICM-BLR-DEMO",
        "Gujarat",
        "Anand",
    ),
    (
        "COOP-OTHER-DEMO",
        "Multi-purpose Demonstration Cooperative",
        InstitutionType.OTHER_COOPERATIVE,
        "ICM-PUNE-DEMO",
        "Maharashtra",
        "Nashik",
    ),
    (
        "NOM-DEMO",
        "Nominating Demonstration Cooperative",
        InstitutionType.NOMINATING_INSTITUTION,
        "NCCT",
        "Madhya Pradesh",
        "Bhopal",
    ),
    (
        "EMP-DEMO",
        "Cooperative Employer Demonstration Office",
        InstitutionType.EMPLOYER,
        "NCCT",
        "Delhi",
        "New Delhi",
    ),
)

DEMO_USERS = (
    (
        "superadmin@demo.ncct.gov.in",
        "Demonstration NCCT Administrator",
        RoleCode.NCCT_SUPER_ADMIN,
        "NCCT",
    ),
    (
        "institute.admin@demo.ncct.gov.in",
        "Demonstration Institute Administrator",
        RoleCode.INSTITUTE_ADMIN,
        "VAMNICOM",
    ),
    (
        "trainer@demo.ncct.gov.in",
        "Demonstration Trainer",
        RoleCode.TRAINER,
        "VAMNICOM",
    ),
    (
        "trainee@demo.ncct.gov.in",
        "Asha Patil - Demonstration Trainee",
        RoleCode.TRAINEE,
        "PACS-SATARA-DEMO",
    ),
    (
        "nominator@demo.ncct.gov.in",
        "Demonstration Nominating Officer",
        RoleCode.NOMINATING_INSTITUTION,
        "NOM-DEMO",
    ),
    (
        "recruiter@demo.ncct.gov.in",
        "Demonstration Cooperative Recruiter",
        RoleCode.EMPLOYER_RECRUITER,
        "EMP-DEMO",
    ),
)


def seed_demonstration_course(
    db: Session,
    users: dict[RoleCode, User],
    programme: Programme,
    enrollment: ProgrammeEnrollment,
    seeded_at: datetime,
) -> None:
    existing = db.scalar(select(Course).where(Course.programme_id == programme.id))
    if existing is not None:
        return

    pdf_content = (
        b"%PDF-1.4\n% Fictional NCCT demonstration learning document.\n"
        b"1 0 obj<</Type/Catalog>>endobj\n%%EOF"
    )
    lesson_text = Lesson(
        title="Welcome to cooperative governance",
        lesson_type=LessonType.TEXT,
        position=1,
        is_required=True,
        contents=[
            LessonContent(
                language_code="en",
                title="Welcome to cooperative governance",
                text_content=(
                    "This demonstration lesson introduces member ownership, democratic "
                    "decision-making and accountable cooperative leadership."
                ),
            ),
            LessonContent(
                language_code="hi",
                title="सहकारी शासन में आपका स्वागत है",
                text_content=(
                    "यह प्रदर्शन पाठ सदस्य स्वामित्व, लोकतांत्रिक निर्णय और जवाबदेह "
                    "सहकारी नेतृत्व का परिचय देता है।"
                ),
            ),
            LessonContent(
                language_code="te",
                title="సహకార పాలనకు స్వాగతం",
                text_content=(
                    "ఈ ప్రదర్శన పాఠం సభ్యుల యాజమాన్యం, ప్రజాస్వామ్య నిర్ణయాలు మరియు "
                    "జవాబుదారీ సహకార నాయకత్వాన్ని పరిచయం చేస్తుంది."
                ),
            ),
        ],
    )
    video_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
    lesson_video = Lesson(
        title="Member participation in practice",
        lesson_type=LessonType.VIDEO,
        position=2,
        duration_seconds=30,
        is_required=True,
        contents=[
            LessonContent(
                language_code=code,
                title=title,
                external_url=video_url,
            )
            for code, title in (
                ("en", "Member participation in practice"),
                ("hi", "व्यवहार में सदस्य भागीदारी"),
                ("te", "ఆచరణలో సభ్యుల భాగస్వామ్యం"),
            )
        ],
    )
    orientation_module = CourseModule(
        title="Orientation",
        description="Demonstration lessons on cooperative values and member voice.",
        position=1,
        lessons=[lesson_text, lesson_video],
    )
    foundation_section = CourseSection(
        title="Governance foundations",
        position=1,
        modules=[orientation_module],
    )

    lesson_pdf = Lesson(
        title="Board meeting checklist",
        lesson_type=LessonType.PDF,
        position=1,
        is_required=True,
        contents=[
            LessonContent(
                language_code=code,
                title=title,
                filename=f"board-checklist-{code}-demo.pdf",
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                content=pdf_content,
            )
            for code, title in (
                ("en", "Board meeting checklist"),
                ("hi", "बोर्ड बैठक जांच सूची"),
                ("te", "బోర్డు సమావేశ తనిఖీ జాబితా"),
            )
        ],
    )
    audio_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-audio/t-rex-roar.mp3"
    lesson_audio = Lesson(
        title="Listening: clear member communication",
        lesson_type=LessonType.AUDIO,
        position=2,
        duration_seconds=5,
        is_required=False,
        contents=[
            LessonContent(
                language_code=code,
                title=title,
                external_url=audio_url,
            )
            for code, title in (
                ("en", "Listening: clear member communication"),
                ("hi", "सुनना: सदस्यों के साथ स्पष्ट संवाद"),
                ("te", "వినికిడి: సభ్యులతో స్పష్టమైన సంభాషణ"),
            )
        ],
    )
    lesson_external = Lesson(
        title="Explore the Ministry of Cooperation",
        lesson_type=LessonType.EXTERNAL_RESOURCE,
        position=3,
        is_required=False,
        contents=[
            LessonContent(
                language_code=code,
                title=title,
                external_url="https://cooperation.gov.in/",
            )
            for code, title in (
                ("en", "Explore the Ministry of Cooperation"),
                ("hi", "सहकारिता मंत्रालय देखें"),
                ("te", "సహకార మంత్రిత్వ శాఖను చూడండి"),
            )
        ],
    )
    practice_module = CourseModule(
        title="Board practice",
        description="Apply transparent governance and communication in practical tasks.",
        position=1,
        lessons=[lesson_pdf, lesson_audio, lesson_external],
    )
    practice_section = CourseSection(
        title="Practice and reflection",
        position=2,
        modules=[practice_module],
    )

    bank = QuestionBank(
        title="Governance knowledge bank (demonstration)",
        description="Fictional sample questions for pre, practice and post assessments.",
        questions=[
            Question(
                prompt="Who ultimately owns a cooperative?",
                choices=["Its members", "One trainer", "An external supplier"],
                correct_option_index=0,
                explanation="A cooperative is jointly owned by its members.",
                points=1,
                position=1,
            ),
            Question(
                prompt="Which practice supports accountable board decisions?",
                choices=["No written record", "Clear minutes", "Private member exclusion"],
                correct_option_index=1,
                explanation="Clear minutes create an accountable record of decisions.",
                points=1,
                position=2,
            ),
            Question(
                prompt="How should important information be shared with members?",
                choices=["Clearly and accessibly", "Only after one year", "Never in writing"],
                correct_option_index=0,
                explanation="Clear, accessible information supports meaningful participation.",
                points=1,
                position=3,
            ),
        ],
    )
    course = Course(
        programme=programme,
        created_by=users[RoleCode.INSTITUTE_ADMIN],
        title="Cooperative Governance Learning Journey (Demonstration)",
        summary=(
            "A complete demonstration course covering lessons, progress, assignments and "
            "automatically graded assessments."
        ),
        status=CourseStatus.PUBLISHED,
        default_language_code="en",
        languages=[
            CourseLanguage(code="en", name="English"),
            CourseLanguage(code="hi", name="हिन्दी"),
            CourseLanguage(code="te", name="తెలుగు"),
        ],
        sections=[foundation_section, practice_section],
        question_banks=[bank],
    )
    assignment = Assignment(
        course=course,
        module=practice_module,
        title="Board decision reflection (demonstration)",
        instructions=(
            "Upload a PDF explaining how a cooperative board can record and communicate one "
            "important decision. Use fictional information only."
        ),
        max_score=20,
        allowed_content_types=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
        is_published=True,
    )
    assessments = [
        LearnerAssessment(
            course=course,
            question_bank=bank,
            title="Pre-training knowledge check",
            instructions="Answer all questions before beginning the learning journey.",
            assessment_type=AssessmentType.PRE_TRAINING,
            attempt_limit=2,
            passing_score_percent=50,
            is_published=True,
        ),
        LearnerAssessment(
            course=course,
            question_bank=bank,
            title="Module practice quiz",
            instructions="Check your understanding of member-led governance.",
            assessment_type=AssessmentType.QUIZ,
            attempt_limit=3,
            passing_score_percent=60,
            is_published=True,
        ),
        LearnerAssessment(
            course=course,
            question_bank=bank,
            title="Post-training assessment",
            instructions="Complete the final knowledge check after the required lessons.",
            assessment_type=AssessmentType.POST_TRAINING,
            attempt_limit=2,
            passing_score_percent=70,
            is_published=True,
        ),
    ]
    db.add_all([course, assignment, *assessments])
    db.flush()

    db.add_all(
        [
            LessonProgress(
                enrollment_id=enrollment.id,
                lesson_id=lesson_text.id,
                status=LearningProgressStatus.COMPLETED,
                completed_at=seeded_at - timedelta(days=1),
                last_accessed_at=seeded_at - timedelta(days=1),
            ),
            LessonProgress(
                enrollment_id=enrollment.id,
                lesson_id=lesson_video.id,
                status=LearningProgressStatus.IN_PROGRESS,
                last_position_seconds=10,
                viewed_seconds=10,
                last_accessed_at=seeded_at,
            ),
        ]
    )
    submission_content = b"%PDF-1.4\nFictional assignment submission for demonstration only.\n%%EOF"
    db.add(
        AssignmentSubmission(
            assignment_id=assignment.id,
            enrollment_id=enrollment.id,
            submission_number=1,
            status=AssignmentSubmissionStatus.REVIEWED,
            filename="fictional-board-reflection-demo.pdf",
            content_type="application/pdf",
            size_bytes=len(submission_content),
            content=submission_content,
            score=16,
            trainer_feedback=(
                "Clear demonstration response. Add one example of how members receive the "
                "decision record."
            ),
            reviewed_by_id=users[RoleCode.TRAINER].id,
            reviewed_at=seeded_at,
        )
    )
    pre_assessment = assessments[0]
    questions = sorted(bank.questions, key=lambda item: item.position)
    db.add(
        AssessmentAttempt(
            assessment_id=pre_assessment.id,
            enrollment_id=enrollment.id,
            attempt_number=1,
            status=AssessmentAttemptStatus.SUBMITTED,
            question_ids=[str(item.id) for item in questions],
            answers={str(questions[0].id): 0, str(questions[1].id): 0, str(questions[2].id): 0},
            grading_details=[
                {
                    "question_id": str(item.id),
                    "selected_option_index": selected,
                    "correct": selected == item.correct_option_index,
                    "points_earned": 1 if selected == item.correct_option_index else 0,
                    "explanation": item.explanation,
                }
                for item, selected in zip(questions, (0, 0, 0), strict=True)
            ],
            points_earned=2,
            points_available=3,
            score_percent=66.67,
            passed=True,
            started_at=seeded_at - timedelta(days=2),
            submitted_at=seeded_at - timedelta(days=2),
            trainer_feedback="A sound demonstration baseline. Review accountable record-keeping.",
            reviewed_by_id=users[RoleCode.TRAINER].id,
            reviewed_at=seeded_at - timedelta(days=1),
        )
    )
    db.add(
        AuditLog(
            user_id=users[RoleCode.NCCT_SUPER_ADMIN].id,
            event_type="learning.demonstration_seeded",
            success=True,
            details={
                "course_id": str(course.id),
                "notice": "Fictional demonstration learning data only",
            },
        )
    )


def seed_demonstration_operations(
    db: Session,
    users: dict[RoleCode, User],
    institution: Institution,
    programme: Programme,
    enrollment: ProgrammeEnrollment,
    seeded_at: datetime,
) -> None:
    admin = users[RoleCode.INSTITUTE_ADMIN]
    trainer = users[RoleCode.TRAINER]
    venue = db.scalar(
        select(TrainingVenue).where(
            TrainingVenue.institution_id == institution.id,
            TrainingVenue.name == "VAMNICOM Demonstration Learning Centre",
        )
    )
    if venue is None:
        venue = TrainingVenue(
            institution_id=institution.id,
            name="VAMNICOM Demonstration Learning Centre",
            address="Fictional Training Road, Pune, Maharashtra",
            capacity=80,
        )
        db.add(venue)
        db.flush()
    classroom = db.scalar(
        select(Classroom).where(
            Classroom.venue_id == venue.id,
            Classroom.code == "DEMO-HALL-A",
        )
    )
    if classroom is None:
        classroom = Classroom(
            institution_id=institution.id,
            venue_id=venue.id,
            name="Demonstration Hall A",
            code="DEMO-HALL-A",
            capacity=40,
            equipment="Projector, audio system and accessible seating (demonstration)",
        )
        db.add(classroom)
        db.flush()

    if enrollment.batch_id and not db.scalar(
        select(TimetableSession.id).where(
            TimetableSession.batch_id == enrollment.batch_id,
            TimetableSession.title == "Cooperative leadership workshop (demonstration)",
        )
    ):
        starts_at = datetime.combine(programme.start_date, datetime.min.time(), UTC).replace(hour=9)
        db.add(
            TimetableSession(
                institution_id=institution.id,
                programme_id=programme.id,
                batch_id=enrollment.batch_id,
                trainer_id=trainer.id,
                venue_id=venue.id,
                classroom_id=classroom.id,
                created_by_id=admin.id,
                title="Cooperative leadership workshop (demonstration)",
                description="Fictional opening workshop for the demonstration cohort.",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=3),
                status=ScheduleStatus.SCHEDULED,
            )
        )

    building = db.scalar(
        select(HostelBuilding).where(
            HostelBuilding.institution_id == institution.id,
            HostelBuilding.name == "Sahyadri Demonstration Hostel",
        )
    )
    if building is None:
        building = HostelBuilding(
            institution_id=institution.id,
            name="Sahyadri Demonstration Hostel",
            address="Fictional Campus Lane, Pune, Maharashtra",
            contact_phone="+91 90000 10001",
        )
        db.add(building)
        db.flush()
    room = db.scalar(
        select(HostelRoom).where(
            HostelRoom.building_id == building.id,
            HostelRoom.room_number == "D-101",
        )
    )
    if room is None:
        room = HostelRoom(
            building_id=building.id,
            room_number="D-101",
            floor="Ground floor",
            capacity=2,
            is_accessible=True,
        )
        db.add(room)
        db.flush()
        db.add_all(
            [
                HostelBed(room_id=room.id, bed_number="A"),
                HostelBed(room_id=room.id, bed_number="B"),
            ]
        )
        db.flush()
    bed = db.scalar(
        select(HostelBed).where(
            HostelBed.room_id == room.id,
            HostelBed.bed_number == "A",
        )
    )
    if bed and not db.scalar(
        select(BedAllocation.id).where(BedAllocation.enrollment_id == enrollment.id)
    ):
        db.add(
            BedAllocation(
                bed_id=bed.id,
                enrollment_id=enrollment.id,
                allocated_by_id=admin.id,
                start_date=programme.start_date - timedelta(days=1),
                end_date=programme.end_date + timedelta(days=1),
                status=BedAllocationStatus.RESERVED,
            )
        )

    logistics = db.scalar(
        select(ParticipantLogistics).where(ParticipantLogistics.enrollment_id == enrollment.id)
    )
    if logistics is None:
        db.add(
            ParticipantLogistics(
                enrollment_id=enrollment.id,
                meal_preference=MealPreference.VEGETARIAN,
                dietary_notes="No peanuts (fictional demonstration preference)",
                arrival_mode=TransportMode.TRAIN,
                arrival_details="Demonstration Express, coach D1",
                arrival_at=seeded_at + timedelta(days=43),
                departure_mode=TransportMode.INSTITUTIONAL,
                departure_details="VAMNICOM demonstration shuttle",
                departure_at=seeded_at + timedelta(days=49),
                emergency_contact_name="Meera Patil (demonstration)",
                emergency_contact_phone="+91 90000 10002",
                emergency_contact_relationship="Sibling",
            )
        )

    material = db.scalar(
        select(TrainingMaterial).where(
            TrainingMaterial.programme_id == programme.id,
            TrainingMaterial.name == "Cooperative governance workbook (demonstration)",
        )
    )
    if material is None:
        material = TrainingMaterial(
            institution_id=institution.id,
            programme_id=programme.id,
            name="Cooperative governance workbook (demonstration)",
            description="Fictional printed workbook for local platform demonstration.",
            quantity_available=40,
        )
        db.add(material)
        db.flush()
    if not db.scalar(
        select(MaterialDistribution.id).where(
            MaterialDistribution.material_id == material.id,
            MaterialDistribution.enrollment_id == enrollment.id,
        )
    ):
        db.add(
            MaterialDistribution(
                material_id=material.id,
                enrollment_id=enrollment.id,
                distributed_by_id=admin.id,
                quantity=1,
            )
        )

    if not db.scalar(
        select(OperationsIssue.id).where(
            OperationsIssue.institution_id == institution.id,
            OperationsIssue.title == "Projector cable inspection (demonstration)",
        )
    ):
        db.add(
            OperationsIssue(
                institution_id=institution.id,
                reported_by_id=trainer.id,
                issue_type=OperationsIssueType.MAINTENANCE,
                priority=OperationsIssuePriority.MEDIUM,
                status=OperationsIssueStatus.OPEN,
                title="Projector cable inspection (demonstration)",
                description="Inspect the fictional spare cable before the opening workshop.",
                location="Demonstration Hall A",
            )
        )
        db.add(
            AuditLog(
                user_id=admin.id,
                event_type="operations.demonstration_seeded",
                success=True,
                details={
                    "programme_id": str(programme.id),
                    "notice": "Fictional demonstration operations data only",
                },
            )
        )


def seed_development_data(db: Session) -> None:
    roles: dict[RoleCode, Role] = {}
    for role_code, display_name in ROLE_NAMES.items():
        role = db.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            role = Role(code=role_code, display_name=display_name)
            db.add(role)
            db.flush()
        roles[role_code] = role

    institutions: dict[str, Institution] = {}
    for institution_code, name, institution_type, _parent, state, district in INSTITUTIONS:
        institution = db.scalar(select(Institution).where(Institution.code == institution_code))
        if institution is None:
            institution = Institution(
                code=institution_code,
                name=name,
                institution_type=institution_type,
            )
            db.add(institution)
            db.flush()
        institution.name = name
        institution.institution_type = institution_type
        institution.state = state
        institution.district = district
        institution.is_demo = True
        institution.profile_summary = (
            "Fictional demonstration institution for local development and testing only."
        )
        institutions[institution_code] = institution

    for institution_code, _name, _type, parent_code, _state, _district in INSTITUTIONS:
        institutions[institution_code].parent = institutions[parent_code] if parent_code else None

    verified_at = datetime.now(UTC)
    users: dict[RoleCode, User] = {}
    for email, full_name, role_code, institution_code in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(settings.seed_demo_password),
                status=AccountStatus.ACTIVE,
                email_verified_at=verified_at,
                institution=institutions[institution_code],
                roles=[roles[role_code]],
                profile=UserProfile(full_name=full_name),
            )
            db.add(user)
            db.flush()
        user.institution = institutions[institution_code]
        if user.profile:
            user.profile.full_name = full_name
        users[role_code] = user

    seed_career_faqs(db, users[RoleCode.NCCT_SUPER_ADMIN])

    programme = db.scalar(select(Programme).where(Programme.code == "CGOV-2026-DEMO"))
    if programme is None:
        deadline = verified_at + timedelta(days=30)
        start_date = (deadline + timedelta(days=15)).date()
        end_date = start_date + timedelta(days=4)
        institute_admin = users[RoleCode.INSTITUTE_ADMIN]
        super_admin = users[RoleCode.NCCT_SUPER_ADMIN]
        trainer = users[RoleCode.TRAINER]
        programme = Programme(
            institution_id=institutions["VAMNICOM"].id,
            created_by_id=institute_admin.id,
            updated_by_id=institute_admin.id,
            approved_by_id=super_admin.id,
            title="Cooperative Governance and Leadership",
            code="CGOV-2026-DEMO",
            summary="A practical programme for stronger boards and member-led governance.",
            description=(
                "Build practical skills in cooperative governance, board accountability, member "
                "participation and transparent institutional decision-making."
            ),
            mode=ProgrammeMode.HYBRID,
            status=ProgrammeStatus.PUBLISHED,
            eligibility_criteria=(
                "Open to individual cooperative-sector learners and nominees from PACS, SHGs "
                "and registered cooperative institutions."
            ),
            eligible_applicant_types=[item.value for item in EligibilityType],
            capacity=40,
            location="VAMNICOM Campus, Pune",
            language="English and Hindi",
            duration_days=5,
            application_deadline=deadline,
            start_date=start_date,
            end_date=end_date,
            approved_at=verified_at,
            published_at=verified_at,
        )
        db.add(programme)
        db.flush()
        batch = ProgrammeBatch(
            programme_id=programme.id,
            name="October Cohort",
            code="OCT-01",
            capacity=40,
            start_date=start_date,
            end_date=end_date,
            location="VAMNICOM Campus and online classroom",
        )
        db.add(batch)
        db.flush()
        db.add(
            BatchTrainerAssignment(
                batch_id=batch.id,
                trainer_id=trainer.id,
                assigned_by_id=institute_admin.id,
            )
        )

    trainee = users[RoleCode.TRAINEE]
    trainee_account = trainee.profile
    if trainee_account:
        trainee_account.phone = "9000000001"
        trainee_account.designation = "PACS member (demonstration)"
    trainee_profile = db.scalar(select(TraineeProfile).where(TraineeProfile.user_id == trainee.id))
    if trainee_profile is None:
        trainee_profile = TraineeProfile(user_id=trainee.id)
        db.add(trainee_profile)
        db.flush()
    trainee_profile.date_of_birth = date(1996, 8, 12)
    trainee_profile.gender = "Woman"
    trainee_profile.alternate_email = "asha.demo@example.test"
    trainee_profile.address_line = "Demonstration address, Training Road"
    trainee_profile.city = "Satara"
    trainee_profile.state = "Maharashtra"
    trainee_profile.postal_code = "415001"
    trainee_profile.preferred_language = "Marathi and Hindi"
    trainee_profile.preferred_location = "Western India"
    trainee_profile.career_interests = (
        "Demonstration interests: cooperative governance, member services and rural finance."
    )
    trainee_profile.skills = [
        "Member mobilisation",
        "Basic bookkeeping",
        "Digital literacy",
    ]
    trainee_profile.placement_visibility_consent = True
    trainee_profile.communication_consent = True
    trainee_profile.data_sharing_consent = False
    trainee_profile.completion_percent = 100
    trainee_profile.is_demo = True

    education = db.scalar(
        select(EducationRecord).where(
            EducationRecord.profile_id == trainee_profile.id,
            EducationRecord.institution_name == "Demonstration Cooperative College",
        )
    )
    if education is None:
        db.add(
            EducationRecord(
                profile_id=trainee_profile.id,
                qualification="Bachelor of Commerce (demonstration)",
                field_of_study="Cooperative management",
                institution_name="Demonstration Cooperative College",
                completion_year=2018,
                grade="First class",
                is_highest_qualification=True,
            )
        )
    employment = db.scalar(
        select(EmploymentRecord).where(
            EmploymentRecord.profile_id == trainee_profile.id,
            EmploymentRecord.employer_name == "Satara PACS Demonstration Society",
        )
    )
    if employment is None:
        db.add(
            EmploymentRecord(
                profile_id=trainee_profile.id,
                employer_name="Satara PACS Demonstration Society",
                job_title="Member services assistant (demonstration)",
                start_date=date(2022, 6, 1),
                is_current=True,
                responsibilities="Fictional member onboarding and records support.",
            )
        )
    membership = db.scalar(
        select(CooperativeMembership).where(
            CooperativeMembership.profile_id == trainee_profile.id,
            CooperativeMembership.member_number == "DEMO-PACS-1042",
        )
    )
    if membership is None:
        db.add(
            CooperativeMembership(
                profile_id=trainee_profile.id,
                institution_name="Satara PACS Demonstration Society",
                membership_type="Ordinary member (demonstration)",
                member_number="DEMO-PACS-1042",
                joined_on=date(2021, 4, 10),
            )
        )
    profile_document = db.scalar(
        select(TraineeDocument).where(
            TraineeDocument.profile_id == trainee_profile.id,
            TraineeDocument.filename == "demonstration-membership-proof.pdf",
        )
    )
    if profile_document is None:
        document_content = b"%PDF-1.4\nFictional demonstration document. Not valid evidence.\n%%EOF"
        db.add(
            TraineeDocument(
                profile_id=trainee_profile.id,
                uploaded_by_id=trainee.id,
                document_type=ProfileDocumentType.MEMBERSHIP,
                filename="demonstration-membership-proof.pdf",
                content_type="application/pdf",
                size_bytes=len(document_content),
                content=document_content,
                validation_status=DocumentValidationStatus.VERIFIED,
                validation_notes="Verified demonstration document; not valid for real use.",
                validated_by_id=users[RoleCode.NCCT_SUPER_ADMIN].id,
                validated_at=verified_at,
            )
        )

    current_enrollment = db.scalar(
        select(ProgrammeEnrollment).where(
            ProgrammeEnrollment.trainee_id == trainee.id,
            ProgrammeEnrollment.programme_id == programme.id,
        )
    )
    if current_enrollment is None:
        current_batch = db.scalar(
            select(ProgrammeBatch).where(ProgrammeBatch.programme_id == programme.id)
        )
        current_enrollment = ProgrammeEnrollment(
            trainee_id=trainee.id,
            programme_id=programme.id,
            batch_id=current_batch.id if current_batch else None,
            status=EnrollmentStatus.ENROLLED,
        )
        db.add(current_enrollment)
        db.flush()

    seed_demonstration_operations(
        db,
        users,
        institutions["VAMNICOM"],
        programme,
        current_enrollment,
        verified_at,
    )

    seed_demonstration_course(
        db,
        users,
        programme,
        current_enrollment,
        verified_at,
    )

    certificate_policy = db.scalar(
        select(CertificatePolicy).where(CertificatePolicy.programme_id == programme.id)
    )
    if certificate_policy is None:
        db.add(
            CertificatePolicy(
                programme_id=programme.id,
                configured_by_id=users[RoleCode.INSTITUTE_ADMIN].id,
                certificate_title="Certificate of Cooperative Governance",
                minimum_course_completion_percent=100,
                minimum_attendance_percent=75,
                minimum_assessment_score_percent=70,
                validity_days=730,
                is_active=True,
            )
        )

    if current_enrollment.batch_id:
        attendance_session = db.scalar(
            select(AttendanceSession).where(
                AttendanceSession.programme_id == programme.id,
                AttendanceSession.title == "Demonstration kiosk check-in",
            )
        )
        if attendance_session is None:
            attendance_session = AttendanceSession(
                programme_id=programme.id,
                batch_id=current_enrollment.batch_id,
                created_by_id=users[RoleCode.TRAINER].id,
                title="Demonstration kiosk check-in",
                starts_at=verified_at - timedelta(minutes=15),
                ends_at=verified_at + timedelta(hours=8),
                status=AttendanceSessionStatus.OPEN,
            )
            db.add(attendance_session)
        else:
            attendance_session.starts_at = verified_at - timedelta(minutes=15)
            attendance_session.ends_at = verified_at + timedelta(hours=8)
            attendance_session.status = AttendanceSessionStatus.OPEN

    completed_programme = db.scalar(select(Programme).where(Programme.code == "DIGI-2025-DEMO"))
    if completed_programme is None:
        institute_admin = users[RoleCode.INSTITUTE_ADMIN]
        super_admin = users[RoleCode.NCCT_SUPER_ADMIN]
        completed_programme = Programme(
            institution_id=institutions["VAMNICOM"].id,
            created_by_id=institute_admin.id,
            updated_by_id=institute_admin.id,
            approved_by_id=super_admin.id,
            title="Digital Services for Cooperatives (Demonstration)",
            code="DIGI-2025-DEMO",
            summary="A fictional completed programme used to demonstrate trainee history.",
            description=(
                "Demonstration-only learning record covering digital member services and "
                "responsible data handling."
            ),
            mode=ProgrammeMode.OFFLINE,
            status=ProgrammeStatus.ARCHIVED,
            eligibility_criteria="Fictional demonstration eligibility.",
            eligible_applicant_types=[EligibilityType.INDIVIDUAL.value],
            capacity=30,
            location="VAMNICOM Demonstration Campus, Pune",
            language="Marathi and English",
            duration_days=3,
            application_deadline=datetime(2025, 6, 1, tzinfo=UTC),
            start_date=date(2025, 6, 15),
            end_date=date(2025, 6, 17),
            approved_at=datetime(2025, 5, 20, tzinfo=UTC),
            published_at=datetime(2025, 5, 21, tzinfo=UTC),
            archived_at=datetime(2025, 6, 30, tzinfo=UTC),
        )
        db.add(completed_programme)
        db.flush()
        db.add(
            ProgrammeBatch(
                programme_id=completed_programme.id,
                name="Demonstration June Cohort",
                code="DEMO-JUN-25",
                capacity=30,
                start_date=completed_programme.start_date,
                end_date=completed_programme.end_date,
                location=completed_programme.location,
            )
        )
        db.flush()
    completed_enrollment = db.scalar(
        select(ProgrammeEnrollment).where(
            ProgrammeEnrollment.trainee_id == trainee.id,
            ProgrammeEnrollment.programme_id == completed_programme.id,
        )
    )
    if completed_enrollment is None:
        completed_batch = db.scalar(
            select(ProgrammeBatch).where(ProgrammeBatch.programme_id == completed_programme.id)
        )
        completed_enrollment = ProgrammeEnrollment(
            trainee_id=trainee.id,
            programme_id=completed_programme.id,
            batch_id=completed_batch.id if completed_batch else None,
            status=EnrollmentStatus.COMPLETED,
            enrolled_at=datetime(2025, 6, 5, tzinfo=UTC),
            completed_at=datetime(2025, 6, 17, tzinfo=UTC),
        )
        db.add(completed_enrollment)
        db.flush()
    if not db.scalar(
        select(AttendanceRecord.id).where(AttendanceRecord.enrollment_id == completed_enrollment.id)
    ):
        db.add_all(
            [
                AttendanceRecord(
                    enrollment_id=completed_enrollment.id,
                    session_date=date(2025, 6, 15),
                    topic="Digital member records (demonstration)",
                    status=AttendanceStatus.PRESENT,
                ),
                AttendanceRecord(
                    enrollment_id=completed_enrollment.id,
                    session_date=date(2025, 6, 16),
                    topic="Responsible data handling (demonstration)",
                    status=AttendanceStatus.PRESENT,
                ),
            ]
        )
    if not db.scalar(
        select(AssessmentRecord.id).where(AssessmentRecord.enrollment_id == completed_enrollment.id)
    ):
        db.add(
            AssessmentRecord(
                enrollment_id=completed_enrollment.id,
                title="Demonstration final assessment",
                score=84,
                maximum_score=100,
                result=AssessmentResult.PASSED,
                assessed_at=datetime(2025, 6, 17, tzinfo=UTC),
            )
        )
    if not db.scalar(
        select(CertificateRecord.id).where(
            CertificateRecord.certificate_number == "DEMO-CERT-2025-001"
        )
    ):
        db.add(
            CertificateRecord(
                enrollment_id=completed_enrollment.id,
                certificate_number="DEMO-CERT-2025-001",
                title="Demonstration certificate - not valid",
                issued_at=datetime(2025, 6, 20, tzinfo=UTC),
            )
        )

    completed_policy = db.scalar(
        select(CertificatePolicy).where(CertificatePolicy.programme_id == completed_programme.id)
    )
    if completed_policy is None:
        completed_policy = CertificatePolicy(
            programme_id=completed_programme.id,
            configured_by_id=users[RoleCode.INSTITUTE_ADMIN].id,
            certificate_title="Certificate in Digital Cooperative Services (Demonstration)",
            minimum_course_completion_percent=0,
            minimum_attendance_percent=0,
            minimum_assessment_score_percent=0,
            validity_days=730,
            is_active=True,
        )
        db.add(completed_policy)
        db.flush()
    digital_certificate = db.scalar(
        select(DigitalCertificate).where(
            DigitalCertificate.enrollment_id == completed_enrollment.id
        )
    )
    if digital_certificate is None:
        digital_certificate = DigitalCertificate(
            enrollment_id=completed_enrollment.id,
            policy_id=completed_policy.id,
            issued_by_id=users[RoleCode.INSTITUTE_ADMIN].id,
            certificate_number="NCCT-DEMO-DIGITAL-2025-001",
            verification_token=token_urlsafe(32),
            title=completed_policy.certificate_title,
            course_completion_percent=100,
            attendance_percent=100,
            assessment_score_percent=84,
            pdf_content=b"pending",
            issued_at=datetime(2025, 6, 20, tzinfo=UTC),
            expires_at=verified_at + timedelta(days=730),
        )
        digital_certificate.enrollment = completed_enrollment
        digital_certificate.pdf_content = generate_certificate_pdf(
            digital_certificate, completed_enrollment
        )
        db.add(digital_certificate)
        db.flush()

    for skill in trainee_profile.skills:
        if not db.scalar(
            select(VerifiedEmploymentSkill.id).where(
                VerifiedEmploymentSkill.trainee_id == trainee.id,
                VerifiedEmploymentSkill.certificate_id == digital_certificate.id,
                VerifiedEmploymentSkill.name == skill,
            )
        ):
            db.add(
                VerifiedEmploymentSkill(
                    trainee_id=trainee.id,
                    certificate_id=digital_certificate.id,
                    name=skill,
                )
            )

    employer_profile = db.scalar(
        select(EmployerProfile).where(EmployerProfile.institution_id == institutions["EMP-DEMO"].id)
    )
    if employer_profile is None:
        employer_profile = EmployerProfile(
            institution_id=institutions["EMP-DEMO"].id,
            registered_by_id=users[RoleCode.EMPLOYER_RECRUITER].id,
            verified_by_id=users[RoleCode.NCCT_SUPER_ADMIN].id,
            industry="Cooperative technology and member services",
            website="https://example.invalid/ncct-employer-demo",
            company_size="51-200 (demonstration)",
            description=(
                "A fictional verified employer profile for local development and testing only."
            ),
            headquarters="New Delhi (demonstration)",
            registration_number="DEMO-EMPLOYER-001",
            verification_status=EmployerVerificationStatus.VERIFIED,
            verification_notes="Verified fictional demonstration employer.",
            verified_at=verified_at,
        )
        db.add(employer_profile)
        db.flush()

    employment_profile = db.scalar(
        select(TraineeEmploymentProfile).where(TraineeEmploymentProfile.trainee_id == trainee.id)
    )
    if employment_profile is None:
        resume_content = (
            b"%PDF-1.4\nFictional demonstration resume. Not a real candidate record.\n%%EOF"
        )
        employment_profile = TraineeEmploymentProfile(
            trainee_id=trainee.id,
            headline="Certified cooperative member-services associate (demonstration)",
            professional_summary=(
                "Fictional trainee profile with experience in member onboarding, digital "
                "records and cooperative administration."
            ),
            preferred_roles=["Member services", "Cooperative operations"],
            preferred_locations=["Pune", "Remote"],
            open_to_work=True,
            resume_filename="asha-patil-demonstration-resume.pdf",
            resume_content_type="application/pdf",
            resume_size_bytes=len(resume_content),
            resume_content=resume_content,
            resume_uploaded_at=verified_at,
        )
        db.add(employment_profile)

    demonstration_job = db.scalar(
        select(JobPosting).where(
            JobPosting.employer_profile_id == employer_profile.id,
            JobPosting.title == "Cooperative Member Services Associate (Demonstration)",
        )
    )
    if demonstration_job is None:
        demonstration_job = JobPosting(
            employer_profile_id=employer_profile.id,
            created_by_id=users[RoleCode.EMPLOYER_RECRUITER].id,
            updated_by_id=users[RoleCode.EMPLOYER_RECRUITER].id,
            title="Cooperative Member Services Associate (Demonstration)",
            description=(
                "Support fictional cooperative members with digital records, onboarding and "
                "clear service communication. Demonstration vacancy only."
            ),
            location="Pune, Maharashtra",
            employment_type=EmploymentType.FULL_TIME,
            workplace_mode=WorkplaceMode.HYBRID,
            required_skills=["Digital literacy", "Member mobilisation"],
            preferred_skills=["Basic bookkeeping"],
            minimum_experience_years=0,
            vacancies=2,
            salary_minimum=300000,
            salary_maximum=420000,
            application_deadline=verified_at + timedelta(days=30),
            status=JobStatus.PUBLISHED,
            published_at=verified_at,
            programme_requirements=[JobProgrammeRequirement(programme_id=completed_programme.id)],
        )
        db.add(demonstration_job)

    for consent_type, granted in (
        ("placement_visibility_consent", True),
        ("communication_consent", True),
        ("data_sharing_consent", False),
    ):
        if not db.scalar(
            select(ConsentRecord.id).where(
                ConsentRecord.user_id == trainee.id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.version == "profile-v1-demo",
            )
        ):
            db.add(
                ConsentRecord(
                    user_id=trainee.id,
                    consent_type=consent_type,
                    version="profile-v1-demo",
                    granted=granted,
                )
            )
    if not db.scalar(
        select(AuditLog.id).where(
            AuditLog.event_type == "profile.demonstration_seeded",
            AuditLog.user_id == users[RoleCode.NCCT_SUPER_ADMIN].id,
        )
    ):
        db.add(
            AuditLog(
                user_id=users[RoleCode.NCCT_SUPER_ADMIN].id,
                event_type="profile.demonstration_seeded",
                success=True,
                details={
                    "target_user_id": str(trainee.id),
                    "notice": "Fictional demonstration data only",
                },
            )
        )

    db.commit()


def main() -> None:
    if settings.environment != "development":
        raise RuntimeError(
            "Development seed data can only be loaded in the development environment"
        )

    with SessionLocal() as db:
        seed_development_data(db)

    print("Development roles, institutions and demo accounts are ready.")


if __name__ == "__main__":
    main()
