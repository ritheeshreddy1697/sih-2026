from enum import StrEnum


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class RoleCode(StrEnum):
    NCCT_SUPER_ADMIN = "ncct_super_admin"
    INSTITUTE_ADMIN = "institute_admin"
    TRAINER = "trainer"
    TRAINEE = "trainee"
    NOMINATING_INSTITUTION = "nominating_institution"
    EMPLOYER_RECRUITER = "employer_recruiter"


class InstitutionType(StrEnum):
    NCCT = "ncct"
    TRAINING_INSTITUTE = "training_institute"
    VAMNICOM = "vamnicom"
    RICM = "ricm"
    ICM = "icm"
    PACS = "pacs"
    SHG = "shg"
    DAIRY_COOPERATIVE = "dairy_cooperative"
    OTHER_COOPERATIVE = "other_cooperative"
    NOMINATING_INSTITUTION = "nominating_institution"
    EMPLOYER = "employer"


class ProgrammeMode(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class ProgrammeStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"
    WITHDRAWN = "withdrawn"


class EligibilityType(StrEnum):
    INDIVIDUAL = "individual"
    PACS = "pacs"
    SHG = "shg"
    COOPERATIVE_INSTITUTION = "cooperative_institution"


class NominationSource(StrEnum):
    INDIVIDUAL = "individual"
    BULK_CSV = "bulk_csv"


class DocumentType(StrEnum):
    IDENTITY = "identity"
    ELIGIBILITY = "eligibility"
    NOMINATION_LETTER = "nomination_letter"
    OTHER = "other"


class ProfileDocumentType(StrEnum):
    IDENTITY = "identity"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    MEMBERSHIP = "membership"
    RESUME = "resume"
    OTHER = "other"


class DocumentValidationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class EnrollmentStatus(StrEnum):
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"


class AttendanceSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class AttendanceSource(StrEnum):
    KIOSK = "kiosk"
    MANUAL = "manual"
    BIOMETRIC = "biometric"
    BIOMETRIC_MANUAL = "biometric_manual"


class KioskDeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class CorrectionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BiometricChallengePurpose(StrEnum):
    ENROLLMENT = "enrollment"
    ATTENDANCE = "attendance"


class BiometricChallengeType(StrEnum):
    TURN_HEAD = "turn_head"


class BiometricVerificationStatus(StrEnum):
    VERIFIED = "verified"
    MANUAL_REVIEW = "manual_review"
    REJECTED = "rejected"


class CertificateState(StrEnum):
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ScheduleStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BedAllocationStatus(StrEnum):
    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class MealPreference(StrEnum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    EGGETARIAN = "eggetarian"
    NON_VEGETARIAN = "non_vegetarian"
    JAIN = "jain"
    OTHER = "other"


class TransportMode(StrEnum):
    SELF = "self"
    TRAIN = "train"
    BUS = "bus"
    FLIGHT = "flight"
    INSTITUTIONAL = "institutional"
    OTHER = "other"


class OperationsIssueType(StrEnum):
    MAINTENANCE = "maintenance"
    PARTICIPANT = "participant"


class OperationsIssuePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class OperationsIssueStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EmployerVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class WorkplaceMode(StrEnum):
    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class JobApplicationStatus(StrEnum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CareerLanguage(StrEnum):
    ENGLISH = "en"
    HINDI = "hi"
    TELUGU = "te"


class CareerConversationStatus(StrEnum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class CareerMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class CareerFeedbackRating(StrEnum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class CareerEscalationStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class AssessmentResult(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LessonType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"
    TEXT = "text"
    EXTERNAL_RESOURCE = "external_resource"


class LearningProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AssignmentSubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    RESUBMISSION_REQUESTED = "resubmission_requested"


class AssessmentType(StrEnum):
    QUIZ = "quiz"
    PRE_TRAINING = "pre_training"
    POST_TRAINING = "post_training"


class AssessmentAttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
