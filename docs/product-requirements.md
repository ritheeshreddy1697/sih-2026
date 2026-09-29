# NCCT Cooperative Training Platform Product Requirements

## Purpose

Create a national cooperative training platform that helps NCCT coordinate training demand, nominations, program delivery, trainee progress, assessments and employer visibility across NCCT, VAMNICOM, RICM and ICM stakeholders.

## Users

- NCCT administrators manage platform governance, reporting, institutional configuration and cross-institution visibility.
- VAMNICOM/RICM/ICM administrators manage institute-level programs, trainers, batches, calendars and reporting.
- Trainers manage assigned sessions, materials, attendance and trainee evaluation workflows.
- Trainees access enrolled programs, schedules, materials, assessments, certificates and placement-related information.
- Nominating institutions nominate candidates, track approvals and monitor completion outcomes.
- Employers discover eligible trainees and interact with placement or post-training outcome workflows.

## Phase 1 Scope

- Establish production-quality monorepo foundations.
- Provide responsive frontend application shell.
- Provide reusable loading, empty and error states.
- Provide frontend API client for backend communication.
- Provide backend health-check endpoints.
- Provide automated test setup for frontend and backend.
- Provide Docker Compose for local PostgreSQL and app services.
- Document architecture, setup and progress.

## Phase 2 Authentication Scope

- Authentication for NCCT super administrators, institute administrators, trainers, trainees,
  nominating institutions and employers/recruiters.
- Secure login, logout, refresh and password-reset workflows.
- Backend role and permission enforcement with protected frontend routes.
- Active, suspended and pending-verification account states.
- Authentication audit logs and development seed accounts.

## Phase 3 Interface Scope

- Public landing, sign-in and self-registration experiences.
- Responsive authenticated navigation with desktop sidebar and mobile drawer.
- Profile and notification controls with keyboard-accessible interactions.
- Role-relevant dashboards for NCCT, institute administrators, trainers, trainees,
  nominating institutions and employers/recruiters.
- Backend-provided dashboard content and quick actions filtered through the shared permission model.
- Clear loading, empty, error and permission-denied states.
- Accessible status labels, large touch targets and plain-language interface copy.

## Phase 4 Programme Management Scope

- Programme drafting, editing, NCCT approval or rejection, publishing and archiving.
- Online, offline and hybrid delivery with eligibility, capacity, location, language, duration,
  dates and application deadlines.
- Programme batches and institution-scoped trainer assignments.
- Eligible trainee discovery, individual applications, supporting documents and status tracking.
- PACS, SHG and cooperative-institution nominations submitted individually or through validated
  CSV files.
- Institute review decisions covering under-review, approved, rejected and wait-listed states.
- Capacity, ownership, deadline, eligibility and duplicate-submission enforcement in the backend.
- Programme search and filters, including NCCT institution-wide visibility.
- Audit events for programme lifecycle, application, nomination, assignment and document actions.

## Phase 5 Profile Management Scope

- Central institution hierarchy for NCCT, VAMNICOM, RICMs, ICMs, PACS, SHGs, dairy
  cooperatives and other cooperative institutions.
- Institution profiles with parent relationships, contact details, location, registration details,
  active status, search, filters and pagination.
- Private trainee profiles covering personal and contact information, education, employment,
  cooperative membership, skills, career interests, language and location preferences.
- Validated trainee documents and explicit placement, communication and data-sharing consent.
- Consolidated enrolled and completed programme, attendance, assessment and certificate history.
- Profile completion indicators and trainee audit history.
- Trainee self-service restricted to the authenticated trainee and institution-scoped administrator
  access enforced by backend queries.
- Clearly labelled fictional demonstration profiles and institutions for local development.

## Phase 6 Learning Management And Assessment Scope

- Courses connected one-to-one with persisted training programmes.
- Ordered sections, modules and lessons with text, video, audio, PDF and external-resource formats.
- Extensible course languages with English, Hindi and Telugu demonstration content.
- Enrolment-gated course access, server-owned completion, bounded media progress and resume state.
- Trainer and institute-authorized course, curriculum and localized-content management.
- Published assignments with validated PDF or Word submissions, scores and trainer feedback.
- Reusable question banks and multiple-choice pre-training, practice and post-training assessments.
- Server-enforced attempt limits, passing scores, automatic grading and trainer feedback.
- Protected learning files, assignment files and manager review queues.
- A complete fictional demonstration course covering the learner and trainer workflows.

## Phase 7 Attendance Scope

- Trainer-created attendance sessions restricted to assigned programme batches.
- Stable signed trainee QR identities and rotating 45-second attendance-session QR codes.
- Registered, revocable kiosk devices for Raspberry Pi, laptop and Android Chromium browsers.
- Camera scanning and USB-reader fallback at `/kiosk/attendance`, with large controls and clear
  success, duplicate, offline and validation-error feedback.
- Server validation of device, institution, session window, programme, batch, enrolment, trainee
  role and active account state.
- Duplicate prevention through both a unique session-enrolment constraint and idempotency keys.
- Client capture time, server receipt time, source and kiosk device recorded for each check-in.
- IndexedDB queueing before transmission and automatic retry when browser connectivity returns.
- Trainer-requested manual corrections with mandatory reasons and separate institute/NCCT approval.
- Session reports with present, absent and excused totals, attendance rate, timestamps and devices.
- Audit events for session, device, pairing, check-in and correction actions.

## Phase 8 Digital Certification Scope

- Programme-scoped certificate policies with configurable course-completion, attendance and
  post-training assessment thresholds, optional expiry and an active or paused issuance state.
- Administrator-controlled issuance restricted to NCCT and the programme's owning institute.
- Eligibility recomputed from persisted lesson progress, operational attendance and server-graded
  post-training attempts at the time of issuance.
- Backend-generated PDF certificates with unique certificate numbers, cryptographically random
  verification tokens and a QR code linked to public verification.
- Public verification with valid, revoked and expired states and only the recipient name,
  programme, institution, certificate number and validity dates.
- Reasoned certificate revocation with append-only audit events and immediately invalid public
  verification.
- A private trainee digital skill wallet with authenticated PDF downloads and verification-link
  sharing.
- Narrow issuance requests that reject browser-supplied names, scores, progress, dates,
  certificate numbers and verification data.

## Phase 9 Training Operations And Logistics Scope

- Institution-owned training venues and classrooms with capacities, equipment and active state.
- Programme-batch timetables with trainer, venue and optional classroom allocation in calendar and
  list views.
- Transactional overlap validation for trainers, classrooms and whole-venue reservations.
- Hostel buildings, rooms and individual beds with dated trainee allocation, check-in and
  check-out state.
- Transactional overlap validation preventing either a bed or a trainee from being double-booked.
- Per-enrolment meal preferences, dietary notes, arrival/departure transport and emergency
  contacts.
- Programme material inventory and one-time trainee distribution with stock validation.
- Maintenance and participant issue reporting, priority, status, resolution notes and audit events.
- Institute administrators restricted to their own institution, NCCT cross-institution visibility
  and trainee self-only timetable and logistics access enforced by backend queries.
- Clearly labelled fictional training-operations data for local development.

## Phase 10 Employment Exchange Scope

- Employer self-registration creates a pending company record that requires NCCT administrator
  verification before recruitment access is enabled.
- Verified employers manage company profiles and institution-owned draft, published and closed
  job postings.
- Employers search only placement-visible, open-to-work trainees with valid digital certificates,
  using verified skill, certified course, certificate number and location filters.
- Employers shortlist candidates, schedule interviews and record offer, hiring and rejection
  outcomes through validated backend transitions.
- Trainees maintain a private employment profile and validated PDF/Word resume, search and save
  jobs, apply, track status and withdraw non-terminal applications.
- Recommendations use a deterministic 100-point breakdown: verified skill match (40), required
  certified course match (25), preferred location (20) and career-interest alignment (15).
- Every recommendation displays matched reasons and gaps; the platform does not present an opaque
  or AI-generated employability score.
- Candidate contact details and resume bytes remain unavailable until the trainee has enabled data
  sharing and submitted an active application to that employer.
- Certificate and skill facts attached to applications are selected from current backend records,
  never accepted from the browser.

## Phase 11 Multilingual Career Counselling Scope

- An authenticated trainee counsellor in English, Hindi and Telugu with persisted conversation
  history and language-specific approved FAQ retrieval.
- Guidance for suitable published training programmes, jobs matched to verified skills, resume and
  interview preparation, cooperative entrepreneurship, platform FAQs and navigation.
- Programme and job responses grounded only in current platform rows, with typed references linking
  to the actual programme detail or employment record used in the response.
- A provider-independent backend AI interface with an optional Gemini-compatible provider selected
  through server environment variables and no provider credentials shipped to the browser.
- A deterministic local FAQ provider when no key is configured, plus automatic local fallback if
  the external provider fails or returns an unusable response.
- No free-form model generation for programme listings, job listings, schemes or eligibility
  criteria; unavailable information must be stated explicitly.
- Per-answer helpful/not-helpful feedback, trainee-to-human support escalation, audit events,
  validated 2,000-character input and per-user database-backed rate limiting.
- Backend permission and conversation-ownership checks for every private operation, with NCCT-only
  access to the human-support queue.

## Phase 12 Analytics Scope

- Permission-gated analytics for NCCT national administrators and institute administrators, with
  institute users restricted to their institution hierarchy by backend queries.
- Filters for institution, participant home state, programme, programme start-date range, gender
  and participant category.
- Persisted metrics for registrations, approvals, attendance, required-course completion,
  pre/post assessment improvement, dropouts, certificate issuance, job applications, interviews
  and placements.
- Institution-wise and programme-wise performance summaries plus participant geographic
  distribution.
- Visible metric definitions, with date filters consistently selecting programme cohorts by
  programme start date.
- Keyboard-operable metric drill-downs, responsive summary tables, accessible comparison charts
  and scoped CSV export.
- Explicit labels whenever fictional seeded institutions or trainee records contribute to a view.
- No browser-supplied totals, random production values or mutable analytics snapshot tables.

## Phase 13 Optional Biometric Attendance Scope

- Voluntary, purpose-specific biometric enrolment consent with QR attendance always available.
- Webcam enrolment and a time-limited head-turn liveness challenge using exactly three transient
  JPEG or PNG frames.
- Strict one-to-one verification only after an enrolled trainee claims their identity code; no
  unknown-person identification, roster-wide face search or general surveillance.
- AES-GCM encrypted face templates with a separately managed backend key, version metadata and no
  persisted raw face image or video.
- Backend-owned liveness and confidence calculation, configurable automatic and manual-review
  thresholds, and no automatic presence for uncertain or rejected matches.
- Trainee self-deletion, institution-scoped administrator deletion, consent history and biometric
  enrolment, verification, rejection, review and deletion audit events.
- Replaceable provider interface and clearly labelled local demonstration provider. Production
  configuration refuses to enable the demonstration provider.
- Online-only face verification; existing idempotent QR attendance remains the offline fallback.

## Out Of Scope

- Provider-specific CI/CD and cloud infrastructure provisioning.
- Real NCCT data migration.
- Email delivery, identity-provider federation and other external integrations.
- Multi-factor authentication and malware scanning.
- Procurement, certification and operation of a production-grade face-recognition and
  presentation-attack-detection provider, including independent demographic accuracy testing.

## Non-Functional Requirements

- Modular architecture suitable for role-based feature growth.
- Type-safe frontend code.
- Explicit API versioning.
- Backend configuration through environment variables.
- Automated linting, type-checking and tests.
- Local development parity through Docker Compose.
- No real secrets committed to source control.

## Success Criteria

- Frontend starts locally and renders the application shell.
- Backend starts locally and responds to health endpoints.
- Frontend and backend tests pass.
- Linting and type-checking pass.
- Documentation explains setup and current boundaries.
- Authentication tests cover successful and invalid login, unauthenticated access and forbidden roles.
- Public and authenticated pages have no horizontal overflow at desktop or 390-pixel mobile widths.
- Keyboard focus reaches skip navigation, mobile navigation, notifications, profile controls and
  dashboard actions in a predictable order.
