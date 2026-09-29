from enum import StrEnum

from app.models.enums import RoleCode


class Permission(StrEnum):
    PLATFORM_MANAGE = "platform:manage"
    INSTITUTION_MANAGE = "institution:manage"
    TRAINING_DELIVER = "training:deliver"
    LEARNING_ACCESS = "learning:access"
    NOMINATIONS_MANAGE = "nominations:manage"
    RECRUITMENT_ACCESS = "recruitment:access"
    PROGRAMMES_VIEW = "programmes:view"
    PROGRAMMES_MANAGE = "programmes:manage"
    PROGRAMMES_APPROVE = "programmes:approve"
    APPLICATIONS_APPLY = "applications:apply"
    APPLICATIONS_REVIEW = "applications:review"
    NOMINATIONS_CREATE = "nominations:create"
    PROFILE_SELF_MANAGE = "profiles:self"
    PROFILE_TRAINEE_DIRECTORY_VIEW = "profiles:view_trainee_directory"
    PROFILE_ADMIN_VIEW = "profiles:view_private"
    PROFILE_INSTITUTION_MANAGE = "profiles:manage_institutions"
    PROFILE_DOCUMENT_VALIDATE = "profiles:validate_documents"
    LEARNING_MANAGE = "learning:manage"
    ASSESSMENTS_REVIEW = "assessments:review"
    ATTENDANCE_SELF = "attendance:self"
    ATTENDANCE_MANAGE = "attendance:manage"
    ATTENDANCE_APPROVE = "attendance:approve"
    ATTENDANCE_REPORTS = "attendance:reports"
    CERTIFICATES_SELF = "certificates:self"
    CERTIFICATES_MANAGE = "certificates:manage"
    OPERATIONS_SELF = "operations:self"
    OPERATIONS_MANAGE = "operations:manage"
    EMPLOYMENT_SELF = "employment:self"
    EMPLOYMENT_MANAGE = "employment:manage"
    EMPLOYMENT_VERIFY = "employment:verify"
    CAREER_COUNSELLING = "career:counselling"
    CAREER_SUPPORT = "career:support"
    ANALYTICS_VIEW = "analytics:view"
    NOTIFICATIONS_SEND = "notifications:send"


ROLE_PERMISSIONS: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.NCCT_SUPER_ADMIN: frozenset(Permission),
    RoleCode.INSTITUTE_ADMIN: frozenset(
        {
            Permission.INSTITUTION_MANAGE,
            Permission.TRAINING_DELIVER,
            Permission.PROGRAMMES_VIEW,
            Permission.PROGRAMMES_MANAGE,
            Permission.APPLICATIONS_REVIEW,
            Permission.PROFILE_TRAINEE_DIRECTORY_VIEW,
            Permission.PROFILE_ADMIN_VIEW,
            Permission.PROFILE_INSTITUTION_MANAGE,
            Permission.PROFILE_DOCUMENT_VALIDATE,
            Permission.LEARNING_MANAGE,
            Permission.ASSESSMENTS_REVIEW,
            Permission.ATTENDANCE_MANAGE,
            Permission.ATTENDANCE_APPROVE,
            Permission.ATTENDANCE_REPORTS,
            Permission.CERTIFICATES_MANAGE,
            Permission.OPERATIONS_MANAGE,
            Permission.ANALYTICS_VIEW,
            Permission.NOTIFICATIONS_SEND,
        }
    ),
    RoleCode.TRAINER: frozenset(
        {
            Permission.TRAINING_DELIVER,
            Permission.PROGRAMMES_VIEW,
            Permission.PROFILE_TRAINEE_DIRECTORY_VIEW,
            Permission.LEARNING_MANAGE,
            Permission.ASSESSMENTS_REVIEW,
            Permission.ATTENDANCE_MANAGE,
            Permission.ATTENDANCE_REPORTS,
        }
    ),
    RoleCode.TRAINEE: frozenset(
        {
            Permission.LEARNING_ACCESS,
            Permission.PROGRAMMES_VIEW,
            Permission.APPLICATIONS_APPLY,
            Permission.PROFILE_SELF_MANAGE,
            Permission.ATTENDANCE_SELF,
            Permission.CERTIFICATES_SELF,
            Permission.OPERATIONS_SELF,
            Permission.EMPLOYMENT_SELF,
            Permission.CAREER_COUNSELLING,
        }
    ),
    RoleCode.NOMINATING_INSTITUTION: frozenset(
        {
            Permission.NOMINATIONS_MANAGE,
            Permission.PROGRAMMES_VIEW,
            Permission.NOMINATIONS_CREATE,
        }
    ),
    RoleCode.EMPLOYER_RECRUITER: frozenset(
        {Permission.RECRUITMENT_ACCESS, Permission.EMPLOYMENT_MANAGE}
    ),
}


def has_permission(role_codes: set[RoleCode], permission: Permission) -> bool:
    return any(
        permission in ROLE_PERMISSIONS.get(role_code, frozenset()) for role_code in role_codes
    )


def permissions_for_roles(role_codes: set[RoleCode]) -> set[Permission]:
    permissions: set[Permission] = set()
    for role_code in role_codes:
        permissions.update(ROLE_PERMISSIONS.get(role_code, frozenset()))
    return permissions
