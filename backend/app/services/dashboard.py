from app.core.permissions import Permission, has_permission
from app.models.enums import RoleCode
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardMetric,
    DashboardNotification,
    DashboardQuickAction,
    DashboardResponse,
    DashboardScheduleItem,
    MetricTone,
)


def metric(label: str, value: str, change: str, tone: MetricTone = "neutral") -> DashboardMetric:
    return DashboardMetric(label=label, value=value, change=change, tone=tone)


def action(
    label: str,
    description: str,
    href: str,
    permission: Permission,
) -> DashboardQuickAction:
    return DashboardQuickAction(
        label=label,
        description=description,
        href=href,
        permission=permission,
    )


DASHBOARDS: dict[RoleCode, DashboardResponse] = {
    RoleCode.NCCT_SUPER_ADMIN: DashboardResponse(
        dashboard_key=RoleCode.NCCT_SUPER_ADMIN,
        title="National training overview",
        description="Monitor institute delivery, nominations and outcomes across the NCCT network.",
        metrics=[
            metric("Active institutes", "18", "All institutes reporting", "success"),
            metric("Programs this quarter", "42", "6 starting this month", "accent"),
            metric("Pending nominations", "126", "24 need attention", "warning"),
            metric("Completion rate", "87%", "Up 4% this quarter", "success"),
        ],
        quick_actions=[
            action(
                "Review programmes",
                "Approve programme submissions across institutes.",
                "/programmes",
                Permission.PROGRAMMES_APPROVE,
            ),
            action(
                "Add an institute",
                "Start a new institute onboarding record.",
                "/workspace/institutions",
                Permission.PLATFORM_MANAGE,
            ),
            action(
                "Open national report",
                "View consolidated participation and completion data.",
                "/workspace/reports",
                Permission.PLATFORM_MANAGE,
            ),
        ],
        schedule_title="Network priorities",
        schedule=[
            DashboardScheduleItem(
                date_label="28 Sep",
                title="Quarterly institute review",
                meta="18 institutes · Online",
                status="confirmed",
            ),
            DashboardScheduleItem(
                date_label="30 Sep",
                title="Nomination approval deadline",
                meta="126 pending records",
                status="due",
            ),
            DashboardScheduleItem(
                date_label="04 Oct",
                title="National outcome report",
                meta="FY 2026-27 · Quarter 2",
                status="scheduled",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="VAMNICOM submitted its monthly report",
                description="Attendance and completion data passed validation.",
                time_label="18 minutes ago",
            ),
            DashboardActivityItem(
                title="24 nominations approved",
                description="Candidates were assigned to October programs.",
                time_label="2 hours ago",
            ),
            DashboardActivityItem(
                title="RICM Bengaluru updated its calendar",
                description="Two trainer-development sessions were added.",
                time_label="Yesterday",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="ncct-1",
                title="24 nominations need review",
                description="The September approval window closes in two days.",
            ),
            DashboardNotification(
                id="ncct-2",
                title="Monthly reports received",
                description="All 18 active institutes have submitted data.",
                unread=False,
            ),
        ],
    ),
    RoleCode.INSTITUTE_ADMIN: DashboardResponse(
        dashboard_key=RoleCode.INSTITUTE_ADMIN,
        title="Institute operations",
        description="Keep batches, trainers and learner participation on schedule.",
        metrics=[
            metric("Active batches", "8", "3 programs represented", "accent"),
            metric("Current trainees", "286", "34 joined this month", "success"),
            metric("Assigned trainers", "24", "2 assignments pending", "warning"),
            metric("Average attendance", "92%", "Above NCCT target", "success"),
        ],
        quick_actions=[
            action(
                "Create a programme",
                "Prepare eligibility, dates, capacity and delivery mode.",
                "/programmes/new",
                Permission.PROGRAMMES_MANAGE,
            ),
            action(
                "Review applications",
                "Make admissions decisions for active programmes.",
                "/applications",
                Permission.APPLICATIONS_REVIEW,
            ),
            action(
                "Manage courses",
                "Build lessons, assignments and assessments.",
                "/learning",
                Permission.LEARNING_MANAGE,
            ),
        ],
        schedule_title="Institute calendar",
        schedule=[
            DashboardScheduleItem(
                date_label="Today",
                title="Cooperative governance · Batch 12",
                meta="Room 204 · 38 trainees",
                status="scheduled",
            ),
            DashboardScheduleItem(
                date_label="29 Sep",
                title="Trainer allocation review",
                meta="Academic office · 2 pending",
                status="due",
            ),
            DashboardScheduleItem(
                date_label="02 Oct",
                title="New batch orientation",
                meta="Main auditorium · 52 trainees",
                status="confirmed",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="Batch 9 attendance submitted",
                description="Monthly attendance is ready for NCCT review.",
                time_label="35 minutes ago",
            ),
            DashboardActivityItem(
                title="Dr. Meera Shah assigned",
                description="Assigned to Rural Credit Management, Batch 4.",
                time_label="3 hours ago",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="institute-1",
                title="Two sessions need trainers",
                description="Assignments are due before 29 September.",
            ),
            DashboardNotification(
                id="institute-2",
                title="Attendance is ready",
                description="Batch 9 can now be submitted to NCCT.",
                unread=False,
            ),
        ],
    ),
    RoleCode.TRAINER: DashboardResponse(
        dashboard_key=RoleCode.TRAINER,
        title="Trainer workspace",
        description="Prepare upcoming sessions and keep learner progress up to date.",
        metrics=[
            metric("Sessions this week", "6", "Next session today", "accent"),
            metric("Active learners", "84", "Across 3 batches"),
            metric("Assessments to review", "17", "5 due tomorrow", "warning"),
            metric("Average attendance", "94%", "Above institute average", "success"),
        ],
        quick_actions=[
            action(
                "Mark attendance",
                "Open today's participant list.",
                "/attendance",
                Permission.ATTENDANCE_MANAGE,
            ),
            action(
                "Manage course content",
                "Prepare lessons and learning resources.",
                "/learning",
                Permission.LEARNING_MANAGE,
            ),
            action(
                "Review assessments",
                "Grade submitted learner work.",
                "/learning",
                Permission.ASSESSMENTS_REVIEW,
            ),
        ],
        schedule_title="Teaching schedule",
        schedule=[
            DashboardScheduleItem(
                date_label="10:30",
                title="Principles of cooperation",
                meta="Batch 12 · Room 204",
                status="confirmed",
            ),
            DashboardScheduleItem(
                date_label="14:00",
                title="Case discussion: dairy unions",
                meta="Batch 9 · Online",
                status="scheduled",
            ),
            DashboardScheduleItem(
                date_label="Tomorrow",
                title="Rural credit assessment review",
                meta="17 submissions",
                status="due",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="12 learners completed the quiz",
                description="Batch 12 results are ready for review.",
                time_label="42 minutes ago",
            ),
            DashboardActivityItem(
                title="Session material viewed 76 times",
                description="Cooperative Governance, Module 3.",
                time_label="Yesterday",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="trainer-1",
                title="Five assessments due tomorrow",
                description="Complete reviews before the batch closes.",
            ),
            DashboardNotification(
                id="trainer-2",
                title="Room changed for Batch 12",
                description="Today's 10:30 session is now in Room 204.",
            ),
        ],
    ),
    RoleCode.TRAINEE: DashboardResponse(
        dashboard_key=RoleCode.TRAINEE,
        title="My learning",
        description="Continue your program, meet upcoming deadlines and track completion.",
        metrics=[
            metric("Program progress", "68%", "4 of 6 modules complete", "accent"),
            metric("Upcoming sessions", "3", "Next session tomorrow"),
            metric("Assessments due", "2", "One due this week", "warning"),
            metric("Certificates", "1", "Foundation course earned", "success"),
        ],
        quick_actions=[
            action(
                "Browse programmes",
                "Find training that matches your eligibility.",
                "/programmes",
                Permission.PROGRAMMES_VIEW,
            ),
            action(
                "Track applications",
                "See decisions and upload supporting documents.",
                "/applications",
                Permission.APPLICATIONS_APPLY,
            ),
            action(
                "Continue learning",
                "Resume lessons, assignments and assessments.",
                "/learning",
                Permission.LEARNING_ACCESS,
            ),
            action(
                "Show attendance QR",
                "Open your secure trainee identity code.",
                "/attendance",
                Permission.ATTENDANCE_SELF,
            ),
        ],
        schedule_title="Coming up",
        schedule=[
            DashboardScheduleItem(
                date_label="Tomorrow",
                title="Cooperative financial management",
                meta="10:30 · Online",
                status="confirmed",
            ),
            DashboardScheduleItem(
                date_label="01 Oct",
                title="Rural credit case response",
                meta="Assessment · 11:59 PM",
                status="due",
            ),
            DashboardScheduleItem(
                date_label="04 Oct",
                title="Field visit: producer cooperative",
                meta="Meet at institute gate · 08:30",
                status="scheduled",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="Module 4 completed",
                description="Your quiz score was 86%.",
                time_label="Yesterday",
            ),
            DashboardActivityItem(
                title="Certificate added",
                description="Cooperative Foundations is ready to view.",
                time_label="5 days ago",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="trainee-1",
                title="Assessment due 1 October",
                description="Submit the rural credit case response before 11:59 PM.",
            ),
            DashboardNotification(
                id="trainee-2",
                title="Field visit confirmed",
                description="Transport details are available in your schedule.",
                unread=False,
            ),
        ],
    ),
    RoleCode.NOMINATING_INSTITUTION: DashboardResponse(
        dashboard_key=RoleCode.NOMINATING_INSTITUTION,
        title="Nomination overview",
        description="Track nominated candidates from approval through program completion.",
        metrics=[
            metric("Active nominees", "46", "Across 5 programs", "accent"),
            metric("Awaiting approval", "8", "3 need documents", "warning"),
            metric("Currently training", "31", "92% attendance", "success"),
            metric("Completed", "112", "18 this quarter"),
        ],
        quick_actions=[
            action(
                "Nominate a candidate",
                "Choose a programme and submit candidate details.",
                "/programmes",
                Permission.NOMINATIONS_CREATE,
            ),
            action(
                "Review status",
                "Check approvals and document requests.",
                "/nominations",
                Permission.NOMINATIONS_CREATE,
            ),
            action(
                "View outcomes",
                "Review completion and certificate results.",
                "/workspace/outcomes",
                Permission.NOMINATIONS_MANAGE,
            ),
        ],
        schedule_title="Nomination deadlines",
        schedule=[
            DashboardScheduleItem(
                date_label="30 Sep",
                title="October program nominations",
                meta="8 drafts · 3 documents missing",
                status="due",
            ),
            DashboardScheduleItem(
                date_label="03 Oct",
                title="Candidate orientation",
                meta="Online · 11:00",
                status="confirmed",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="Four candidates approved",
                description="Cooperative Banking program, October intake.",
                time_label="1 hour ago",
            ),
            DashboardActivityItem(
                title="Completion results published",
                description="18 certificates are available for review.",
                time_label="Yesterday",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="nominator-1",
                title="Three nominations need documents",
                description="Add identity and sponsorship documents before submission.",
            ),
            DashboardNotification(
                id="nominator-2",
                title="Four candidates approved",
                description="Orientation is scheduled for 3 October.",
                unread=False,
            ),
        ],
    ),
    RoleCode.EMPLOYER_RECRUITER: DashboardResponse(
        dashboard_key=RoleCode.EMPLOYER_RECRUITER,
        title="Talent workspace",
        description="Review eligible cooperative-sector talent and manage hiring follow-up.",
        metrics=[
            metric("Eligible trainees", "124", "21 newly available", "accent"),
            metric("Shortlisted", "9", "Across 4 roles"),
            metric("Interviews", "4", "Two this week", "warning"),
            metric("Offers recorded", "2", "Awaiting acceptance", "success"),
        ],
        quick_actions=[
            action(
                "Browse eligible talent",
                "Filter trainees by skills and program.",
                "/workspace/talent",
                Permission.RECRUITMENT_ACCESS,
            ),
            action(
                "Manage shortlist",
                "Review candidates saved by your team.",
                "/workspace/shortlist",
                Permission.RECRUITMENT_ACCESS,
            ),
            action(
                "Record an outcome",
                "Update interview or offer status.",
                "/workspace/outcomes",
                Permission.RECRUITMENT_ACCESS,
            ),
        ],
        schedule_title="Hiring follow-up",
        schedule=[
            DashboardScheduleItem(
                date_label="29 Sep",
                title="Interview: Programme Associate",
                meta="2 candidates · Online",
                status="confirmed",
            ),
            DashboardScheduleItem(
                date_label="02 Oct",
                title="Shortlist review",
                meta="9 candidates · Hiring team",
                status="scheduled",
            ),
        ],
        activity=[
            DashboardActivityItem(
                title="21 trainee profiles added",
                description="Newly certified in cooperative management.",
                time_label="Today",
            ),
            DashboardActivityItem(
                title="Interview feedback recorded",
                description="Programme Associate · 2 candidates.",
                time_label="Yesterday",
            ),
        ],
        notifications=[
            DashboardNotification(
                id="employer-1",
                title="Two interviews this week",
                description="Candidate profiles and schedules are ready.",
            ),
            DashboardNotification(
                id="employer-2",
                title="New certified trainees",
                description="21 profiles now match your saved criteria.",
            ),
        ],
    ),
}

ROLE_PRIORITY = tuple(DASHBOARDS)


def get_dashboard(role_codes: set[RoleCode]) -> DashboardResponse:
    dashboard_role = next((role for role in ROLE_PRIORITY if role in role_codes), None)
    if dashboard_role is None:
        raise LookupError("No dashboard is configured for this account")

    dashboard = DASHBOARDS[dashboard_role].model_copy(deep=True)
    dashboard.quick_actions = [
        quick_action
        for quick_action in dashboard.quick_actions
        if has_permission(role_codes, quick_action.permission)
    ]
    return dashboard
