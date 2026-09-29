export type ApiClientOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
};

export type RoleCode =
  | "ncct_super_admin"
  | "institute_admin"
  | "trainer"
  | "trainee"
  | "nominating_institution"
  | "employer_recruiter";

export type AccountStatus = "active" | "suspended" | "pending_verification";

export type PermissionCode =
  | "platform:manage"
  | "institution:manage"
  | "training:deliver"
  | "learning:access"
  | "nominations:manage"
  | "recruitment:access"
  | "programmes:view"
  | "programmes:manage"
  | "programmes:approve"
  | "applications:apply"
  | "applications:review"
  | "nominations:create"
  | "profiles:self"
  | "profiles:view_trainee_directory"
  | "profiles:view_private"
  | "profiles:manage_institutions"
  | "profiles:validate_documents"
  | "learning:manage"
  | "assessments:review"
  | "attendance:self"
  | "attendance:manage"
  | "attendance:approve"
  | "attendance:reports"
  | "certificates:self"
  | "certificates:manage"
  | "operations:self"
  | "operations:manage"
  | "employment:self"
  | "employment:manage"
  | "employment:verify"
  | "career:counselling"
  | "career:support"
  | "analytics:view"
  | "notifications:send";

export type User = {
  id: string;
  email: string;
  status: AccountStatus;
  roles: Array<{ code: RoleCode; display_name: string }>;
  permissions: PermissionCode[];
  profile: {
    full_name: string;
    phone: string | null;
    designation: string | null;
  } | null;
  institution: {
    id: string;
    name: string;
    code: string;
    institution_type: string;
  } | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
};

export type HealthResponse = {
  status: string;
  service: string;
};

export type PasswordResetRequestResponse = {
  message: string;
  reset_token: string | null;
};

export type AccountDeletionRequest = {
  id: string;
  user_id: string;
  account_email: string;
  account_name: string;
  status: "pending" | "cancelled" | "completed";
  reason: string | null;
  requested_at: string;
  scheduled_for: string;
  cancelled_at: string | null;
  completed_at: string | null;
  resolution_note: string | null;
};

export type DashboardMetric = {
  label: string;
  value: string;
  change: string;
  tone: "neutral" | "success" | "warning" | "accent";
};

export type DashboardQuickAction = {
  label: string;
  description: string;
  href: string;
  permission: PermissionCode;
};

export type DashboardScheduleItem = {
  date_label: string;
  title: string;
  meta: string;
  status: "scheduled" | "due" | "completed" | "pending" | "confirmed";
};

export type DashboardNotification = {
  id: string;
  title: string;
  description: string;
  unread: boolean;
};

export type NotificationItem = DashboardNotification & {
  sender_name: string;
  created_at: string;
};

export type NotificationTargetType = "trainees" | "trainers" | "institutions";

export type DashboardResponse = {
  dashboard_key: RoleCode;
  title: string;
  description: string;
  metrics: DashboardMetric[];
  quick_actions: DashboardQuickAction[];
  schedule_title: string;
  schedule: DashboardScheduleItem[];
  activity: Array<{ title: string; description: string; time_label: string }>;
  notifications: DashboardNotification[];
};

export type AnalyticsMetricKey =
  | "registrations"
  | "approved_participants"
  | "attendance_percentage"
  | "course_completion_rate"
  | "assessment_improvement"
  | "dropout_rate"
  | "certificates_issued"
  | "job_applications"
  | "interviews"
  | "placements";

export type AnalyticsFilters = {
  institution_id?: string;
  programme_id?: string;
  start_date?: string;
  end_date?: string;
  state?: string;
  gender?: string;
  participant_category?: EligibilityType;
};

export type AnalyticsFilterOptions = {
  institutions: Array<{
    id: string;
    name: string;
    code: string;
    state: string | null;
    is_demo: boolean;
  }>;
  programmes: Array<{
    id: string;
    institution_id: string;
    title: string;
    code: string;
    start_date: string;
    is_demo: boolean;
  }>;
  states: string[];
  genders: string[];
  participant_categories: EligibilityType[];
  start_date_min: string | null;
  start_date_max: string | null;
};

export type AnalyticsMetric = {
  key: AnalyticsMetricKey;
  label: string;
  value: number;
  unit: "count" | "percent" | "percentage_points";
  numerator: number;
  denominator: number | null;
  definition: string;
};

export type AnalyticsPerformanceRow = {
  id: string;
  label: string;
  secondary_label: string;
  is_demo: boolean;
  registrations: number;
  approved_participants: number;
  enrollments: number;
  attendance_percentage: number;
  course_completion_rate: number;
  assessment_improvement: number;
  dropout_rate: number;
  certificates_issued: number;
  job_applications: number;
  interviews: number;
  placements: number;
};

export type AnalyticsGeographyRow = {
  state: string;
  registrations: number;
  approved_participants: number;
  enrollments: number;
  certificates_issued: number;
  placements: number;
};

export type AnalyticsDashboard = {
  generated_at: string;
  scope_label: string;
  contains_demo_data: boolean;
  filters: {
    institution_id: string | null;
    programme_id: string | null;
    start_date: string | null;
    end_date: string | null;
    state: string | null;
    gender: string | null;
    participant_category: string | null;
  };
  metrics: AnalyticsMetric[];
  institution_performance: AnalyticsPerformanceRow[];
  programme_performance: AnalyticsPerformanceRow[];
  geographic_distribution: AnalyticsGeographyRow[];
};

export type AnalyticsDrilldown = {
  metric: AnalyticsMetricKey;
  title: string;
  definition: string;
  columns: Array<{ key: string; label: string }>;
  rows: Array<Record<string, string | number | null>>;
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type RegistrationPayload = {
  full_name: string;
  email: string;
  password: string;
  role_code: "trainee" | "nominating_institution" | "employer_recruiter";
  phone?: string;
  organisation_name?: string;
  industry?: string;
  website?: string;
  company_size?: string;
  company_description?: string;
  headquarters?: string;
  registration_number?: string;
  consent_accepted: boolean;
};

export type ProgrammeMode = "online" | "offline" | "hybrid";
export type ProgrammeStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "published"
  | "archived";
export type ApplicationStatus =
  | "submitted"
  | "under_review"
  | "approved"
  | "rejected"
  | "waitlisted"
  | "withdrawn";
export type EligibilityType = "individual" | "pacs" | "shg" | "cooperative_institution";
export type DocumentType = "identity" | "eligibility" | "nomination_letter" | "other";
export type InstitutionType =
  | "ncct"
  | "training_institute"
  | "vamnicom"
  | "ricm"
  | "icm"
  | "pacs"
  | "shg"
  | "dairy_cooperative"
  | "other_cooperative"
  | "nominating_institution"
  | "employer";
export type ProfileDocumentType =
  | "identity"
  | "education"
  | "employment"
  | "membership"
  | "resume"
  | "other";
export type DocumentValidationStatus = "pending" | "verified" | "rejected";

export type InstitutionSummary = {
  id: string;
  name: string;
  code: string;
  institution_type: InstitutionType;
};

export type InstitutionRecord = InstitutionSummary & {
  parent: InstitutionSummary | null;
  state: string | null;
  district: string | null;
  address: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  registration_number: string | null;
  profile_summary: string | null;
  is_active: boolean;
  is_demo: boolean;
  child_count: number;
  children: InstitutionSummary[];
};

export type InstitutionPayload = {
  name: string;
  code: string;
  institution_type: InstitutionType;
  parent_id?: string | null;
  state?: string | null;
  district?: string | null;
  address?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  website?: string | null;
  registration_number?: string | null;
  profile_summary?: string | null;
  is_active?: boolean;
};

export type EducationRecord = {
  id: string;
  qualification: string;
  field_of_study: string | null;
  institution_name: string;
  completion_year: number | null;
  grade: string | null;
  is_highest_qualification: boolean;
};

export type EmploymentRecord = {
  id: string;
  employer_name: string;
  job_title: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  responsibilities: string | null;
};

export type MembershipRecord = {
  id: string;
  institution_name: string;
  membership_type: string;
  member_number: string | null;
  joined_on: string | null;
  is_active: boolean;
};

export type ProfileDocument = {
  id: string;
  document_type: ProfileDocumentType;
  filename: string;
  content_type: string;
  size_bytes: number;
  validation_status: DocumentValidationStatus;
  validation_notes: string | null;
  validated_by_name: string | null;
  validated_at: string | null;
  uploaded_at: string;
};

export type EnrollmentRecord = {
  id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  batch_name: string | null;
  status: "enrolled" | "completed" | "withdrawn";
  enrolled_at: string;
  completed_at: string | null;
  attendance: Array<{
    id: string;
    session_date: string;
    topic: string;
    status: "present" | "absent" | "excused";
  }>;
  assessments: Array<{
    id: string;
    title: string;
    score: number | null;
    maximum_score: number | null;
    result: "passed" | "failed" | "pending";
    assessed_at: string | null;
  }>;
  certificates: Array<{
    id: string;
    certificate_number: string;
    title: string;
    issued_at: string;
  }>;
};

export type AuditEvent = {
  id: string;
  event_type: string;
  success: boolean;
  actor_name: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type TraineeListItem = {
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  institution: InstitutionSummary | null;
  account_status: AccountStatus;
  preferred_language: string | null;
  preferred_location: string | null;
  state: string | null;
  skills: string[];
  completion_percent: number;
  pending_documents: number;
  is_demo: boolean;
};

export type TrainerListItem = {
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  designation: string | null;
  institution: InstitutionSummary | null;
  account_status: AccountStatus;
};

export type TraineeProfile = TraineeListItem & {
  designation: string | null;
  date_of_birth: string | null;
  gender: string | null;
  alternate_email: string | null;
  address_line: string | null;
  city: string | null;
  postal_code: string | null;
  career_interests: string | null;
  completion: {
    percent: number;
    completed_sections: string[];
    missing_sections: string[];
  };
  education: EducationRecord[];
  employment: EmploymentRecord[];
  memberships: MembershipRecord[];
  documents: ProfileDocument[];
  enrollments: EnrollmentRecord[];
  consent_preferences: {
    placement_visibility_consent: boolean;
    communication_consent: boolean;
    data_sharing_consent: boolean;
  };
  audit_history: AuditEvent[];
};

export type PersonalProfilePayload = {
  full_name?: string | null;
  phone?: string | null;
  designation?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  alternate_email?: string | null;
  address_line?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  preferred_language?: string | null;
  preferred_location?: string | null;
  career_interests?: string | null;
  skills?: string[];
};

export type ProgrammeBatch = {
  id: string;
  name: string;
  code: string;
  capacity: number;
  start_date: string;
  end_date: string;
  location: string | null;
  trainers: Array<{
    id: string;
    trainer: { id: string; full_name: string; email: string };
    assigned_at: string;
  }>;
};

export type Programme = {
  id: string;
  institution: { id: string; name: string; code: string };
  title: string;
  code: string;
  summary: string;
  description?: string;
  mode: ProgrammeMode;
  status: ProgrammeStatus;
  eligibility_criteria?: string;
  eligible_applicant_types: EligibilityType[];
  capacity: number;
  available_capacity: number;
  location: string | null;
  language: string;
  duration_days: number;
  application_deadline: string;
  start_date: string;
  end_date: string;
  can_apply: boolean;
  has_applied: boolean;
  rejection_reason?: string | null;
  batches?: ProgrammeBatch[];
  application_count?: number;
  nomination_count?: number;
  approved_count?: number;
};

export type ProgrammePayload = {
  institution_id?: string;
  title: string;
  code: string;
  summary: string;
  description: string;
  mode: ProgrammeMode;
  eligibility_criteria: string;
  eligible_applicant_types: EligibilityType[];
  capacity: number;
  location?: string | null;
  language: string;
  duration_days: number;
  application_deadline: string;
  start_date: string;
  end_date: string;
};

export type AttendanceStatus = "present" | "absent" | "excused";
export type AttendanceSessionStatus = "open" | "closed" | "cancelled";
export type BiometricVerificationStatus = "verified" | "manual_review" | "rejected";

export type AttendanceSession = {
  id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  batch_id: string;
  batch_name: string;
  title: string;
  starts_at: string;
  ends_at: string;
  status: AttendanceSessionStatus;
  check_in_count: number;
};

export type TraineeAttendanceIdentity = {
  trainee_id: string;
  full_name: string;
  identity_code: string;
  qr_payload: string;
};

export type KioskDevice = {
  id: string;
  institution_id: string;
  institution_name: string;
  name: string;
  device_code: string;
  status: "active" | "revoked";
  last_seen_at: string | null;
  created_at: string;
};

export type RegisteredKioskDevice = KioskDevice & { device_token: string };

export type KioskSession = {
  session_id: string;
  title: string;
  programme_title: string;
  programme_code: string;
  batch_name: string;
  starts_at: string;
  ends_at: string;
  offline_until: string;
};

export type OfflineAttendanceEvent = {
  idempotency_key: string;
  session_id: string;
  trainee_qr: string;
  captured_at: string;
};

export type AttendanceSyncItem = {
  idempotency_key: string;
  result: "created" | "duplicate" | "already_checked_in" | "rejected";
  check_in_id: string | null;
  trainee_name: string | null;
  detail: string;
};

export type AttendanceSyncResponse = {
  items: AttendanceSyncItem[];
  accepted: number;
  duplicates: number;
  rejected: number;
};

export type AttendanceReport = {
  session: AttendanceSession;
  expected_count: number;
  present_count: number;
  absent_count: number;
  excused_count: number;
  attendance_percent: number;
  rows: Array<{
    enrollment_id: string;
    trainee_id: string;
    trainee_name: string;
    trainee_email: string;
    status: AttendanceStatus;
    captured_at: string | null;
    checked_in_at: string | null;
    device_code: string | null;
    source: "kiosk" | "manual" | "biometric" | "biometric_manual" | null;
    biometric_enrolled: boolean;
  }>;
};

export type BiometricEnrollment = {
  enrolled: boolean;
  enrolled_at: string | null;
  provider_name: string;
  provider_mode: "demonstration" | "production" | "disabled";
  is_demo: boolean;
  consent_version: string;
  privacy_notice: string;
};

export type BiometricChallenge = {
  id: string;
  challenge_type: "turn_head";
  instruction: string;
  expires_at: string;
  trainee_name: string;
  provider_mode: "demonstration" | "production";
  is_demo: boolean;
};

export type BiometricVerification = {
  id: string;
  trainee_id: string;
  trainee_name: string;
  session_id: string;
  session_title: string;
  status: BiometricVerificationStatus;
  review_status: "pending" | "approved" | "rejected" | null;
  confidence: number;
  threshold: number;
  liveness_score: number;
  attendance_recorded: boolean;
  check_in_id: string | null;
  detail: string;
  captured_at: string;
  created_at: string;
};

export type AttendanceCorrection = {
  id: string;
  attendance_session_id: string;
  session_title: string;
  enrollment_id: string;
  trainee_name: string;
  previous_status: AttendanceStatus | null;
  requested_status: AttendanceStatus;
  reason: string;
  approval_status: "pending" | "approved" | "rejected";
  requested_by_name: string;
  reviewed_by_name: string | null;
  review_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
};

export type CertificateState = "valid" | "revoked" | "expired";

export type CertificateMetrics = {
  course_completion_percent: number;
  attendance_percent: number;
  assessment_score_percent: number;
};

export type EligibilityMetrics = CertificateMetrics & {
  required_lessons: number;
  completed_lessons: number;
  attendance_sessions: number;
  attended_sessions: number;
};

export type CertificatePolicy = {
  id: string;
  programme_id: string;
  configured_by_name: string;
  certificate_title: string;
  minimum_course_completion_percent: number;
  minimum_attendance_percent: number;
  minimum_assessment_score_percent: number;
  validity_days: number | null;
  is_active: boolean;
  updated_at: string;
};

export type CertificateAuditEvent = {
  event_type: string;
  actor_name: string | null;
  details: Record<string, string | number | boolean | null>;
  created_at: string;
};

export type DigitalCertificate = {
  id: string;
  enrollment_id: string;
  certificate_number: string;
  title: string;
  recipient_name: string;
  recipient_email: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  institution_name: string;
  state: CertificateState;
  valid: boolean;
  metrics: CertificateMetrics;
  issued_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  revocation_reason: string | null;
  verification_url: string;
  audit_history: CertificateAuditEvent[];
};

export type CertificateCandidate = {
  enrollment_id: string;
  trainee_name: string;
  trainee_email: string;
  enrollment_status: "enrolled" | "completed" | "withdrawn";
  metrics: EligibilityMetrics;
  eligible: boolean;
  reasons: string[];
  certificate: DigitalCertificate | null;
};

export type SkillWallet = {
  certificates: DigitalCertificate[];
  total: number;
  valid_count: number;
};

export type CertificateVerification = {
  certificate_number: string;
  title: string;
  recipient_name: string;
  programme_title: string;
  institution_name: string;
  state: CertificateState;
  valid: boolean;
  issued_at: string;
  expires_at: string | null;
};

export type ScheduleStatus = "scheduled" | "completed" | "cancelled";
export type BedAllocationStatus = "reserved" | "checked_in" | "checked_out" | "cancelled";
export type MealPreference =
  | "vegetarian"
  | "vegan"
  | "eggetarian"
  | "non_vegetarian"
  | "jain"
  | "other";
export type TransportMode = "self" | "train" | "bus" | "flight" | "institutional" | "other";
export type OperationsIssueType = "maintenance" | "participant";
export type OperationsIssuePriority = "low" | "medium" | "high" | "urgent";
export type OperationsIssueStatus = "open" | "in_progress" | "resolved" | "closed";

export type InstitutionOption = { id: string; name: string; code: string };
export type ProgrammeOption = {
  id: string;
  title: string;
  code: string;
  batches: Array<{ id: string; name: string; code: string }>;
};
export type EnrollmentOption = {
  id: string;
  trainee: { id: string; full_name: string; email: string };
  programme_id: string;
  programme_title: string;
  batch_id: string | null;
  batch_name: string | null;
};
export type Classroom = {
  id: string;
  venue_id: string;
  name: string;
  code: string;
  capacity: number;
  equipment: string | null;
  is_active: boolean;
};
export type TrainingVenue = {
  id: string;
  institution_id: string;
  name: string;
  address: string;
  capacity: number;
  is_active: boolean;
  classrooms: Classroom[];
};
export type TimetableSession = {
  id: string;
  institution_id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  batch_id: string;
  batch_name: string;
  trainer_id: string;
  trainer_name: string;
  venue_id: string;
  venue_name: string;
  classroom_id: string | null;
  classroom_name: string | null;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  status: ScheduleStatus;
};
export type HostelBed = { id: string; bed_number: string; is_active: boolean };
export type HostelRoom = {
  id: string;
  room_number: string;
  floor: string | null;
  capacity: number;
  is_accessible: boolean;
  is_active: boolean;
  beds: HostelBed[];
};
export type HostelBuilding = {
  id: string;
  institution_id: string;
  name: string;
  address: string;
  contact_phone: string | null;
  is_active: boolean;
  rooms: HostelRoom[];
};
export type BedAllocation = {
  id: string;
  bed_id: string;
  bed_number: string;
  room_id: string;
  room_number: string;
  building_id: string;
  building_name: string;
  enrollment_id: string;
  trainee_name: string;
  programme_title: string;
  start_date: string;
  end_date: string;
  status: BedAllocationStatus;
  checked_in_at: string | null;
  checked_out_at: string | null;
};
export type ParticipantLogistics = {
  id: string;
  enrollment_id: string;
  trainee_name: string;
  programme_title: string;
  meal_preference: MealPreference;
  dietary_notes: string | null;
  arrival_mode: TransportMode | null;
  arrival_details: string | null;
  arrival_at: string | null;
  departure_mode: TransportMode | null;
  departure_details: string | null;
  departure_at: string | null;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
};
export type TrainingMaterial = {
  id: string;
  programme_id: string;
  programme_title: string;
  name: string;
  description: string | null;
  quantity_available: number;
  quantity_distributed: number;
  distributions: Array<{
    id: string;
    enrollment_id: string;
    trainee_name: string;
    quantity: number;
    distributed_at: string;
  }>;
};
export type OperationsIssue = {
  id: string;
  institution_id: string;
  enrollment_id: string | null;
  trainee_name: string | null;
  reported_by_name: string;
  issue_type: OperationsIssueType;
  priority: OperationsIssuePriority;
  status: OperationsIssueStatus;
  title: string;
  description: string;
  location: string | null;
  resolution_notes: string | null;
  resolved_by_name: string | null;
  resolved_at: string | null;
  created_at: string;
};
export type OperationsWorkspace = {
  institution: InstitutionOption;
  available_institutions: InstitutionOption[];
  programmes: ProgrammeOption[];
  trainers: Array<{ id: string; full_name: string; email: string }>;
  enrollments: EnrollmentOption[];
  venues: TrainingVenue[];
  timetable: TimetableSession[];
  hostels: HostelBuilding[];
  bed_allocations: BedAllocation[];
  participant_logistics: ParticipantLogistics[];
  materials: TrainingMaterial[];
  issues: OperationsIssue[];
};
export type TraineeProgrammeOperations = {
  enrollment_id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  batch_name: string | null;
  timetable: TimetableSession[];
  logistics: ParticipantLogistics | null;
  accommodation: BedAllocation | null;
  materials: TrainingMaterial[];
  issues: OperationsIssue[];
};
export type TraineeOperations = { programmes: TraineeProgrammeOperations[] };

export type EmployerVerificationStatus = "pending" | "verified" | "rejected";
export type JobStatus = "draft" | "published" | "closed";
export type EmploymentType = "full_time" | "part_time" | "contract" | "internship";
export type WorkplaceMode = "on_site" | "hybrid" | "remote";
export type JobApplicationStatus =
  | "applied"
  | "shortlisted"
  | "interview_scheduled"
  | "interview_completed"
  | "offered"
  | "hired"
  | "rejected"
  | "withdrawn";

export type EmployerProfile = {
  id: string;
  institution_id: string;
  company_name: string;
  institution_code: string;
  contact_name: string;
  contact_email: string;
  industry: string;
  website: string | null;
  company_size: string | null;
  description: string;
  headquarters: string;
  registration_number: string | null;
  verification_status: EmployerVerificationStatus;
  verification_notes: string | null;
  verified_at: string | null;
  updated_at: string;
};

export type EmployerProfilePayload = {
  industry: string;
  website: string | null;
  company_size: string | null;
  description: string;
  headquarters: string;
  registration_number: string | null;
};

export type MatchBreakdown = {
  score: number;
  skill_score: number;
  course_score: number;
  location_score: number;
  interest_score: number;
  reasons: string[];
  gaps: string[];
};

export type Job = {
  id: string;
  employer_profile_id: string;
  company_name: string;
  title: string;
  description: string;
  location: string;
  employment_type: EmploymentType;
  workplace_mode: WorkplaceMode;
  required_skills: string[];
  preferred_skills: string[];
  minimum_experience_years: number;
  vacancies: number;
  salary_minimum: number | null;
  salary_maximum: number | null;
  application_deadline: string | null;
  status: JobStatus;
  published_at: string | null;
  closed_at: string | null;
  required_programmes: Array<{ id: string; code: string; title: string }>;
  saved: boolean;
  application_status: JobApplicationStatus | null;
  match: MatchBreakdown | null;
};

export type JobPayload = {
  title: string;
  description: string;
  location: string;
  employment_type: EmploymentType;
  workplace_mode: WorkplaceMode;
  required_skills: string[];
  preferred_skills: string[];
  minimum_experience_years: number;
  vacancies: number;
  salary_minimum: number | null;
  salary_maximum: number | null;
  application_deadline: string | null;
  required_programme_ids: string[];
};

export type CertificateSummary = {
  id: string;
  certificate_number: string;
  title: string;
  programme_title: string;
  programme_code: string;
  issued_at: string;
  expires_at: string | null;
  verification_url: string;
};

export type Candidate = {
  trainee_id: string;
  full_name: string;
  headline: string | null;
  professional_summary: string | null;
  location: string | null;
  verified_skills: string[];
  career_interests: string[];
  certificates: CertificateSummary[];
  contact: { email: string; phone: string | null } | null;
  contact_locked_reason: string | null;
  resume_available: boolean;
  resume_download_allowed: boolean;
  shortlisted: boolean;
  match: MatchBreakdown | null;
};

export type EmploymentProfile = {
  trainee_id: string;
  full_name: string;
  headline: string | null;
  professional_summary: string | null;
  preferred_roles: string[];
  preferred_locations: string[];
  open_to_work: boolean;
  location: string | null;
  career_interests: string[];
  placement_visibility_consent: boolean;
  data_sharing_consent: boolean;
  verified_skills: Array<{
    name: string;
    certificate_id: string;
    certificate_number: string;
  }>;
  resume_filename: string | null;
  resume_size_bytes: number | null;
  resume_uploaded_at: string | null;
};

export type EmploymentProfilePayload = {
  headline: string | null;
  professional_summary: string | null;
  preferred_roles: string[];
  preferred_locations: string[];
  open_to_work: boolean;
};

export type JobApplication = {
  id: string;
  job_id: string;
  job_title: string;
  company_name: string;
  trainee_id: string;
  trainee_name: string;
  status: JobApplicationStatus;
  cover_note: string | null;
  applied_at: string;
  status_updated_at: string;
  interview_at: string | null;
  interview_mode: string | null;
  interview_details: string | null;
  employer_notes: string | null;
  certificates: CertificateSummary[];
  contact: { email: string; phone: string | null } | null;
};

export type EmployerWorkspace = {
  profile: EmployerProfile;
  jobs: Job[];
  applications: JobApplication[];
  shortlisted_count: number;
};

export type TraineeEmploymentWorkspace = {
  profile: EmploymentProfile;
  recommendations: Job[];
  saved_jobs: Job[];
  applications: JobApplication[];
};

export type ParticipantLogisticsPayload = {
  meal_preference: MealPreference;
  dietary_notes: string | null;
  arrival_mode: TransportMode | null;
  arrival_details: string | null;
  arrival_at: string | null;
  departure_mode: TransportMode | null;
  departure_details: string | null;
  departure_at: string | null;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
};

export type OperationsIssuePayload = {
  institution_id?: string | null;
  enrollment_id?: string | null;
  issue_type: OperationsIssueType;
  priority?: OperationsIssuePriority;
  title: string;
  description: string;
  location?: string | null;
};

export type SubmissionDocument = {
  id: string;
  document_type: DocumentType;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
};

export type ProgrammeApplication = {
  id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  trainee_id: string;
  trainee_name: string;
  trainee_email: string;
  status: ApplicationStatus;
  statement: string | null;
  review_notes: string | null;
  submitted_at: string;
  reviewed_at: string | null;
  documents: SubmissionDocument[];
};

export type ProgrammeNomination = {
  id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  nominating_institution: { id: string; name: string; code: string };
  nomination_type: EligibilityType;
  source: "individual" | "bulk_csv";
  candidate_full_name: string;
  candidate_email: string;
  candidate_phone: string | null;
  member_identifier: string | null;
  status: ApplicationStatus;
  review_notes: string | null;
  submitted_at: string;
  reviewed_at: string | null;
  documents: SubmissionDocument[];
};

export type CourseStatus = "draft" | "published" | "archived";
export type LessonType = "video" | "audio" | "pdf" | "text" | "external_resource";
export type LearningProgressStatus = "not_started" | "in_progress" | "completed";
export type AssessmentType = "quiz" | "pre_training" | "post_training";
export type AssessmentAttemptStatus = "in_progress" | "submitted";
export type AssignmentSubmissionStatus =
  | "submitted"
  | "reviewed"
  | "resubmission_requested";

export type CourseLanguage = { id: string; code: string; name: string };

export type LessonProgress = {
  status: LearningProgressStatus;
  last_position_seconds: number;
  viewed_seconds: number;
  completed_at: string | null;
};

export type LearningProgressEvent = {
  idempotency_key: string;
  lesson_id: string;
  action: "start" | "heartbeat" | "complete";
  captured_at: string;
  position_seconds?: number;
  elapsed_seconds?: number;
};

export type LearningProgressSyncItem = {
  idempotency_key: string;
  lesson_id: string;
  result: "applied" | "duplicate" | "rejected";
  detail: string;
  progress: LessonProgress | null;
};

export type LearningProgressSyncResponse = {
  items: LearningProgressSyncItem[];
  applied: number;
  duplicates: number;
  rejected: number;
};

export type LessonContent = {
  id: string;
  language_code: string;
  title: string;
  text_content: string | null;
  external_url: string | null;
  filename: string | null;
  content_type: string | null;
  size_bytes: number | null;
  has_asset: boolean;
};

export type CourseLesson = {
  id: string;
  title: string;
  lesson_type: LessonType;
  position: number;
  duration_seconds: number | null;
  is_required: boolean;
  contents: LessonContent[];
  progress: LessonProgress;
};

export type CourseModule = {
  id: string;
  title: string;
  description: string | null;
  position: number;
  lessons: CourseLesson[];
};

export type CourseSection = {
  id: string;
  title: string;
  position: number;
  modules: CourseModule[];
};

export type AssignmentSubmission = {
  id: string;
  enrollment_id: string;
  trainee_name: string;
  submission_number: number;
  status: AssignmentSubmissionStatus;
  filename: string;
  content_type: string;
  size_bytes: number;
  submitted_at: string;
  score: number | null;
  trainer_feedback: string | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
};

export type CourseAssignment = {
  id: string;
  module_id: string | null;
  title: string;
  instructions: string;
  due_at: string | null;
  max_score: number;
  allowed_content_types: string[];
  is_published: boolean;
  latest_submission: AssignmentSubmission | null;
};

export type AssessmentSummary = {
  id: string;
  title: string;
  instructions: string | null;
  assessment_type: AssessmentType;
  attempt_limit: number;
  attempts_used: number;
  attempts_remaining: number;
  passing_score_percent: number;
  best_score_percent: number | null;
  passed: boolean;
  is_published: boolean;
};

export type CourseListItem = {
  id: string;
  programme_id: string;
  programme_title: string;
  programme_code: string;
  title: string;
  summary: string;
  status: CourseStatus;
  languages: CourseLanguage[];
  lesson_count: number;
  completed_lesson_count: number;
  progress_percent: number;
  resume_lesson_id: string | null;
  resume_position_seconds: number;
  can_manage: boolean;
};

export type CourseDetail = CourseListItem & {
  default_language_code: string;
  sections: CourseSection[];
  assignments: CourseAssignment[];
  assessments: AssessmentSummary[];
};

export type QuestionBank = {
  id: string;
  title: string;
  description: string | null;
  questions: Array<{
    id: string;
    prompt: string;
    choices: string[];
    correct_option_index: number;
    explanation: string | null;
    points: number;
    position: number;
  }>;
};

export type AssessmentAttempt = {
  id: string;
  assessment_id: string;
  assessment_title: string;
  attempt_number: number;
  status: AssessmentAttemptStatus;
  questions: Array<{
    id: string;
    prompt: string;
    choices: string[];
    points: number;
    position: number;
  }>;
  score_percent: number | null;
  points_earned: number | null;
  points_available: number | null;
  passed: boolean | null;
  grading_details: Array<{
    question_id: string;
    selected_option_index: number | null;
    correct: boolean;
    points_earned: number;
    explanation: string | null;
  }>;
  trainer_feedback: string | null;
  started_at: string;
  submitted_at: string | null;
};

export type CareerLanguage = "en" | "hi" | "te";
export type CareerConversationStatus = "active" | "escalated" | "closed";
export type CareerFeedbackRating = "helpful" | "not_helpful";

export type CareerSource = {
  source_type: "faq" | "programme" | "job";
  record_id: string;
  title: string;
  url: string;
  summary: string;
};

export type CareerFeedback = {
  id: string;
  rating: CareerFeedbackRating;
  comment: string | null;
};

export type CareerMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: CareerSource[];
  provider: string | null;
  created_at: string;
  feedback: CareerFeedback | null;
};

export type CareerEscalation = {
  id: string;
  conversation_id: string;
  requested_by_id: string;
  requester_name: string;
  requester_email: string;
  reason: string;
  status: "open" | "resolved";
  resolution_notes: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type CareerConversationSummary = {
  id: string;
  language: CareerLanguage;
  title: string;
  status: CareerConversationStatus;
  last_message_at: string;
  created_at: string;
};

export type CareerConversation = CareerConversationSummary & {
  messages: CareerMessage[];
  escalation: CareerEscalation | null;
};

export type CareerMessageExchange = {
  user_message: CareerMessage;
  assistant_message: CareerMessage;
  used_local_fallback: boolean;
};

export type AssistantChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type AssistantChatResponse = {
  answer: string;
  provider: string;
  used_local_fallback: boolean;
};

const defaultBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetcher?: typeof fetch;
  private accessToken: string | null = null;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? defaultBaseUrl;
    this.fetcher = options.fetcher;
  }

  setAccessToken(accessToken: string | null) {
    this.accessToken = accessToken;
  }

  health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/api/v1/health");
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const auth = await this.request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.accessToken = auth.access_token;
    return auth;
  }

  async refresh(): Promise<AuthResponse> {
    const auth = await this.request<AuthResponse>("/api/v1/auth/refresh", { method: "POST" });
    this.accessToken = auth.access_token;
    return auth;
  }

  async logout(): Promise<void> {
    try {
      await this.request<{ message: string }>(
        "/api/v1/auth/logout",
        { method: "POST" },
        true,
      );
    } finally {
      this.accessToken = null;
    }
  }

  me(): Promise<User> {
    return this.request<User>("/api/v1/auth/me", {}, true);
  }

  dashboard(): Promise<DashboardResponse> {
    return this.request<DashboardResponse>("/api/v1/dashboard", {}, true);
  }

  notifications(): Promise<{ items: NotificationItem[]; unread_count: number }> {
    return this.request("/api/v1/notifications", {}, true);
  }

  markNotificationRead(id: string): Promise<NotificationItem> {
    return this.request<NotificationItem>(
      `/api/v1/notifications/${id}/read`,
      { method: "PATCH" },
      true,
    );
  }

  sendNotification(payload: {
    target_type: NotificationTargetType;
    target_ids: string[];
    title: string;
    description: string;
  }): Promise<{ id: string; sent_count: number }> {
    return this.request(
      "/api/v1/notifications",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  analyticsOptions(): Promise<AnalyticsFilterOptions> {
    return this.request<AnalyticsFilterOptions>("/api/v1/analytics/options", {}, true);
  }

  analyticsDashboard(filters: AnalyticsFilters = {}): Promise<AnalyticsDashboard> {
    const query = this.analyticsQuery(filters);
    return this.request<AnalyticsDashboard>(`/api/v1/analytics/dashboard${query}`, {}, true);
  }

  analyticsDrilldown(
    metric: AnalyticsMetricKey,
    filters: AnalyticsFilters = {},
    page = 1,
  ): Promise<AnalyticsDrilldown> {
    const query = this.analyticsQuery({ ...filters, page });
    return this.request<AnalyticsDrilldown>(
      `/api/v1/analytics/drilldown/${metric}${query}`,
      {},
      true,
    );
  }

  analyticsCsv(
    view: "institution" | "programme" | "geography",
    filters: AnalyticsFilters = {},
  ): Promise<Blob> {
    const query = this.analyticsQuery({ ...filters, view });
    return this.download(`/api/v1/analytics/export${query}`);
  }

  certificatePolicy(programmeId: string): Promise<CertificatePolicy | null> {
    return this.request(
      `/api/v1/certificates/programmes/${programmeId}/policy`,
      {},
      true,
    );
  }

  configureCertificatePolicy(
    programmeId: string,
    payload: {
      certificate_title: string;
      minimum_course_completion_percent: number;
      minimum_attendance_percent: number;
      minimum_assessment_score_percent: number;
      validity_days: number | null;
      is_active: boolean;
    },
  ): Promise<CertificatePolicy> {
    return this.request(
      `/api/v1/certificates/programmes/${programmeId}/policy`,
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  certificateCandidates(programmeId: string): Promise<CertificateCandidate[]> {
    return this.request(
      `/api/v1/certificates/candidates?programme_id=${encodeURIComponent(programmeId)}`,
      {},
      true,
    );
  }

  issueCertificate(enrollmentId: string): Promise<DigitalCertificate> {
    return this.request(
      "/api/v1/certificates/issue",
      { method: "POST", body: JSON.stringify({ enrollment_id: enrollmentId }) },
      true,
    );
  }

  certificates(programmeId?: string): Promise<DigitalCertificate[]> {
    const query = programmeId ? `?programme_id=${encodeURIComponent(programmeId)}` : "";
    return this.request(`/api/v1/certificates${query}`, {}, true);
  }

  revokeCertificate(id: string, reason: string): Promise<DigitalCertificate> {
    return this.request(
      `/api/v1/certificates/${id}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) },
      true,
    );
  }

  skillWallet(): Promise<SkillWallet> {
    return this.request("/api/v1/certificates/wallet/me", {}, true);
  }

  verifyCertificate(token: string): Promise<CertificateVerification> {
    return this.request(
      `/api/v1/certificates/verify/${encodeURIComponent(token)}`,
    );
  }

  downloadCertificate(id: string): Promise<Blob> {
    return this.download(`/api/v1/certificates/${id}/download`);
  }

  adminEmployers(status?: EmployerVerificationStatus): Promise<EmployerProfile[]> {
    const query = status ? `?verification_status=${encodeURIComponent(status)}` : "";
    return this.request(`/api/v1/employment/admin/employers${query}`, {}, true);
  }

  verifyEmployer(
    id: string,
    payload: { status: Exclude<EmployerVerificationStatus, "pending">; notes?: string },
  ): Promise<EmployerProfile> {
    return this.request(
      `/api/v1/employment/admin/employers/${id}/verification`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  employerWorkspace(): Promise<EmployerWorkspace> {
    return this.request("/api/v1/employment/employer/workspace", {}, true);
  }

  updateEmployerProfile(payload: EmployerProfilePayload): Promise<EmployerProfile> {
    return this.request(
      "/api/v1/employment/employer/profile",
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  createJob(payload: JobPayload): Promise<Job> {
    return this.request(
      "/api/v1/employment/employer/jobs",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateJob(id: string, payload: JobPayload): Promise<Job> {
    return this.request(
      `/api/v1/employment/employer/jobs/${id}`,
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  publishJob(id: string): Promise<Job> {
    return this.request(
      `/api/v1/employment/employer/jobs/${id}/publish`,
      { method: "POST" },
      true,
    );
  }

  closeJob(id: string): Promise<Job> {
    return this.request(
      `/api/v1/employment/employer/jobs/${id}/close`,
      { method: "POST" },
      true,
    );
  }

  searchCandidates(filters: {
    job_id?: string;
    skill?: string;
    course_id?: string;
    certificate_number?: string;
    location?: string;
  }): Promise<Candidate[]> {
    const query = new URLSearchParams(
      Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1])),
    );
    return this.request(`/api/v1/employment/employer/candidates?${query}`, {}, true);
  }

  shortlistCandidate(jobId: string, traineeId: string, notes?: string): Promise<Candidate> {
    return this.request(
      `/api/v1/employment/employer/jobs/${jobId}/shortlist`,
      { method: "POST", body: JSON.stringify({ trainee_id: traineeId, notes: notes || null }) },
      true,
    );
  }

  candidateResume(traineeId: string): Promise<Blob> {
    return this.download(`/api/v1/employment/employer/candidates/${traineeId}/resume`);
  }

  updateJobApplication(
    id: string,
    payload: {
      status: Exclude<JobApplicationStatus, "applied" | "withdrawn">;
      interview_at?: string | null;
      interview_mode?: string | null;
      interview_details?: string | null;
      employer_notes?: string | null;
    },
  ): Promise<JobApplication> {
    return this.request(
      `/api/v1/employment/employer/applications/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  traineeEmploymentWorkspace(): Promise<TraineeEmploymentWorkspace> {
    return this.request("/api/v1/employment/me/workspace", {}, true);
  }

  updateEmploymentProfile(payload: EmploymentProfilePayload): Promise<EmploymentProfile> {
    return this.request(
      "/api/v1/employment/me/profile",
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  uploadEmploymentResume(file: File): Promise<EmploymentProfile> {
    const body = new FormData();
    body.set("file", file);
    return this.request(
      "/api/v1/employment/me/resume",
      { method: "POST", body },
      true,
    );
  }

  searchJobs(filters: {
    query?: string;
    location?: string;
    skill?: string;
    programme_id?: string;
  } = {}): Promise<Job[]> {
    const query = new URLSearchParams(
      Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1])),
    );
    const suffix = query.size ? `?${query}` : "";
    return this.request(`/api/v1/employment/jobs${suffix}`, {}, true);
  }

  jobRecommendations(): Promise<Job[]> {
    return this.request("/api/v1/employment/jobs/recommendations", {}, true);
  }

  saveJob(id: string): Promise<Job> {
    return this.request(
      `/api/v1/employment/jobs/${id}/save`,
      { method: "POST" },
      true,
    );
  }

  unsaveJob(id: string): Promise<{ message: string }> {
    return this.request(
      `/api/v1/employment/jobs/${id}/save`,
      { method: "DELETE" },
      true,
    );
  }

  applyForJob(id: string, coverNote?: string): Promise<JobApplication> {
    return this.request(
      `/api/v1/employment/jobs/${id}/apply`,
      { method: "POST", body: JSON.stringify({ cover_note: coverNote || null }) },
      true,
    );
  }

  withdrawJobApplication(id: string): Promise<JobApplication> {
    return this.request(
      `/api/v1/employment/me/applications/${id}/withdraw`,
      { method: "POST" },
      true,
    );
  }

  operationsWorkspace(institutionId?: string): Promise<OperationsWorkspace> {
    const query = institutionId
      ? `?institution_id=${encodeURIComponent(institutionId)}`
      : "";
    return this.request(`/api/v1/operations/workspace${query}`, {}, true);
  }

  myOperations(): Promise<TraineeOperations> {
    return this.request("/api/v1/operations/me", {}, true);
  }

  createVenue(payload: {
    institution_id: string;
    name: string;
    address: string;
    capacity: number;
  }): Promise<TrainingVenue> {
    return this.request(
      "/api/v1/operations/venues",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  createClassroom(payload: {
    venue_id: string;
    name: string;
    code: string;
    capacity: number;
    equipment: string | null;
  }): Promise<Classroom> {
    return this.request(
      "/api/v1/operations/classrooms",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  createTimetableSession(payload: {
    programme_id: string;
    batch_id: string;
    trainer_id: string;
    venue_id: string;
    classroom_id: string | null;
    title: string;
    description: string | null;
    starts_at: string;
    ends_at: string;
  }): Promise<TimetableSession> {
    return this.request(
      "/api/v1/operations/timetable",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateTimetableSession(
    id: string,
    payload: Partial<{
      trainer_id: string;
      venue_id: string;
      classroom_id: string | null;
      title: string;
      description: string | null;
      starts_at: string;
      ends_at: string;
      status: ScheduleStatus;
    }>,
  ): Promise<TimetableSession> {
    return this.request(
      `/api/v1/operations/timetable/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  createHostel(payload: {
    institution_id: string;
    name: string;
    address: string;
    contact_phone: string | null;
  }): Promise<HostelBuilding> {
    return this.request(
      "/api/v1/operations/hostels",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  createHostelRoom(
    buildingId: string,
    payload: {
      room_number: string;
      floor: string | null;
      capacity: number;
      bed_numbers: string[];
      is_accessible: boolean;
    },
  ): Promise<HostelRoom> {
    return this.request(
      `/api/v1/operations/hostels/${buildingId}/rooms`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  allocateBed(payload: {
    bed_id: string;
    enrollment_id: string;
    start_date: string;
    end_date: string;
  }): Promise<BedAllocation> {
    return this.request(
      "/api/v1/operations/bed-allocations",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  checkInBed(id: string): Promise<BedAllocation> {
    return this.request(
      `/api/v1/operations/bed-allocations/${id}/check-in`,
      { method: "POST" },
      true,
    );
  }

  checkOutBed(id: string): Promise<BedAllocation> {
    return this.request(
      `/api/v1/operations/bed-allocations/${id}/check-out`,
      { method: "POST" },
      true,
    );
  }

  updateParticipantLogistics(
    enrollmentId: string,
    payload: ParticipantLogisticsPayload,
  ): Promise<ParticipantLogistics> {
    return this.request(
      `/api/v1/operations/enrollments/${enrollmentId}/logistics`,
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  createTrainingMaterial(payload: {
    programme_id: string;
    name: string;
    description: string | null;
    quantity_available: number;
  }): Promise<TrainingMaterial> {
    return this.request(
      "/api/v1/operations/materials",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  distributeTrainingMaterial(
    materialId: string,
    payload: { enrollment_id: string; quantity: number },
  ): Promise<TrainingMaterial> {
    return this.request(
      `/api/v1/operations/materials/${materialId}/distributions`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  reportMyOperationsIssue(payload: OperationsIssuePayload): Promise<OperationsIssue> {
    return this.request(
      "/api/v1/operations/issues/me",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  createOperationsIssue(payload: OperationsIssuePayload): Promise<OperationsIssue> {
    return this.request(
      "/api/v1/operations/issues",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateOperationsIssue(
    id: string,
    payload: { status: OperationsIssueStatus; resolution_notes: string | null },
  ): Promise<OperationsIssue> {
    return this.request(
      `/api/v1/operations/issues/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  attendanceIdentity(): Promise<TraineeAttendanceIdentity> {
    return this.request("/api/v1/attendance/identity/me", {}, true);
  }

  biometricEnrollment(): Promise<BiometricEnrollment> {
    return this.request("/api/v1/attendance/biometrics/enrollment/me", {}, true);
  }

  createBiometricEnrollmentChallenge(): Promise<BiometricChallenge> {
    return this.request(
      "/api/v1/attendance/biometrics/enrollment/challenge",
      { method: "POST" },
      true,
    );
  }

  enrollBiometric(challengeId: string, frames: Blob[]): Promise<BiometricEnrollment> {
    const body = new FormData();
    body.append("challenge_id", challengeId);
    body.append("consent_granted", "true");
    frames.forEach((frame, index) => body.append("frames", frame, `face-frame-${index + 1}.jpg`));
    return this.request(
      "/api/v1/attendance/biometrics/enrollment",
      { method: "POST", body },
      true,
    );
  }

  deleteMyBiometricEnrollment(): Promise<{ message: string }> {
    return this.request(
      "/api/v1/attendance/biometrics/enrollment/me",
      { method: "DELETE" },
      true,
    );
  }

  deleteTraineeBiometricEnrollment(traineeId: string): Promise<{ message: string }> {
    return this.request(
      `/api/v1/attendance/biometrics/enrollments/${traineeId}`,
      { method: "DELETE" },
      true,
    );
  }

  biometricReviews(): Promise<BiometricVerification[]> {
    return this.request("/api/v1/attendance/biometrics/reviews", {}, true);
  }

  reviewBiometric(
    verificationId: string,
    decision: "approved" | "rejected",
    reviewNotes: string,
  ): Promise<BiometricVerification> {
    return this.request(
      `/api/v1/attendance/biometrics/reviews/${verificationId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ decision, review_notes: reviewNotes }),
      },
      true,
    );
  }

  attendanceSessions(): Promise<AttendanceSession[]> {
    return this.request("/api/v1/attendance/sessions", {}, true);
  }

  createAttendanceSession(payload: {
    programme_id: string;
    batch_id: string;
    title: string;
    starts_at: string;
    ends_at: string;
  }): Promise<AttendanceSession> {
    return this.request(
      "/api/v1/attendance/sessions",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateAttendanceSession(
    id: string,
    payload: Partial<{ title: string; status: AttendanceSessionStatus }>,
  ): Promise<AttendanceSession> {
    return this.request(
      `/api/v1/attendance/sessions/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  attendanceSessionQr(id: string): Promise<{
    payload: string;
    expires_at: string;
    refresh_after_seconds: number;
  }> {
    return this.request(`/api/v1/attendance/sessions/${id}/qr`, {}, true);
  }

  attendanceReport(id: string): Promise<AttendanceReport> {
    return this.request(`/api/v1/attendance/sessions/${id}/report`, {}, true);
  }

  kioskDevices(): Promise<KioskDevice[]> {
    return this.request("/api/v1/attendance/devices", {}, true);
  }

  registerKioskDevice(payload: {
    name: string;
    institution_id?: string;
  }): Promise<RegisteredKioskDevice> {
    return this.request(
      "/api/v1/attendance/devices",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  revokeKioskDevice(id: string): Promise<KioskDevice> {
    return this.request(
      `/api/v1/attendance/devices/${id}/revoke`,
      { method: "POST" },
      true,
    );
  }

  attendanceCorrections(): Promise<AttendanceCorrection[]> {
    return this.request("/api/v1/attendance/corrections", {}, true);
  }

  requestAttendanceCorrection(
    sessionId: string,
    payload: { enrollment_id: string; requested_status: AttendanceStatus; reason: string },
  ): Promise<AttendanceCorrection> {
    return this.request(
      `/api/v1/attendance/sessions/${sessionId}/corrections`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  reviewAttendanceCorrection(
    id: string,
    decision: "approved" | "rejected",
    reviewNotes?: string,
  ): Promise<AttendanceCorrection> {
    return this.request(
      `/api/v1/attendance/corrections/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify({ decision, review_notes: reviewNotes || null }),
      },
      true,
    );
  }

  pairKiosk(deviceToken: string, sessionQr: string): Promise<KioskSession> {
    return this.request("/api/v1/attendance/kiosk/pair", {
      method: "POST",
      body: JSON.stringify({ session_qr: sessionQr }),
      headers: { "X-Kiosk-Token": deviceToken },
    });
  }

  syncKioskAttendance(
    deviceToken: string,
    items: OfflineAttendanceEvent[],
  ): Promise<AttendanceSyncResponse> {
    return this.request("/api/v1/attendance/kiosk/check-ins/sync", {
      method: "POST",
      body: JSON.stringify({ items }),
      headers: { "X-Kiosk-Token": deviceToken },
    });
  }

  createKioskBiometricChallenge(
    deviceToken: string,
    sessionId: string,
    identityCode: string,
  ): Promise<BiometricChallenge> {
    return this.request("/api/v1/attendance/kiosk/biometrics/challenge", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, identity_code: identityCode }),
      headers: { "X-Kiosk-Token": deviceToken },
    });
  }

  verifyKioskBiometric(
    deviceToken: string,
    challengeId: string,
    frames: Blob[],
  ): Promise<BiometricVerification> {
    const body = new FormData();
    body.append("challenge_id", challengeId);
    body.append("idempotency_key", crypto.randomUUID());
    body.append("captured_at", new Date().toISOString());
    frames.forEach((frame, index) => body.append("frames", frame, `face-frame-${index + 1}.jpg`));
    return this.request("/api/v1/attendance/kiosk/biometrics/verify", {
      method: "POST",
      body,
      headers: { "X-Kiosk-Token": deviceToken },
    });
  }

  courses(): Promise<{ items: CourseListItem[]; total: number }> {
    return this.request("/api/v1/learning/courses", {}, true);
  }

  course(id: string): Promise<CourseDetail> {
    return this.request<CourseDetail>(`/api/v1/learning/courses/${id}`, {}, true);
  }

  createCourse(payload: {
    programme_id: string;
    title: string;
    summary: string;
    default_language_code: string;
  }): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      "/api/v1/learning/courses",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateCourse(
    id: string,
    payload: Partial<{
      title: string;
      summary: string;
      status: CourseStatus;
      default_language_code: string;
    }>,
  ): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      `/api/v1/learning/courses/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  addCourseLanguage(id: string, code: string, name: string): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      `/api/v1/learning/courses/${id}/languages`,
      { method: "POST", body: JSON.stringify({ code, name }) },
      true,
    );
  }

  addCourseSection(id: string, title: string, position: number): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      `/api/v1/learning/courses/${id}/sections`,
      { method: "POST", body: JSON.stringify({ title, position }) },
      true,
    );
  }

  addCourseModule(
    sectionId: string,
    payload: { title: string; description?: string; position: number },
  ): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      `/api/v1/learning/sections/${sectionId}/modules`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  addCourseLesson(
    moduleId: string,
    payload: {
      title: string;
      lesson_type: LessonType;
      position: number;
      duration_seconds?: number;
      is_required: boolean;
    },
  ): Promise<CourseDetail> {
    return this.request<CourseDetail>(
      `/api/v1/learning/modules/${moduleId}/lessons`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  putLessonContent(
    lessonId: string,
    payload: {
      language_code: string;
      title: string;
      text_content?: string;
      external_url?: string;
      file?: File;
    },
  ): Promise<LessonContent> {
    const body = new FormData();
    body.set("language_code", payload.language_code);
    body.set("title", payload.title);
    if (payload.text_content) body.set("text_content", payload.text_content);
    if (payload.external_url) body.set("external_url", payload.external_url);
    if (payload.file) body.set("file", payload.file);
    return this.request<LessonContent>(
      `/api/v1/learning/lessons/${lessonId}/content`,
      { method: "PUT", body },
      true,
    );
  }

  startLesson(lessonId: string): Promise<LessonProgress> {
    return this.request<LessonProgress>(
      `/api/v1/learning/lessons/${lessonId}/start`,
      { method: "POST" },
      true,
    );
  }

  heartbeatLesson(
    lessonId: string,
    positionSeconds: number,
    elapsedSeconds: number,
  ): Promise<LessonProgress> {
    return this.request<LessonProgress>(
      `/api/v1/learning/lessons/${lessonId}/heartbeat`,
      {
        method: "POST",
        body: JSON.stringify({
          position_seconds: Math.max(0, Math.floor(positionSeconds)),
          elapsed_seconds: Math.min(30, Math.max(1, Math.floor(elapsedSeconds))),
        }),
      },
      true,
    );
  }

  completeLesson(lessonId: string): Promise<LessonProgress> {
    return this.request<LessonProgress>(
      `/api/v1/learning/lessons/${lessonId}/complete`,
      { method: "POST" },
      true,
    );
  }

  syncLessonProgress(events: LearningProgressEvent[]): Promise<LearningProgressSyncResponse> {
    return this.request<LearningProgressSyncResponse>(
      "/api/v1/learning/progress/sync",
      { method: "POST", body: JSON.stringify({ events }) },
      true,
    );
  }

  lessonAsset(contentId: string): Promise<Blob> {
    return this.download(`/api/v1/learning/content/${contentId}/asset`);
  }

  createAssignment(
    courseId: string,
    payload: {
      module_id?: string;
      title: string;
      instructions: string;
      max_score: number;
      allowed_content_types: string[];
      is_published: boolean;
    },
  ): Promise<CourseAssignment> {
    return this.request<CourseAssignment>(
      `/api/v1/learning/courses/${courseId}/assignments`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  submitAssignment(assignmentId: string, file: File): Promise<AssignmentSubmission> {
    const body = new FormData();
    body.set("file", file);
    return this.request<AssignmentSubmission>(
      `/api/v1/learning/assignments/${assignmentId}/submissions`,
      { method: "POST", body },
      true,
    );
  }

  assignmentSubmissions(assignmentId: string): Promise<AssignmentSubmission[]> {
    return this.request(
      `/api/v1/learning/assignments/${assignmentId}/submissions`,
      {},
      true,
    );
  }

  reviewAssignment(
    submissionId: string,
    payload: {
      score?: number;
      trainer_feedback: string;
      status: Exclude<AssignmentSubmissionStatus, "submitted">;
    },
  ): Promise<AssignmentSubmission> {
    return this.request<AssignmentSubmission>(
      `/api/v1/learning/submissions/${submissionId}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  questionBanks(courseId: string): Promise<QuestionBank[]> {
    return this.request(`/api/v1/learning/courses/${courseId}/question-banks`, {}, true);
  }

  createQuestionBank(
    courseId: string,
    payload: { title: string; description?: string },
  ): Promise<QuestionBank> {
    return this.request<QuestionBank>(
      `/api/v1/learning/courses/${courseId}/question-banks`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  addQuestion(
    bankId: string,
    payload: {
      prompt: string;
      choices: string[];
      correct_option_index: number;
      explanation?: string;
      points: number;
      position: number;
    },
  ): Promise<QuestionBank> {
    return this.request<QuestionBank>(
      `/api/v1/learning/question-banks/${bankId}/questions`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  createAssessment(
    courseId: string,
    payload: {
      question_bank_id: string;
      title: string;
      instructions?: string;
      assessment_type: AssessmentType;
      attempt_limit: number;
      passing_score_percent: number;
      is_published: boolean;
    },
  ): Promise<AssessmentSummary> {
    return this.request<AssessmentSummary>(
      `/api/v1/learning/courses/${courseId}/assessments`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  startAssessment(assessmentId: string): Promise<AssessmentAttempt> {
    return this.request<AssessmentAttempt>(
      `/api/v1/learning/assessments/${assessmentId}/attempts`,
      { method: "POST" },
      true,
    );
  }

  assessmentAttempts(assessmentId: string): Promise<AssessmentAttempt[]> {
    return this.request(
      `/api/v1/learning/assessments/${assessmentId}/attempts`,
      {},
      true,
    );
  }

  assessmentAttempt(attemptId: string): Promise<AssessmentAttempt> {
    return this.request(`/api/v1/learning/attempts/${attemptId}`, {}, true);
  }

  submitAssessment(
    attemptId: string,
    answers: Array<{ question_id: string; option_index: number }>,
  ): Promise<AssessmentAttempt> {
    return this.request<AssessmentAttempt>(
      `/api/v1/learning/attempts/${attemptId}/submit`,
      { method: "POST", body: JSON.stringify({ answers }) },
      true,
    );
  }

  addAssessmentFeedback(attemptId: string, trainerFeedback: string) {
    return this.request<AssessmentAttempt>(
      `/api/v1/learning/attempts/${attemptId}/feedback`,
      { method: "PATCH", body: JSON.stringify({ trainer_feedback: trainerFeedback }) },
      true,
    );
  }

  programmes(filters: {
    q?: string;
    status?: ProgrammeStatus;
    mode?: ProgrammeMode;
    language?: string;
    institution_id?: string;
  } = {}): Promise<{ items: Programme[]; total: number }> {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) search.set(key, value);
    });
    const suffix = search.size ? `?${search.toString()}` : "";
    return this.request<{ items: Programme[]; total: number }>(
      `/api/v1/programmes${suffix}`,
      {},
      true,
    );
  }

  programme(id: string): Promise<Programme> {
    return this.request<Programme>(`/api/v1/programmes/${id}`, {}, true);
  }

  createProgramme(payload: ProgrammePayload): Promise<Programme> {
    return this.request<Programme>(
      "/api/v1/programmes",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateProgramme(id: string, payload: Partial<ProgrammePayload>): Promise<Programme> {
    return this.request<Programme>(
      `/api/v1/programmes/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  transitionProgramme(
    id: string,
    transition: "submit" | "approve" | "reject" | "publish" | "archive",
    reason?: string,
  ): Promise<Programme> {
    return this.request<Programme>(
      `/api/v1/programmes/${id}/${transition}`,
      { method: "POST", body: reason === undefined ? undefined : JSON.stringify({ reason }) },
      true,
    );
  }

  createBatch(
    programmeId: string,
    payload: {
      name: string;
      code: string;
      capacity: number;
      start_date: string;
      end_date: string;
      location?: string;
    },
  ): Promise<ProgrammeBatch> {
    return this.request<ProgrammeBatch>(
      `/api/v1/programmes/${programmeId}/batches`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  trainers(): Promise<Array<{ id: string; full_name: string; email: string }>> {
    return this.request<Array<{ id: string; full_name: string; email: string }>>(
      "/api/v1/programmes/trainers",
      {},
      true,
    );
  }

  trainingInstitutions(): Promise<Array<{ id: string; name: string; code: string }>> {
    return this.request<Array<{ id: string; name: string; code: string }>>(
      "/api/v1/programmes/institutions",
      {},
      true,
    );
  }

  assignTrainer(batchId: string, trainerId: string): Promise<ProgrammeBatch["trainers"][number]> {
    return this.request<ProgrammeBatch["trainers"][number]>(
      `/api/v1/programmes/batches/${batchId}/trainers`,
      { method: "POST", body: JSON.stringify({ trainer_id: trainerId }) },
      true,
    );
  }

  applications(programmeId?: string): Promise<ProgrammeApplication[]> {
    const query = programmeId ? `?programme_id=${encodeURIComponent(programmeId)}` : "";
    return this.request<ProgrammeApplication[]>(
      `/api/v1/programmes/applications${query}`,
      {},
      true,
    );
  }

  apply(programmeId: string, statement: string): Promise<ProgrammeApplication> {
    return this.request<ProgrammeApplication>(
      `/api/v1/programmes/${programmeId}/applications`,
      { method: "POST", body: JSON.stringify({ statement: statement || null }) },
      true,
    );
  }

  reviewApplication(
    applicationId: string,
    status: ApplicationStatus,
    reviewNotes?: string,
  ): Promise<ProgrammeApplication> {
    return this.request<ProgrammeApplication>(
      `/api/v1/programmes/applications/${applicationId}`,
      { method: "PATCH", body: JSON.stringify({ status, review_notes: reviewNotes || null }) },
      true,
    );
  }

  uploadApplicationDocument(
    applicationId: string,
    documentType: DocumentType,
    file: File,
  ): Promise<SubmissionDocument> {
    const body = new FormData();
    body.set("document_type", documentType);
    body.set("document", file);
    return this.request<SubmissionDocument>(
      `/api/v1/programmes/applications/${applicationId}/documents`,
      { method: "POST", body },
      true,
    );
  }

  nominations(programmeId?: string): Promise<ProgrammeNomination[]> {
    const query = programmeId ? `?programme_id=${encodeURIComponent(programmeId)}` : "";
    return this.request<ProgrammeNomination[]>(
      `/api/v1/programmes/nominations${query}`,
      {},
      true,
    );
  }

  nominate(
    programmeId: string,
    payload: {
      nomination_type: EligibilityType;
      candidate_full_name: string;
      candidate_email: string;
      candidate_phone?: string;
      member_identifier?: string;
    },
  ): Promise<ProgrammeNomination> {
    return this.request<ProgrammeNomination>(
      `/api/v1/programmes/${programmeId}/nominations`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  bulkNominate(
    programmeId: string,
    nominationType: EligibilityType,
    file: File,
  ): Promise<{ created: number; nominations: ProgrammeNomination[] }> {
    const body = new FormData();
    body.set("nomination_type", nominationType);
    body.set("csv_file", file);
    return this.request<{ created: number; nominations: ProgrammeNomination[] }>(
      `/api/v1/programmes/${programmeId}/nominations/bulk`,
      { method: "POST", body },
      true,
    );
  }

  uploadNominationDocument(
    nominationId: string,
    documentType: DocumentType,
    file: File,
  ): Promise<SubmissionDocument> {
    const body = new FormData();
    body.set("document_type", documentType);
    body.set("document", file);
    return this.request<SubmissionDocument>(
      `/api/v1/programmes/nominations/${nominationId}/documents`,
      { method: "POST", body },
      true,
    );
  }

  async downloadDocument(documentId: string): Promise<Blob> {
    if (!this.accessToken) throw new ApiError("Authentication required", 401);
    const fetcher = this.fetcher ?? globalThis.fetch;
    const response = await fetcher.call(
      globalThis,
      `${this.baseUrl}/api/v1/programmes/documents/${documentId}`,
      {
        credentials: "include",
        headers: { Authorization: `Bearer ${this.accessToken}` },
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new ApiError(body?.detail ?? "Unable to download document", response.status);
    }
    return response.blob();
  }

  reviewNomination(
    nominationId: string,
    status: ApplicationStatus,
    reviewNotes?: string,
  ): Promise<ProgrammeNomination> {
    return this.request<ProgrammeNomination>(
      `/api/v1/programmes/nominations/${nominationId}`,
      { method: "PATCH", body: JSON.stringify({ status, review_notes: reviewNotes || null }) },
      true,
    );
  }

  myProfile(): Promise<TraineeProfile> {
    return this.request<TraineeProfile>("/api/v1/profiles/me", {}, true);
  }

  updateMyProfile(payload: PersonalProfilePayload): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me",
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  updateProfileConsents(payload: TraineeProfile["consent_preferences"]): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me/consents",
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    );
  }

  accountDeletionRequest(): Promise<AccountDeletionRequest | null> {
    return this.request<AccountDeletionRequest | null>(
      "/api/v1/auth/account-deletion",
      {},
      true,
    );
  }

  requestAccountDeletion(payload: {
    current_password: string;
    reason?: string;
    acknowledge_retention: boolean;
  }): Promise<AccountDeletionRequest> {
    return this.request<AccountDeletionRequest>(
      "/api/v1/auth/account-deletion",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  cancelAccountDeletion(id: string): Promise<AccountDeletionRequest> {
    return this.request<AccountDeletionRequest>(
      `/api/v1/auth/account-deletion/${id}`,
      { method: "DELETE" },
      true,
    );
  }

  addEducation(payload: Omit<EducationRecord, "id">): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me/education",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  deleteEducation(id: string): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      `/api/v1/profiles/me/education/${id}`,
      { method: "DELETE" },
      true,
    );
  }

  addEmployment(payload: Omit<EmploymentRecord, "id">): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me/employment",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  deleteEmployment(id: string): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      `/api/v1/profiles/me/employment/${id}`,
      { method: "DELETE" },
      true,
    );
  }

  addMembership(payload: Omit<MembershipRecord, "id">): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me/memberships",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  deleteMembership(id: string): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(
      `/api/v1/profiles/me/memberships/${id}`,
      { method: "DELETE" },
      true,
    );
  }

  uploadProfileDocument(
    documentType: ProfileDocumentType,
    file: File,
  ): Promise<TraineeProfile> {
    const body = new FormData();
    body.set("document_type", documentType);
    body.set("document", file);
    return this.request<TraineeProfile>(
      "/api/v1/profiles/me/documents",
      { method: "POST", body },
      true,
    );
  }

  async downloadProfileDocument(documentId: string): Promise<Blob> {
    if (!this.accessToken) throw new ApiError("Authentication required", 401);
    const fetcher = this.fetcher ?? globalThis.fetch;
    const response = await fetcher.call(
      globalThis,
      `${this.baseUrl}/api/v1/profiles/documents/${documentId}`,
      {
        credentials: "include",
        headers: { Authorization: `Bearer ${this.accessToken}` },
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new ApiError(body?.detail ?? "Unable to download document", response.status);
    }
    return response.blob();
  }

  validateProfileDocument(
    documentId: string,
    status: Exclude<DocumentValidationStatus, "pending">,
    notes?: string,
  ): Promise<ProfileDocument> {
    return this.request<ProfileDocument>(
      `/api/v1/profiles/documents/${documentId}/validation`,
      { method: "PATCH", body: JSON.stringify({ status, notes: notes || null }) },
      true,
    );
  }

  trainees(filters: {
    q?: string;
    institution_id?: string;
    state?: string;
    language?: string;
    skill?: string;
    minimum_completion?: number;
    page?: number;
    page_size?: number;
  } = {}): Promise<{
    items: TraineeListItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }> {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    const suffix = search.size ? `?${search.toString()}` : "";
    return this.request(`/api/v1/profiles/trainees${suffix}`, {}, true);
  }

  traineeProfile(id: string): Promise<TraineeProfile> {
    return this.request<TraineeProfile>(`/api/v1/profiles/trainees/${id}`, {}, true);
  }

  trainersDirectory(filters: {
    q?: string;
    institution_id?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<{
    items: TrainerListItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }> {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    const suffix = search.size ? `?${search.toString()}` : "";
    return this.request(`/api/v1/profiles/trainers${suffix}`, {}, true);
  }

  institutions(filters: {
    q?: string;
    institution_type?: InstitutionType;
    state?: string;
    active_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<{
    items: InstitutionRecord[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }> {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    const suffix = search.size ? `?${search.toString()}` : "";
    return this.request(`/api/v1/profiles/institutions${suffix}`, {}, true);
  }

  createInstitution(payload: InstitutionPayload): Promise<InstitutionRecord> {
    return this.request<InstitutionRecord>(
      "/api/v1/profiles/institutions",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  updateInstitution(
    id: string,
    payload: Partial<InstitutionPayload>,
  ): Promise<InstitutionRecord> {
    return this.request<InstitutionRecord>(
      `/api/v1/profiles/institutions/${id}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    );
  }

  platformAssistant(payload: {
    message: string;
    history: AssistantChatTurn[];
    page_path: string;
    language: CareerLanguage;
  }): Promise<AssistantChatResponse> {
    return this.request(
      "/api/v1/assistant/chat",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    );
  }

  careerConversations(): Promise<CareerConversationSummary[]> {
    return this.request("/api/v1/career/conversations", {}, true);
  }

  createCareerConversation(language: CareerLanguage): Promise<CareerConversation> {
    return this.request(
      "/api/v1/career/conversations",
      { method: "POST", body: JSON.stringify({ language }) },
      true,
    );
  }

  careerConversation(id: string): Promise<CareerConversation> {
    return this.request(`/api/v1/career/conversations/${id}`, {}, true);
  }

  sendCareerMessage(id: string, content: string): Promise<CareerMessageExchange> {
    return this.request(
      `/api/v1/career/conversations/${id}/messages`,
      { method: "POST", body: JSON.stringify({ content }) },
      true,
    );
  }

  saveCareerFeedback(
    conversationId: string,
    messageId: string,
    rating: CareerFeedbackRating,
  ): Promise<CareerFeedback> {
    return this.request(
      `/api/v1/career/conversations/${conversationId}/messages/${messageId}/feedback`,
      { method: "PUT", body: JSON.stringify({ rating }) },
      true,
    );
  }

  escalateCareerConversation(id: string, reason: string): Promise<CareerEscalation> {
    return this.request(
      `/api/v1/career/conversations/${id}/escalate`,
      { method: "POST", body: JSON.stringify({ reason }) },
      true,
    );
  }

  register(payload: RegistrationPayload): Promise<{ message: string; status: AccountStatus }> {
    return this.request<{ message: string; status: AccountStatus }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  adminCheck(): Promise<{ authorized: boolean; role: RoleCode }> {
    return this.request<{ authorized: boolean; role: RoleCode }>(
      "/api/v1/auth/admin-check",
      {},
      true,
    );
  }

  requestPasswordReset(email: string): Promise<PasswordResetRequestResponse> {
    return this.request<PasswordResetRequestResponse>("/api/v1/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  confirmPasswordReset(token: string, newPassword: string): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/v1/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  }

  private analyticsQuery(values: Record<string, string | number | undefined>): string {
    const query = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    return query.size ? `?${query.toString()}` : "";
  }

  private async request<T>(
    path: string,
    options: { method?: string; body?: BodyInit; headers?: Record<string, string> } = {},
    authenticated = false,
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
    if (typeof options.body === "string") {
      headers["Content-Type"] = "application/json";
    }
    if (authenticated) {
      if (!this.accessToken) {
        throw new ApiError("Authentication required", 401);
      }
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    const fetcher = this.fetcher ?? globalThis.fetch;
    const response = await fetcher.call(globalThis, `${this.baseUrl}${path}`, {
      method: options.method ?? "GET",
      body: options.body,
      credentials: "include",
      headers,
    });
    const responseBody = (await response.json().catch(() => null)) as
      | (T & { detail?: string })
      | null;

    if (!response.ok) {
      throw new ApiError(
        responseBody?.detail ?? `Request failed with status ${response.status}`,
        response.status,
      );
    }

    return responseBody as T;
  }

  private async download(path: string): Promise<Blob> {
    if (!this.accessToken) throw new ApiError("Authentication required", 401);
    const fetcher = this.fetcher ?? globalThis.fetch;
    const response = await fetcher.call(globalThis, `${this.baseUrl}${path}`, {
      credentials: "include",
      headers: { Authorization: `Bearer ${this.accessToken}` },
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new ApiError(body?.detail ?? "Unable to download learning file", response.status);
    }
    return response.blob();
  }
}

export const apiClient = new ApiClient();
